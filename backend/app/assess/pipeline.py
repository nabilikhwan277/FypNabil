"""Assessment pipeline: wires the real models, retriever and memory into the
ReAct loop, then saves the attempt (step 7 of the system architecture)."""
from __future__ import annotations

import json
import logging
import random
import time
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from ..config import get_settings
from ..embeddings import embed
from ..kb.retriever import search_notes
from ..llm import get_llm
from ..memory.db import MemoryStore
from ..notes import note_meta, source_label
from ..questions import load_questions
from .decision import load_config
from .react import run_react

log = logging.getLogger(__name__)

MAX_ANSWER_CHARS = 2000


class AssessmentError(ValueError):
    pass


@lru_cache
def get_memory() -> MemoryStore:
    return MemoryStore(get_settings().sqlite_path)


def live_scorer() -> str:
    """The marking system chosen by the admin (live_config.py), else KAFA_SCORER."""
    from ..live_config import current

    return current()


def llm_generate(messages: list[dict], max_new_tokens: int) -> str:
    return get_llm().generate(messages, max_new_tokens=max_new_tokens).text


def llm_label_probs(messages: list[dict], labels: dict[str, list[str]]) -> dict[str, float]:
    return get_llm().label_probs(messages, labels)


@lru_cache
def judge_examples() -> list[dict]:
    """Few-shot examples for the probability judge (built from the TRAIN silver set)."""
    path = Path(__file__).resolve().parent.parent / "prompts" / "judge_examples.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


@dataclass
class Assessment:
    attempt_id: int | None
    question_id: str
    score: float
    max_marks: float
    percent: float
    feedback: dict
    criteria: list[dict]
    trace: list[dict]
    new_badges: list[str]
    latency_ms: int

    def to_dict(self) -> dict:
        return self.__dict__.copy()


def assess(student_id: int, question_id: str, answer: str, *, use_llm: bool = True,
           memory: MemoryStore | None = None, save: bool = True) -> Assessment:
    answer = (answer or "").strip()
    if not answer:
        raise AssessmentError("Jawapan kosong.")
    if len(answer) > MAX_ANSWER_CHARS:
        raise AssessmentError(f"Jawapan terlalu panjang (maksimum {MAX_ANSWER_CHARS} aksara).")
    question = load_questions().get(question_id)
    if question is None:
        raise AssessmentError(f"Soalan tidak dijumpai: {question_id}")
    mem = memory or get_memory()
    if mem.get_student(student_id) is None:
        raise AssessmentError(f"Murid tidak dijumpai: {student_id}")

    t0 = time.perf_counter()
    llm_feedback: dict = {}
    score_fn = None
    choice = mcq_choice(question, answer)
    if choice is not None:              # objective question: exact marking, no model needed
        question, answer, score_fn = mcq_marking(question, choice)
    elif live_scorer() != "b2":
        score_fn = lambda: _llm_score(question, answer, student_id, mem, llm_feedback)  # noqa: E731
    res = run_react(
        question, answer,
        search=search_notes, embed=embed,
        history=lambda topic_id: mem.history(student_id, topic_id),
        source=source_label,
        generate=llm_generate if use_llm else None,
        label_probs=llm_label_probs if use_llm else None,
        config=load_config(), examples=judge_examples(),
        use_llm_feedback=get_settings().llm_encouragement,
        score_fn=score_fn,
    )
    latency = int((time.perf_counter() - t0) * 1000)
    rubric = res.rubric.to_dict()
    trace = res.trace_dicts()
    if llm_feedback.get("text"):
        res.feedback["ai_feedback"] = {"rumi": llm_feedback["text"], "jawi": "", "config": llm_feedback["config"]}
    attempt_id, badges = None, []
    if save:
        saved = mem.record_attempt(student_id=student_id, question=question, answer=answer, rubric=rubric,
                                   feedback=res.feedback, trace=trace, latency_ms=latency)
        attempt_id, badges = saved["attempt_id"], saved["new_badges"]
    return Assessment(attempt_id, question_id, rubric["score"], rubric["max_marks"], rubric["percent"],
                      res.feedback, rubric["criteria"], trace, badges, latency)


LETTERS = "ABCD"


def mcq_choice(question: dict, answer: str) -> int | None:
    """Index of the option the pupil picked ("A".."D"), or None for an open answer."""
    a = answer.strip().upper().rstrip(".")
    return LETTERS.index(a) if question.get("mcq") and len(a) == 1 and a in LETTERS else None


def mcq_marking(question: dict, choice: int):
    """The objective version of a question as a one-criterion rubric (1 mark), plus its exact scorer.
    Returns (question to record and give feedback on, answer text to save, score_fn for run_react)."""
    from .rubric import CriterionResult, RubricResult

    m = question["mcq"]
    right = m["options"][m["answer"]]
    picked = m["options"][choice]
    label = lambda i, o: f"{LETTERS[i]}. {o['rumi'] or o['jawi']}"  # noqa: E731
    criterion = f"Jawapan betul: {label(m['answer'], right)}"
    q = {**question, "question_rumi": m["stem_rumi"], "question_jawi": m["stem_jawi"], "type": "mcq", "max_marks": 1,
         "rubric": [{"criterion": criterion, "marks": 1, "keywords": []}],
         "reference_answer_rumi": f"{label(m['answer'], right)}\n{m.get('explanation_rumi', '')}".strip(),
         "reference_answer_jawi": f"{LETTERS[m['answer']]}. {right['jawi']}"}
    ok = choice == m["answer"]

    def score_fn():
        c = CriterionResult(criterion=criterion, marks=1.0, awarded=1.0 if ok else 0.0, met="ya" if ok else "tidak",
                            layer="MCQ", evidence=f"Pilihan {LETTERS[choice]}")
        return RubricResult(criteria=[c], score=c.awarded, max_marks=1.0, config="mcq"), {"scorer": "mcq"}

    return q, label(choice, picked), score_fn


