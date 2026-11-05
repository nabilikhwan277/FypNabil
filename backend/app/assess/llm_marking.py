"""LLM marking: the baselines and the proposed system of the blueprint (§4.4, §6.2).

Systems
  b1  Zero-shot LLM            rubric only, no textbook retrieval
  b2  Embedding similarity     the original local scorer (rules + bge-m3 similarity), no LLM
  b3  RAG + rubric             retrieve textbook text, mark in one LLM call
  b4  RAG + rubric + verifier  b3, then a second call checks the feedback against the text
  proposed                     hard rules + ReAct agent (A1 / A2 / A3) + student memory

ReAct types (proposed only)
  A1  vanilla: the model chooses tools in an open Thought -> Action -> Observation loop
  A2  constrained: code fixes the order (rubric -> retrieve -> memory -> mark), strict JSON
  A3  Reflexion: the A2 draft is reviewed by a critic (Year 5 leniency, syllabus limits) and may be revised

The hard rules of the proposed system decide exact Jawi spelling, Betul/Salah
items and answers that contradict the reference numbers. A plain keyword match
is NOT accepted by rule (it goes to the LLM), to avoid the "keyword illusion".
Marks are always added up in code.
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field

from ..llm_api import MODELS, Completion, complete, parse_json
from .decision import award
from .rubric import layer_a

SYSTEMS = ("b1", "b2", "b3", "b4", "proposed")
# Extra options for every model call, e.g. {"seed": 8, "use_cache": False} for the consistency repeats.
CALL_OPTIONS: dict = {}
REACT_TYPES = ("A1", "A2", "A3")
HARD_RULES = {"A-spelling", "A-truefalse", "A-keyword-conflict"}
VERDICTS = ("ya", "separa", "tidak")


@dataclass(frozen=True)
class MarkConfig:
    system: str = "proposed"
    model: str = "luna"
    rag: str = "R2"
    react: str = "A2"
    memory: bool = False

    @property
    def name(self) -> str:
        if self.system == "b2":
            return "b2"
        if self.system == "b1":
            return f"b1:{self.model}"
        if self.system in ("b3", "b4"):
            return f"{self.system}:{self.model}:{self.rag}"
        return f"proposed:{self.model}:{self.rag}:{self.react}:{'on' if self.memory else 'off'}"

    @classmethod
    def parse(cls, text: str) -> "MarkConfig":
        p = text.split(":")
        if p[0] not in SYSTEMS:
            raise ValueError(f"unknown system {p[0]}")
        model = p[1] if len(p) > 1 else "luna"
        if p[0] != "b2" and model not in MODELS:
            raise ValueError(f"unknown model {model}")
        return cls(system=p[0], model=model, rag=p[2] if len(p) > 2 else "R2",
                   react=p[3] if len(p) > 3 else "A2", memory=len(p) > 4 and p[4] == "on")


@dataclass
class MarkResult:
    config: str
    criteria: list[dict]
    score: float
    max_marks: float
    feedback: str
    context: list[dict] = field(default_factory=list)
    trace: list[dict] = field(default_factory=list)
    usage: dict = field(default_factory=dict)
    ok: bool = True
    error: str = ""

    @property
    def percent(self) -> float:
        return round(100 * self.score / self.max_marks, 1) if self.max_marks else 0.0

    def to_dict(self) -> dict:
        return asdict(self) | {"percent": self.percent}


# ------------------------------------------------------------------ prompts
MARKER_RULES = """You are an experienced KAFA teacher in Malaysia marking a Year 5 (age 10-11) pupil's answer for the UPKK exam (Ibadah/Fiqh, Jawi, Tajwid).
Mark EACH rubric criterion separately:
- "ya": the answer clearly meets the criterion. Same meaning is enough; wording may differ; small Rumi spelling slips are fine.
- "separa": the answer partly meets it (the right idea, but an important detail is missing or incomplete).
- "tidak": not met, wrong, or missing.
Rules:
1. Judge the meaning and the ruling, not keywords. An answer that uses the right words but states a wrong ruling, number, condition or order is "tidak".
2. Numbers (harakat, rakaat, takbir, ayat, kalimah) must be exactly right.
3. A Jawi spelling criterion needs exactly the textbook spelling.
4. Use only the rubric, the reference answer and the textbook text given. Do not add rulings from outside the syllabus.
5. Be fair to a 10-11 year old: accept simple everyday words when the meaning is right.
Keep each criterion "reason" short (at most 20 words).
Then write FEEDBACK for the pupil in simple Bahasa Melayu (Rumi script), 2-3 short sentences: what was good, what is missing or wrong, and the correct fact. Every fact in the feedback must come from the textbook text or the reference answer."""

MARK_SCHEMA = {
    "type": "object",
    "properties": {
        "criteria": {"type": "array", "items": {
            "type": "object",
            "properties": {"no": {"type": "integer"}, "verdict": {"type": "string", "enum": list(VERDICTS)},
                           "reason": {"type": "string"}},
            "required": ["no", "verdict", "reason"], "additionalProperties": False}},
        "feedback": {"type": "string"},
    },
    "required": ["criteria", "feedback"], "additionalProperties": False,
}

CRITIC_SCHEMA = {
    **MARK_SCHEMA,
    "properties": {**MARK_SCHEMA["properties"], "changes": {"type": "array", "items": {"type": "string"}}},
    "required": ["criteria", "feedback", "changes"],
}

VERIFY_SCHEMA = {
    "type": "object",
    "properties": {"supported": {"type": "boolean"}, "unsupported": {"type": "array", "items": {"type": "string"}},
                   "feedback": {"type": "string"}},
    "required": ["supported", "unsupported", "feedback"], "additionalProperties": False,
}

CRITIC_RULES = """You are a senior KAFA examiner reviewing a colleague's marking of a Year 5 (age 10-11) UPKK answer.
Check the draft marking criterion by criterion:
(a) Leniency right for a 10-11 year old: not too harsh on wording or small spelling slips, not generous to a wrong ruling.
(b) Keyword illusion: right words with a wrong ruling, number or order must be "tidak".
(c) Numbers must be exactly right.
(d) Syllabus boundary: only facts in the rubric, reference answer and textbook text count.
(e) Every fact in the feedback must be supported by the textbook text or the reference answer; fix or remove any that are not.
Return the FINAL marking for all criteria (keep correct verdicts), the final feedback in simple Bahasa Melayu (2-3 sentences), and "changes": a list of what you changed and why (empty if nothing)."""

VERIFY_RULES = """You check feedback written for a Year 5 KAFA pupil about their answer.
List every factual statement in the feedback that is NOT supported by the textbook text or the reference answer ("unsupported").
Then return the feedback rewritten so that every fact is supported (remove or correct the rest), in simple Bahasa Melayu, 2-3 sentences.
Keep the teacher's judgement: the marking result is given and is final, so the feedback must still say what the pupil got wrong or missed.
"supported" is true only if nothing had to change."""

A1_RULES = MARKER_RULES + """

