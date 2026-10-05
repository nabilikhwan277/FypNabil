"""Two-layer rubric scoring.

Layer A (rules, deterministic) decides whatever it can:
  - Jawi spelling criteria  -> exact match after strict normalisation
  - Betul/Salah items       -> the stated choice must match
  - keyword criteria        -> any rubric keyword appears in the answer
                               (unless the answer contradicts the numbers)
Anything Layer A cannot settle goes to the rule in the scoring configuration
(backend/app/assess/scoring_config.json, chosen in Phase 5 on the train split):
  - Tahap 1: similarity / overlap rule, never the LLM
  - Tahap 2/3: the configured method (similarity/overlap, LLM probability
    judge, generative LLM judge + guard, or a hybrid)
The decision logic itself lives in decision.py, shared with the evaluation.
Marks are always added up in code.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from typing import Callable

from .decision import Rule, ScoringConfig, award, decide, load_config  # noqa: F401 (award re-exported)
from .jawi_text import is_arabic_script
from .judge import Generate, LabelProbs, judge_criterion, judge_prob
from .matching import (content_overlap, first_match, is_true_false, keyword_overlap, number_conflict,
                       true_false_answer)

Embed = Callable[[list[str]], list[list[float]]]


@dataclass
class Thresholds:
    """Override for the generative judge's similarity guard (Phase 4 knob)."""
    guard_similarity: float | None = None


@dataclass
class CriterionResult:
    criterion: str
    marks: float
    awarded: float
    met: str                  # ya | separa | tidak
    layer: str                # A-spelling | A-truefalse | A-keyword | A-keyword-conflict | A-similarity | A-none
                              # | B-prob | B-llm | B-guard | B-fallback
    evidence: str = ""        # matched keyword, if any
    similarity: float | None = None
    overlap: float | None = None
    llm_raw: str = ""
    llm_reason: str = ""
    llm_verdict: str | None = None      # generative judge, before the guard
    llm_probs: dict | None = None       # probability judge output


@dataclass
class RubricResult:
    criteria: list[CriterionResult] = field(default_factory=list)
    score: float = 0.0
    max_marks: float = 0.0
    answer_similarity: float = 0.0
    llm_calls: int = 0
    config: str = ""

    @property
    def percent(self) -> float:
        return round(100 * self.score / self.max_marks, 1) if self.max_marks else 0.0

    def to_dict(self) -> dict:
        d = asdict(self)
        d["percent"] = self.percent
        return d


def _cos(a: list[float], b: list[float]) -> float:
    return round(float(sum(x * y for x, y in zip(a, b))), 4)


def is_spelling_criterion(question: dict, keywords: list[str]) -> bool:
    return question.get("subject") == "jawi" and bool(keywords) and all(is_arabic_script(k) for k in keywords)


def layer_a(question: dict, kws: list[str], answer: str, ref_text: str) -> tuple[str | None, str | None, str]:
    """(layer, met, evidence) from the deterministic rules, or (None, None, '')."""
    if is_spelling_criterion(question, kws):
        hit = first_match(kws, answer, strict=True)
        return "A-spelling", "ya" if hit else "tidak", hit or ""
    if is_true_false(kws):
        expected, got = true_false_answer(" ".join(kws)), true_false_answer(answer)
        return "A-truefalse", "ya" if got and got == expected else "tidak", got or ""
    hit = first_match(kws, answer)
    if hit:
        if number_conflict(" ".join(kws), answer) and number_conflict(ref_text, answer):
            return "A-keyword-conflict", "tidak", hit
        return "A-keyword", "ya", hit
    return None, None, ""


def score_answer(
    question: dict,
    answer: str,
    *,
    embed: Embed,
    generate: Generate | None,
    label_probs: LabelProbs | None = None,
    context: str = "",
    config: ScoringConfig | None = None,
    thresholds: Thresholds | None = None,
    examples: list[dict] | None = None,
    max_new_tokens_judge: int = 80,
) -> RubricResult:
    cfg = config or load_config()
    rubric = question["rubric"]
    reference = question.get("reference_answer_rumi", "")
    reference_jawi = question.get("reference_answer_jawi", "")
    ref_text = "\n".join(x for x in (reference, reference_jawi) if x)
    level = int(question["level"])
    rule: Rule = cfg.rule_for(level)
    if rule.method == "gen" and thresholds and thresholds.guard_similarity is not None:
        rule = replace(rule, guard=thresholds.guard_similarity)
    llm_ok = level >= 2 and (generate if rule.method == "gen" else label_probs) is not None

    crit_texts = [f"{c['criterion']} {' '.join(c.get('keywords', []))}" for c in rubric]
    vecs = embed([answer, ref_text or answer, *crit_texts])
    ans_vec, ref_vec, crit_vecs = vecs[0], vecs[1], vecs[2:]
    answer_sim = _cos(ans_vec, ref_vec)
    result = RubricResult(max_marks=float(sum(c["marks"] for c in rubric)), answer_similarity=answer_sim,
                          config=cfg.name)

    for c, cvec in zip(rubric, crit_vecs):
        kws = [k for k in c.get("keywords", []) if k]
        marks = float(c["marks"])
        a_layer, a_met, evidence = layer_a(question, kws, answer, ref_text)
        f = {"a_layer": a_layer, "a_met": a_met, "crit_sim": _cos(ans_vec, cvec), "ans_sim": answer_sim,
             "kw_overlap": keyword_overlap(kws, answer), "crit_overlap": content_overlap(c["criterion"], answer),
             "num_conflict": number_conflict(ref_text, answer), "n_criteria": len(rubric)}
        r = CriterionResult(criterion=c["criterion"], marks=marks, awarded=0.0, met="tidak", layer=a_layer or "A-none",
                            evidence=evidence, similarity=f["crit_sim"],
                            overlap=round(max(f["kw_overlap"], f["crit_overlap"]), 3))

        use_rule = rule
        if a_layer is None and rule.needs_llm and llm_ok:
            kwargs = dict(criterion=c["criterion"], question=question.get("question_rumi", ""),
                          reference=reference or reference_jawi, answer=answer, context=context)
            if rule.method == "gen":
                j = judge_criterion(generate, max_new_tokens=max_new_tokens_judge, **kwargs)
                result.llm_calls += j.attempts
                r.llm_raw, r.llm_reason, r.llm_verdict = j.raw, j.reason, j.met
                f["llm_gen"] = j.met
            else:
                key = "p_fs" if rule.method.endswith("_fs") else "p_zs"
                f[key] = judge_prob(label_probs, examples=examples if key == "p_fs" else None, **kwargs)
                result.llm_calls += 1
                r.llm_probs = {k: round(v, 4) for k, v in f[key].items()}
        elif a_layer is None and rule.needs_llm:
            use_rule = Rule("mix", hi=0.6, w=0.5)  # LLM unavailable: safe non-LLM fallback

        r.met = decide(f, use_rule)
        if a_layer is None:
            if use_rule.method == "gen":
                if f.get("llm_gen") is None:
                    r.layer = "B-fallback"
                elif f["llm_gen"] in ("ya", "separa") and r.met == "tidak":
                    r.layer = "B-guard"
                else:
                    r.layer = "B-llm"
            elif use_rule.needs_llm:
                r.layer = "B-prob"
            else:
                r.layer = "A-similarity" if r.met != "tidak" else "A-none"
        r.awarded = award(marks, r.met)
        result.criteria.append(r)

    result.score = float(sum(c.awarded for c in result.criteria))
    return result