def _llm_score(question: dict, answer: str, student_id: int, mem: MemoryStore, out: dict):
    """Live marking with the configured LLM system (admin's choice, else KAFA_SCORER). Falls back to the local B2 scorer
    if the API fails or the budget is used up, so pupils are never blocked."""
    from .llm_marking import MarkConfig, mark
    from .rubric import CriterionResult, RubricResult, score_answer

    h = mem.history(student_id, question["topic_id"])
    weak = sorted(mem.all_mastery(student_id).values(), key=lambda m: m["mastery"])[:2]
    memory = {"mastery": h.mastery, "attempts": h.attempts, "recent_mistakes": h.repeated_mistakes,
              "weak_topics": [w["topic_id"].split("_", 2)[-1].replace("_", " ") for w in weak]}
    try:
        cfg = MarkConfig.parse(live_scorer())        # inside the try: a bad name in .env falls back to B2, not an error
        m = mark(question, answer, cfg, memory=memory)
        if not m.ok:
            raise RuntimeError(m.error)
    except Exception as e:  # noqa: BLE001 - any API problem: use the local scorer instead
        log.warning("Live marking fell back to B2 (%s: %s)", type(e).__name__, e)
        r = score_answer(question, answer, embed=embed, generate=None, config=load_config())
        return r, {"scorer": "b2 (fallback)", "fallback_reason": f"{type(e).__name__}: {e}"[:200]}
    crits = [CriterionResult(criterion=c["criterion"], marks=c["marks"], awarded=c["awarded"], met=c["met"],
                             layer=f"LLM-{c['layer']}", llm_reason=c["reason"]) for c in m.criteria]
    out.update(text=m.feedback, config=m.config)
    r = RubricResult(criteria=crits, score=m.score, max_marks=m.max_marks, llm_calls=m.usage.get("calls", 0),
                     config=m.config)
    return r, {"scorer": m.config, "llm_cost": m.usage.get("cost", 0.0),
               "retrieved": [c["id"] for c in m.context]}


def next_question(student_id: int, *, subject: str | None = None, topic_id: str | None = None,
                  level: int | None = None, memory: MemoryStore | None = None,
                  rng: random.Random | None = None) -> dict:
    """Adaptive question choice.

    Topic: the given one, else the weakest topic in the subject (unattempted
    topics count as mastery 0, so they come first in textbook order).
    Level: the given one (must be unlocked), else the highest unlocked level.
    Question: not among the last 5 answered in that topic, least-answered first.
    """
    mem = memory or get_memory()
    rng = rng or random.Random()
    bank = load_questions()
    meta = note_meta()
    mastery = mem.all_mastery(student_id)

    if topic_id is None:
        topics = sorted({q["topic_id"] for q in bank.values() if not subject or q["subject"] == subject},
                        key=lambda t: (mastery.get(t, {}).get("mastery", 0.0),
                                       meta.get(t, {}).get("bab", 0), t))
        if not topics:
            raise AssessmentError("Tiada topik untuk subjek ini.")
        topic_id = topics[0]

    unlocked = mastery.get(topic_id, {}).get("level_unlocked", 1)
    if level is None:
        level = unlocked
    elif level > unlocked:
        raise AssessmentError(f"Tahap {level} belum dibuka untuk topik ini.")

    pool = [q for q in bank.values() if q["topic_id"] == topic_id and q["level"] == level]
    if not pool:  # e.g. latihan-only topic at this level: fall back to any level <= unlocked
        pool = [q for q in bank.values() if q["topic_id"] == topic_id and q["level"] <= unlocked]
    if not pool:
        raise AssessmentError(f"Tiada soalan untuk topik {topic_id}.")
    recent = set(mem.history(student_id, topic_id).recent_question_ids)
    fresh = [q for q in pool if q["id"] not in recent] or pool
    rng.shuffle(fresh)
    return fresh[0]


def public_question(q: dict) -> dict:
    """Question fields safe to send to the student (no answers or rubric keywords).
    Objective questions also get their stem and options, never which option is correct."""
    out = {k: q.get(k) for k in ("id", "topic_id", "subject", "level", "type", "question_rumi",
                                 "question_jawi", "max_marks", "origin")} | {
        "criteria_count": len(q.get("rubric", []))}
    if q.get("mcq"):
        m = q["mcq"]
        out["choices"] = {"stem_rumi": m["stem_rumi"], "stem_jawi": m["stem_jawi"], "spelling": m.get("spelling", False),
                          "options": [{"rumi": o["rumi"], "jawi": o["jawi"]} for o in m["options"]]}
        out["max_marks"] = 1
    return out
