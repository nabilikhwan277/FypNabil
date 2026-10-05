"""Compute (and cache) every scoring signal for each silver answer x criterion.

Runs the expensive parts once (retrieval, embeddings, LLM calls) so that
tune_scoring.py can compare many scoring configurations offline in seconds.

Per criterion we store:
  a_layer / a_met  - the deterministic Layer A decision, or None if unresolved
  crit_sim         - bge-m3 cosine(answer, criterion + keywords)
  ans_sim          - bge-m3 cosine(answer, reference answer)
  kw_overlap       - content-word overlap with the best rubric keyword
  crit_overlap     - content-word overlap with the criterion text
  num_conflict     - reference numbers contradicted by the answer
  llm_gen          - current generative judge verdict (ya/separa/tidak/None)   [L2/L3 only]
  p_zs / p_fs      - probability judge, zero-shot / few-shot                   [L2/L3 only]

Usage: .venv\\Scripts\\python eval\\scoring_features.py train [programmatic_sample]
       .venv\\Scripts\\python eval\\scoring_features.py test
Writes eval/cache/features_<split>.jsonl (resumable).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "eval"))

from backend.app.assess.judge import judge_criterion, judge_prob  # noqa: E402
from backend.app.assess.matching import (  # noqa: E402
    content_overlap, first_match, is_true_false, keyword_overlap, number_conflict, true_false_answer)
from backend.app.assess.pipeline import llm_generate  # noqa: E402
from backend.app.assess.rubric import is_spelling_criterion  # noqa: E402
from backend.app.embeddings import embed  # noqa: E402
from backend.app.kb.retriever import search_notes  # noqa: E402
from backend.app.llm import get_llm  # noqa: E402
from backend.app.questions import load_questions  # noqa: E402
from silver import load_silver  # noqa: E402

CACHE = ROOT / "eval" / "cache"
FEWSHOT_FILE = ROOT / "backend" / "app" / "prompts" / "judge_examples.json"


def cos(a, b) -> float:
    return round(float(sum(x * y for x, y in zip(a, b))), 4)


def layer_a(q: dict, kws: list[str], answer: str, ref_text: str) -> tuple[str | None, str | None]:
    """Same deterministic rules as rubric.score_answer, minus the fallbacks."""
    if is_spelling_criterion(q, kws):
        return "A-spelling", "ya" if first_match(kws, answer, strict=True) else "tidak"
    if is_true_false(kws):
        exp, got = true_false_answer(" ".join(kws)), true_false_answer(answer)
        return "A-truefalse", "ya" if got and got == exp else "tidak"
    if first_match(kws, answer):
        if number_conflict(" ".join(kws), answer) and number_conflict(ref_text, answer):
            return "A-keyword-conflict", "tidak"
        return "A-keyword", "ya"
    return None, None


def build_fewshot(train_items: list[dict], qs: dict) -> list[dict]:
    """3 fixed generic examples from the TRAIN paraphrase set (ya, separa, tidak),
    short answers, non-Jawi-spelling criteria. Saved for use at run time."""
    picks: dict[str, dict] = {}
    for it in train_items:
        if it["family"] != "paraphrase":
            continue
        q = qs[it["question_id"]]
        if q["level"] < 2 or len(it["answer"]) > 120:
            continue
        for rc, lab in zip(q["rubric"], it["criteria"]):
            met = lab["met"]
            if met in picks or is_spelling_criterion(q, rc.get("keywords", [])):
                continue
            if first_match(rc.get("keywords", []), it["answer"]):
                continue  # want examples that need judgement, not keyword hits
            picks[met] = {"criterion": rc["criterion"], "answer": it["answer"], "met": met,
                          "source": it["answer_id"]}
        if len(picks) == 3:
            break
    ex = [picks[k] for k in ("ya", "separa", "tidak") if k in picks]
    FEWSHOT_FILE.write_text(json.dumps(ex, indent=1, ensure_ascii=False), encoding="utf-8")
    return ex


def main(split: str, sample: int | None) -> None:
    qs = load_questions()
    items = load_silver(split, programmatic_sample=sample)
    if split == "train" or not FEWSHOT_FILE.exists():
        examples = build_fewshot(load_silver("train", programmatic_sample=10), qs)
    else:
        examples = json.loads(FEWSHOT_FILE.read_text(encoding="utf-8"))
    CACHE.mkdir(parents=True, exist_ok=True)
    out = CACHE / f"features_{split}.jsonl"
    done = set()
    if out.exists():
        done = {json.loads(line)["answer_id"] for line in out.read_text(encoding="utf-8").splitlines() if line}
    todo = [it for it in items if it["answer_id"] not in done]
    print(f"{split}: {len(items)} items, {len(todo)} to compute, {len(examples)} few-shot examples")
    llm = get_llm()
    t0 = time.perf_counter()
    with out.open("a", encoding="utf-8") as fh:
        for n, it in enumerate(todo, 1):
            q = qs[it["question_id"]]
            ans = it["answer"]
            ref_r, ref_j = q.get("reference_answer_rumi", ""), q.get("reference_answer_jawi", "")
            ref_text = "\n".join(x for x in (ref_r, ref_j) if x)
            crit_texts = [f"{c['criterion']} {' '.join(c.get('keywords', []))}" for c in q["rubric"]]
            vecs = embed([ans, ref_text or ans, *crit_texts])
            ans_sim = cos(vecs[0], vecs[1])
            context = ""
            needs_llm = q["level"] >= 2
            if needs_llm:
                for h in search_notes(f"{q.get('question_rumi', '')} {ans}", subject=q["subject"],
                                      topic_id=q["topic_id"], k=4):
                    if len(context) + len(h.text) > 1800:
                        break
                    context += h.text + "\n\n"
            crits = []
            for c, cvec, lab in zip(q["rubric"], vecs[2:], it["criteria"]):
                kws = [k for k in c.get("keywords", []) if k]
                a_layer, a_met = layer_a(q, kws, ans, ref_text)
                f = {"criterion": c["criterion"], "marks": c["marks"], "label": lab["met"],
                     "a_layer": a_layer, "a_met": a_met, "crit_sim": cos(vecs[0], cvec), "ans_sim": ans_sim,
                     "kw_overlap": round(keyword_overlap(kws, ans), 3),
                     "crit_overlap": round(content_overlap(c["criterion"], ans), 3),
                     "num_conflict": number_conflict(ref_text, ans)}
                if needs_llm and a_layer is None:
                    kwargs = dict(criterion=c["criterion"], question=q.get("question_rumi", ""),
                                  reference=ref_r or ref_j, answer=ans, context=context.strip())
                    f["llm_gen"] = judge_criterion(llm_generate, max_new_tokens=60, **kwargs).met
                    f["p_zs"] = judge_prob(llm.label_probs, **kwargs)
                    f["p_fs"] = judge_prob(llm.label_probs, examples=examples, **kwargs)
                crits.append(f)
            rec = {"answer_id": it["answer_id"], "question_id": q["id"], "kind": it["kind"],
                   "family": it["family"], "script": it.get("script", ""), "subject": q["subject"],
                   "level": q["level"], "max_marks": q["max_marks"], "expected_score": it["expected_score"],
                   "criteria": crits}
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            fh.flush()
            if n % 25 == 0:
                el = time.perf_counter() - t0
                print(f"  {n}/{len(todo)}  {el:.0f}s  (~{el / n * (len(todo) - n):.0f}s left)", flush=True)
    print("done", out)


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else None)
