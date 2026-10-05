"""Controlled ReAct loop.

The five Thought -> Action -> Observation steps run in a fixed order chosen by
code (not planned by the LLM, which is too small to plan reliably). Each step
is recorded in a trace that the UI can show ("Bagaimana AI berfikir") and the
evaluation can inspect.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable

from ..memory.db import TopicHistory, Update, compute_update
from .feedback import build_feedback
from .rubric import Embed, Generate, RubricResult, Thresholds, score_answer

Search = Callable[..., list]            # search_notes-compatible
History = Callable[[str], TopicHistory]  # topic_id -> history
Source = Callable[[str, list[int]], dict]


@dataclass
class Step:
    step: int
    thought: str
    action: str
    action_input: dict
    observation: dict
    ms: int

    def to_dict(self) -> dict:
        return self.__dict__.copy()


@dataclass
class ReActResult:
    rubric: RubricResult
    feedback: dict
    history: TopicHistory
    update: Update
    context_hits: list
    trace: list[Step] = field(default_factory=list)

    def trace_dicts(self) -> list[dict]:
        return [s.to_dict() for s in self.trace]


def _clip(text: str, n: int = 160) -> str:
    return text if len(text) <= n else text[: n - 1] + "…"


def run_react(
    question: dict,
    answer: str,
    *,
    search: Search,
    embed: Embed,
    history: History,
    source: Source,
    generate: Generate | None,
    thresholds: Thresholds | None = None,
    k: int = 4,
    context_chars: int = 1800,
    use_llm_feedback: bool = True,
    label_probs=None,
    config=None,
    examples: list[dict] | None = None,
) -> ReActResult:
    trace: list[Step] = []

    def record(thought, action, action_input, fn):
        t0 = time.perf_counter()
        obs, value = fn()
        trace.append(Step(len(trace) + 1, thought, action, action_input, obs,
                          int((time.perf_counter() - t0) * 1000)))
        return value

    # 1. Understand the question
    rubric_def = question["rubric"]
    record(
        f"Soalan ini Tahap {question['level']} ({question['type']}) topik {question['topic_id']}. "
        f"Apakah kriteria pemarkahannya?",
        "get_question", {"question_id": question["id"]},
        lambda: ({"criteria": [c["criterion"] for c in rubric_def], "max_marks": question["max_marks"],
                  "reference": _clip(question.get("reference_answer_rumi", ""))}, None),
    )

    # 2. Retrieve textbook evidence (RAG)
    query = f"{question.get('question_rumi', '')} {answer}"

    def _retrieve():
        hits = search(query, subject=question["subject"], topic_id=question["topic_id"], k=k)
        return ({"chunks": [{"id": h.id, "section": h.metadata.get("section", ""), "score": h.score}
                            for h in hits]}, hits)

    hits = record("Apakah kata buku teks tentang soalan ini?", "search_notes",
                  {"query": _clip(query), "topic_id": question["topic_id"], "k": k}, _retrieve)
    context = ""
    for h in hits:
        if len(context) + len(h.text) > context_chars:
            break
        context += h.text + "\n\n"

    # 3. Score against the rubric (Layer A rules, Layer B LLM judge)
    def _score():
        r = score_answer(question, answer, embed=embed, generate=generate, label_probs=label_probs,
                         context=context.strip(), config=config, thresholds=thresholds, examples=examples)
        return ({"score": r.score, "max_marks": r.max_marks, "percent": r.percent,
                 "answer_similarity": r.answer_similarity, "llm_calls": r.llm_calls, "config": r.config,
                 "criteria": [{"criterion": c.criterion, "met": c.met, "awarded": c.awarded,
                               "layer": c.layer, "evidence": c.evidence, "similarity": c.similarity,
                               "overlap": c.overlap, "llm_probs": c.llm_probs} for c in r.criteria]}, r)

    rubric = record("Kriteria manakah yang dipenuhi oleh jawapan murid?", "score_rubric",
                    {"answer": _clip(answer)}, _score)

    # 4. Recall the student's learning memory
    def _history():
        h = history(question["topic_id"])
        upd = compute_update(h, int(question["level"]), rubric.percent)
        return ({"mastery": h.mastery, "attempts": h.attempts, "level_unlocked": h.level_unlocked,
                 "repeated_mistakes": h.repeated_mistakes, "mastery_after": upd.mastery_after,
                 "level_after": upd.level_after}, (h, upd))

    hist, upd = record("Apakah yang murid ini pernah tersilap sebelum ini?", "get_history",
                       {"topic_id": question["topic_id"]}, _history)

    # 5. Build adaptive feedback
    def _feedback():
        src = source(question["topic_id"], question.get("source_pages") or [])
        fb = build_feedback(question=question, rubric=rubric, history=hist, update=upd, source=src,
                            generate=generate if use_llm_feedback else None)
        return ({"stars": fb["stars"], "mistakes": len(fb["mistakes"]), "suggestion": fb["suggestion"]["action"],
                 "encouragement_source": fb["encouragement"]["source"]}, fb)

    feedback = record("Maklum balas apakah yang paling membantu murid ini?", "generate_feedback",
                      {"mastery": hist.mastery}, _feedback)

    return ReActResult(rubric=rubric, feedback=feedback, history=hist, update=upd,
                       context_hits=hits, trace=trace)