You work step by step with tools. Reply each turn with ONE JSON object only:
{"thought": "<what you will do and why>", "action": "<tool name>", "input": {...}}
Tools:
- get_rubric   input {}                     -> the rubric criteria and the reference answer
- search_notes input {"query": "<words>"}   -> passages from the Year 5 textbook
- get_history  input {}                     -> the pupil's past mistakes in this topic (if known)
- submit_marks input {"criteria": [{"no": 1, "verdict": "ya|separa|tidak", "reason": "..."}], "feedback": "..."} -> your final marking; this ends the task
Look at the rubric and the textbook before you submit."""


def _rubric_text(q: dict) -> str:
    return "\n".join(f"{n}. {c['criterion']} ({c['marks']} markah)" for n, c in enumerate(q["rubric"], 1))


def _reference(q: dict) -> str:
    r, j = q.get("reference_answer_rumi", ""), q.get("reference_answer_jawi", "")
    return r + (f"\n(Jawi: {j})" if j and j != r else "")


def memory_text(memory: dict | None) -> str:
    """Limited memory (blueprint §6.4): mastery, the last 3 mistakes, 2 weakest topics."""
    if not memory:
        return ""
    parts = [f"Penguasaan topik ini: {round(100 * memory.get('mastery', 0))}% ({memory.get('attempts', 0)} cubaan)."]
    if memory.get("recent_mistakes"):
        parts.append("Kesilapan lalu: " + "; ".join(memory["recent_mistakes"][:3]) + ".")
    if memory.get("weak_topics"):
        parts.append("Topik lemah: " + ", ".join(memory["weak_topics"][:2]) + ".")
    return " ".join(parts)


def _user_prompt(q: dict, answer: str, *, context: str | None, memory: dict | None, fixed: dict[int, tuple],
                 with_reference: bool = True) -> str:
    out = [f"SOALAN (Tahap {q['level']}, {q['max_marks']} markah): {q.get('question_rumi', '')}",
           f"RUBRIK:\n{_rubric_text(q)}"]
    if with_reference:
        out.append(f"JAWAPAN RUJUKAN:\n{_reference(q)}")
    if context is not None:
        out.append(f"TEKS BUKU TEKS:\n<<<\n{context or '(tiada)'}\n>>>")
    if memory:
        out.append(f"SEJARAH MURID: {memory_text(memory)} Sebut kesilapan berulang dalam maklum balas hanya jika berkaitan.")
    if fixed:
        out.append("Kriteria yang sudah diputuskan oleh peraturan tepat (jangan ubah):\n"
                   + "\n".join(f"{n}. {v} ({why})" for n, (v, why) in sorted(fixed.items())))
    out.append(f"JAWAPAN MURID:\n<<<\n{answer}\n>>>")
    return "\n\n".join(out)


# ------------------------------------------------------------------ helpers
class _Run:
    """Collects usage and trace steps across the calls of one marking."""

    def __init__(self, cfg: MarkConfig):
        self.cfg = cfg
        self.trace: list[dict] = []
        self.usage = {"calls": 0, "tokens_in": 0, "tokens_out": 0, "cost": 0.0, "ms": 0, "cached": 0}

    def call(self, messages: list[dict], schema: dict | None, tag: str, max_tokens: int = 2000) -> Completion:
        c = complete(self.cfg.model, messages, schema=schema, max_tokens=max_tokens, tag=f"{self.cfg.name}:{tag}",
                     **CALL_OPTIONS)
        for k, v in c.usage().items():
            self.usage[k] = self.usage.get(k, 0) + v
        return c

    def step(self, thought: str, action: str, observation, t0: float) -> None:
        self.trace.append({"step": len(self.trace) + 1, "thought": thought, "action": action,
                           "observation": observation, "ms": int((time.perf_counter() - t0) * 1000)})


def _hard_rules(q: dict, answer: str) -> dict[int, tuple[str, str]]:
    ref = "\n".join(x for x in (q.get("reference_answer_rumi", ""), q.get("reference_answer_jawi", "")) if x)
    fixed = {}
    for n, c in enumerate(q["rubric"], 1):
        lay, met, ev = layer_a(q, [k for k in c.get("keywords", []) if k], answer, ref)
        if lay in HARD_RULES:
            fixed[n] = (met, {"A-spelling": "ejaan Jawi dibandingkan tepat", "A-truefalse": "pilihan Betul/Salah",
                              "A-keyword-conflict": "nombor bercanggah dengan jawapan rujukan"}[lay] + (f": {ev}" if ev else ""))
    return fixed


def _finish(cfg: MarkConfig, q: dict, data: dict | None, fixed: dict[int, tuple], run: _Run, context: list[dict],
            feedback: str | None = None) -> MarkResult:
    by_no = {}
    for c in (data or {}).get("criteria", []) or []:
        try:
            by_no[int(c.get("no"))] = c
        except (TypeError, ValueError):
            continue
    crits, complete_ = [], data is not None
    for n, c in enumerate(q["rubric"], 1):
        if n in fixed:
            met, why, layer = fixed[n][0], fixed[n][1], "rule"
        else:
            got = by_no.get(n, {})
            met = got.get("verdict") if got.get("verdict") in VERDICTS else None
            if met is None:
                complete_ = False
            met, why, layer = met or "tidak", str(got.get("reason", "")), "llm"
        crits.append({"no": n, "criterion": c["criterion"], "marks": float(c["marks"]), "met": met,
                      "awarded": award(float(c["marks"]), met), "layer": layer, "reason": why})
    fb = feedback if feedback is not None else str((data or {}).get("feedback", ""))
    return MarkResult(cfg.name, crits, float(sum(c["awarded"] for c in crits)), float(sum(c["marks"] for c in crits)),
                      fb, context, run.trace, run.usage, ok=complete_,
                      error="" if complete_ else "model reply missing or incomplete")


def _retrieve(cfg: MarkConfig, q: dict, answer: str, query: str | None = None):
    from ..kb.rag import retrieve

    return retrieve(query or f"{q.get('question_rumi', '')} {answer}", rag=cfg.rag, subject=q["subject"],
                    topic_id=q["topic_id"])


# ------------------------------------------------------------------ systems
def _b2(cfg: MarkConfig, q: dict, answer: str) -> MarkResult:
    from ..embeddings import embed
    from .decision import load_config
    from .rubric import score_answer

    t0 = time.perf_counter()
    r = score_answer(q, answer, embed=embed, generate=None, config=load_config())
    crits = [{"no": n, "criterion": c.criterion, "marks": c.marks, "met": c.met, "awarded": c.awarded,
              "layer": c.layer, "reason": c.evidence} for n, c in enumerate(r.criteria, 1)]
    usage = {"calls": 0, "tokens_in": 0, "tokens_out": 0, "cost": 0.0, "ms": int((time.perf_counter() - t0) * 1000), "cached": 0}
    return MarkResult(cfg.name, crits, r.score, r.max_marks, "", [], [], usage)


def _single(cfg: MarkConfig, q: dict, answer: str, memory: dict | None, *, rag: bool, fixed: dict) -> tuple:
    run = _Run(cfg)
    context, chunks = None, []
    if rag:
        t0 = time.perf_counter()
        got = _retrieve(cfg, q, answer)
        context, chunks = got.context, got.chunks()
        run.step("Apakah kata buku teks tentang soalan ini?", f"search_notes[{cfg.rag}]",
                 {"chunks": [{"id": c["id"], "section": c["section"]} for c in chunks]}, t0)
    t0 = time.perf_counter()
    msgs = [{"role": "system", "content": MARKER_RULES},
            {"role": "user", "content": _user_prompt(q, answer, context=context, memory=memory, fixed=fixed,
                                                     with_reference=cfg.system != "b1")}]
    c = run.call(msgs, MARK_SCHEMA, "mark")
    run.step("Kriteria manakah yang dipenuhi?", "score_rubric",
             {"criteria": (c.data or {}).get("criteria"), "feedback": (c.data or {}).get("feedback")}, t0)
    return run, c, chunks, context


def _b4_verify(run: _Run, q: dict, answer: str, criteria: list[dict], context: str, feedback: str) -> str:
    t0 = time.perf_counter()
    result = "; ".join(f"{c['no']}. {c['criterion']}: {c['met']}" for c in criteria)
    msgs = [{"role": "system", "content": VERIFY_RULES},
            {"role": "user", "content": f"SOALAN: {q.get('question_rumi', '')}\n\nJAWAPAN RUJUKAN:\n{_reference(q)}\n\n"
                                        f"TEKS BUKU TEKS:\n<<<\n{context}\n>>>\n\nJAWAPAN MURID:\n<<<\n{answer}\n>>>\n\n"
                                        f"KEPUTUSAN PEMARKAHAN: {result}\n\nMAKLUM BALAS:\n<<<\n{feedback}\n>>>"}]
    v = run.call(msgs, VERIFY_SCHEMA, "verify", max_tokens=600)
    run.step("Adakah maklum balas disokong oleh buku teks?", "verify_feedback", v.data, t0)
    return str((v.data or {}).get("feedback") or feedback)


def _a3_critic(run: _Run, q: dict, answer: str, context: str, memory: dict | None, fixed: dict, draft: dict) -> dict | None:
    t0 = time.perf_counter()
    msgs = [{"role": "system", "content": CRITIC_RULES},
            {"role": "user", "content": _user_prompt(q, answer, context=context, memory=memory, fixed=fixed)
                                        + "\n\nDRAF PEMARKAHAN:\n" + json.dumps(draft, ensure_ascii=False)}]
    c = run.call(msgs, CRITIC_SCHEMA, "critic")
    run.step("Adakah pemarkahan ini adil untuk murid Tahun 5 dan dalam sukatan?", "critic_review",
             {"changes": (c.data or {}).get("changes")}, t0)
    return c.data


def _a1(cfg: MarkConfig, q: dict, answer: str, memory: dict | None, fixed: dict, max_steps: int = 6) -> MarkResult:
    run = _Run(cfg)
    chunks: list[dict] = []
    first = (f"SOALAN (Tahap {q['level']}, {q['max_marks']} markah): {q.get('question_rumi', '')}\n"
             f"Bilangan kriteria rubrik: {len(q['rubric'])}\n")
    if fixed:
        first += "Kriteria yang sudah diputuskan oleh peraturan tepat (jangan ubah): " + \
                 "; ".join(f"{n}: {v}" for n, (v, _) in sorted(fixed.items())) + "\n"
    first += f"JAWAPAN MURID:\n<<<\n{answer}\n>>>"
    msgs = [{"role": "system", "content": A1_RULES}, {"role": "user", "content": first}]
    for _ in range(max_steps):
        t0 = time.perf_counter()
        c = run.call(msgs, None, "react_step", max_tokens=2000)
        act = parse_json(c.text) or {}
        action, inp = str(act.get("action", "")), act.get("input") or {}
        if action == "submit_marks":
            run.step(str(act.get("thought", "")), "submit_marks", inp, t0)
            return _finish(cfg, q, inp if isinstance(inp, dict) else None, fixed, run, chunks)
        if action == "get_rubric":
            obs = f"RUBRIK:\n{_rubric_text(q)}\n\nJAWAPAN RUJUKAN:\n{_reference(q)}"
        elif action == "search_notes":
            got = _retrieve(cfg, q, answer, query=str(inp.get("query") or q.get("question_rumi", "")))
            chunks = got.chunks()
            obs = f"TEKS BUKU TEKS:\n<<<\n{got.context or '(tiada)'}\n>>>"
        elif action == "get_history":
            obs = memory_text(memory) if memory else "Tiada sejarah murid untuk topik ini."
        else:
            obs = "Tindakan tidak sah. Gunakan get_rubric, search_notes, get_history atau submit_marks, dalam JSON."
        run.step(str(act.get("thought", "")), action or "invalid", obs[:400], t0)
        msgs += [{"role": "assistant", "content": c.text}, {"role": "user", "content": f"OBSERVATION:\n{obs}"}]
    res = _finish(cfg, q, None, fixed, run, chunks)
    res.error = f"no submit_marks within {max_steps} steps"
    return res


def mark(question: dict, answer: str, cfg: MarkConfig, memory: dict | None = None) -> MarkResult:
    """Mark one answer with one configuration. API errors propagate (the caller decides on fallback)."""
    if cfg.system == "b2":
        return _b2(cfg, question, answer)
    mem = memory if cfg.memory else None
    if cfg.system == "b1":
        run, c, chunks, _ = _single(cfg, question, answer, None, rag=False, fixed={})
        return _finish(cfg, question, c.data, {}, run, chunks)
    if cfg.system in ("b3", "b4"):
        run, c, chunks, context = _single(cfg, question, answer, None, rag=True, fixed={})
        res = _finish(cfg, question, c.data, {}, run, chunks)
        if cfg.system == "b4" and c.data is not None:
            res.feedback = _b4_verify(run, question, answer, res.criteria, context or "", res.feedback)
            res.trace, res.usage = run.trace, run.usage
        return res

    # proposed
    t0 = time.perf_counter()
    fixed = _hard_rules(question, answer)
    rules_ms = int((time.perf_counter() - t0) * 1000)
    if cfg.react == "A1":
        res = _a1(cfg, question, answer, mem, fixed)
    else:
        run, c, chunks, context = _single(cfg, question, answer, mem, rag=True, fixed=fixed)
        data = c.data
        if cfg.react == "A3" and data is not None:
            revised = _a3_critic(run, question, answer, context or "", mem, fixed, data)
            data = revised or data
        res = _finish(cfg, question, data, fixed, run, chunks)
    res.trace.insert(0, {"step": 0, "thought": "Peraturan tepat dahulu (ejaan Jawi, Betul/Salah, nombor).",
                         "action": "hard_rules", "observation": {str(n): v for n, (v, _) in fixed.items()},
                         "ms": rules_ms})
    return res
