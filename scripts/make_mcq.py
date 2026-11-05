"""Objective (A, B, C, D) versions of the easier questions, so pupils can answer by tapping.

Which questions: every Tahap 1 question and the first half of the Tahap 2 questions of each topic
(in question-number order). Betul/Salah items already have tap buttons and are left as they are.
The original open questions, rubrics and reference answers are NOT changed (the experiments and the
teacher marking still use them); the objective version is stored next to them in data/mcq/<subject>.json
and the app shows it to pupils.

How each one is made
  1. Claude Haiku 5.5 writes the stem and 4 options (Rumi + Jawi) from the question, its reference
     answer and the topic's textbook note: the correct option comes from the reference answer, the three
     distractors are plausible but clearly wrong according to the note.
     Jawi spelling items ("Tulis ... dalam tulisan Jawi") get 4 Jawi spellings; the correct one must be
     exactly the rubric's spelling (checked in code).
  2. The correct option is placed at A, B, C or D in rotation, so the answers are spread evenly.
  3. GPT-6 Luna (another provider) checks that exactly one option is correct and that it is the right one.
     If not, the item is made again once with the checker's comments; if it still fails it is kept but
     marked check="needs_review".
All items are marked verified=false until a teacher reviews them (review sheet: data/mcq/semakan_mcq.csv).

Usage: .venv\\Scripts\\python scripts\\make_mcq.py [--limit N] [--force]
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import re
import sys
import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.app.llm_api import MODELS, complete, spent_usd  # noqa: E402
from backend.app.notes import note_body  # noqa: E402
from backend.app.questions import load_questions  # noqa: E402

OUT = ROOT / "data" / "mcq"
WRITER, CHECKER = "haiku", "luna"
LETTERS = "ABCD"

OPTION = {"type": "object", "properties": {"rumi": {"type": "string"}, "jawi": {"type": "string"}},
          "required": ["rumi", "jawi"], "additionalProperties": False}
WRITE_SCHEMA = {"type": "object", "properties": {
    "stem_rumi": {"type": "string"}, "stem_jawi": {"type": "string"},
    "correct": OPTION, "distractors": {"type": "array", "items": OPTION},
    "explanation_rumi": {"type": "string"}},
    "required": ["stem_rumi", "stem_jawi", "correct", "distractors", "explanation_rumi"], "additionalProperties": False}
CHECK_SCHEMA = {"type": "object", "properties": {
    "correct_option": {"type": "string", "enum": list(LETTERS)},
    "exactly_one_correct": {"type": "boolean"},
    "problems": {"type": "array", "items": {"type": "string"}}},
    "required": ["correct_option", "exactly_one_correct", "problems"], "additionalProperties": False}

WRITE_RULES = """You write objective (multiple-choice, 4 options) questions for Year 5 KAFA pupils (age 10-11) in Malaysia, for the UPKK exam.
Turn the given open question into ONE multiple-choice question with exactly one correct option.
- Stem: keep the original question if it has one answer. If it asks for several points (e.g. "Nyatakan tiga fadhilat"),
  rewrite it as "Antara berikut, yang manakah ...?" so that exactly ONE option is correct.
- correct: taken from the REFERENCE ANSWER (short and clear).
- distractors: 3 wrong options of the same kind (e.g. other numbers of harakat, other mad names, other solat), plausible
  for a pupil but clearly wrong according to the TEXTBOOK NOTE. Similar length to the correct option.
  Never use "Semua di atas", "Tiada di atas", or trick negatives. No option may also be correct.
- Simple Bahasa Melayu. Give every stem and option in Rumi AND in Jawi (standard DBP Jawi spelling; keep Arabic terms
  and Quranic words in their usual Arabic spelling).
- If you keep the original question unchanged, copy its Jawi text exactly.
- Jawi text must be written fully in Jawi (Arabic) letters: never put Latin letters inside a Jawi word.
- explanation_rumi: one short sentence saying why the correct option is right, from the textbook note."""

SPELLING_RULES = """You write objective Jawi-spelling questions for Year 5 KAFA pupils (age 10-11) in Malaysia.
The pupil must pick the correct Jawi spelling of a word.
- stem_rumi / stem_jawi: e.g. "Pilih ejaan Jawi yang betul bagi perkataan 'X'."
- correct.jawi: EXACTLY the CORRECT SPELLING given (copy it character by character). correct.rumi: "".
- distractors: 3 wrong Jawi spellings that pupils often write (missing or extra alif, wrong hamzah, ta marbutah vs ta,
  missing wau/ya, wrong letter for ng/ny/p/g/c). Each distractor's rumi is "". All four spellings must be different.
- explanation_rumi: one short sentence with the spelling rule, from the textbook note."""

CHECK_RULES = """You check a multiple-choice question for Year 5 KAFA pupils against the textbook note and reference answer.
Decide which option (A, B, C or D) is correct, whether exactly ONE option is correct, and list any problems
(more than one correct option, the marked answer wrong, an option outside the syllabus, unclear wording)."""

_rot_lock = threading.Lock()
_ARABIC = re.compile(r"[؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿]")
_LATIN = re.compile(r"[A-Za-zÀ-ɏ]")
JAWI_LATIN_OK = {"SWT", "S.W.T", "SAW", "S.A.W", "UPKK", "KAFA", "AI", "JAIS", "JAKIM"}


_QUOTED = re.compile(r"['‘’\"“”]([^'‘’\"“”]{1,60})['‘’\"“”]")


def bad_jawi(text: str) -> list[str]:
    """Words in a Jawi string that are broken by Latin letters (e.g. 'اڤakah', 'ڤوluh', 'ményi').

    Allowed on purpose: Rumi words in quotes (the word to spell, e.g. 'kemerdekaan'), short letters and
    affixes (a, i, u, -an, -i, em) and capital acronyms (UPSR, PETRONAS, SWT)."""
    text = text or ""
    quoted = {t for span in _QUOTED.findall(text) for t in re.split(r"[\s,،]+", span) if t}
    out = []
    for tok in re.split(r"[\s،,.;:!?؟()\[\]\"'‘’“”/]+", text):
        if not _LATIN.search(tok):
            continue
        if _ARABIC.search(tok):                     # Latin and Jawi letters in one word: always broken
            out.append(tok)
            continue
        core = tok.strip("-.")
        if tok in quoted or core in quoted or len(core) <= 3 or core.replace(".", "").isupper() \
                or core.upper() in JAWI_LATIN_OK:
            continue
        out.append(tok)
    return out


def pick() -> list[dict]:
    qs = load_questions()
    by_topic: dict[str, list[dict]] = defaultdict(list)
    out = []
    num = lambda q: int(re.search(r"_q(\d+)$", q["id"]).group(1)) if re.search(r"_q(\d+)$", q["id"]) else 0  # noqa: E731
    for q in qs.values():
        ref = (q.get("reference_answer_rumi") or "").strip().lower()
        if ref in ("betul", "salah") or "betul atau salah" in q["question_rumi"].lower():
            continue
        if q["level"] == 1:
            out.append(q)
        elif q["level"] == 2:
            by_topic[q["topic_id"]].append(q)
    for topic, items in by_topic.items():
        items.sort(key=num)
        out += items[: (len(items) + 1) // 2]   # first half of Tahap 2
    return sorted(out, key=lambda q: q["id"])


def is_spelling(q: dict) -> bool:
    """One-word spelling items ("Tulis perkataan 'X' dalam tulisan Jawi") whose ONLY rubric criterion is the
    exact Jawi spelling. Multi-part questions (rules + examples, several words) take the normal path, where the
    checker verifies the answer, because the rubric keyword there is not necessarily the word in the stem."""
    t = q["question_rumi"].lower()
    if q["subject"] != "jawi" or not ("tulisan jawi" in t or "jawikan" in t) or len(q["rubric"]) != 1:
        return False
    kws = [k for k in q["rubric"][0].get("keywords", []) if k]
    return bool(kws) and all(_ARABIC.search(k) and not _LATIN.search(k) for k in kws)


_ASKS_SPELLING = re.compile(r"ejaan jawi|tulis (?:perkataan|akronim|kata)\b|jawikan|ejaan yang betul")


KIND_SCHEMA = {"type": "object", "properties": {"options_are_spellings": {"type": "boolean"}},
               "required": ["options_are_spellings"], "additionalProperties": False}


def options_are_spellings(stem_rumi: str, options: list[dict]) -> bool:
    """Ask GPT-6 Luna whether the options ARE Jawi spellings to recognise (e.g. 4 ways to write 'KLCC')
    rather than statements (e.g. rules about spelling). Cached, so it costs nothing after the first time."""
    opts = "\n".join(f"{LETTERS[i]}. {o['jawi']}" for i, o in enumerate(options))
    c = complete(CHECKER, [{"role": "system", "content": "You classify multiple-choice options in a Jawi (Malay in Arabic script) lesson."},
                           {"role": "user", "content": f"QUESTION: {stem_rumi}\n\nOPTIONS (Jawi):\n{opts}\n\n"
                                                       "Are the options Jawi SPELLINGS of words, names or acronyms that the pupil must "
                                                       "recognise (true), or statements / explanations / rules (false)?"}],
                 schema=KIND_SCHEMA, max_tokens=300, tag="mcq:kind")
    return bool((c.data or {}).get("options_are_spellings"))


def jawi_only(q: dict, stem_rumi: str, options: list[dict]) -> bool:
    """Show the options in Jawi only when they ARE spellings (the pupil picks a Jawi spelling), or when the
    model mixed scripts (some options Jawi, some Rumi), which would give the answer away.
    Statements and explanations keep their Rumi text."""
    if is_spelling(q):
        return True
    pure_jawi = [bool(_ARABIC.search(o["rumi"] or "")) and not _LATIN.search(o["rumi"] or "") for o in options]
    if any(pure_jawi) and not all(pure_jawi):
        return True
    if q["subject"] != "jawi" or not _ASKS_SPELLING.search(stem_rumi.lower()):
        return False
    return options_are_spellings(stem_rumi, options)


def spelling_target(q: dict) -> str:
    """The exact Jawi spelling the rubric expects (first Arabic-script keyword)."""
    for c in q["rubric"]:
        for k in c.get("keywords", []):
            if re.search(r"[؀-ۿ]", k):
                return k
    return q.get("reference_answer_jawi", "")


def _note(q: dict) -> str:
    return (note_body(q["topic_id"]) or "")[:3500]


def write(q: dict, feedback: list[str] | None = None, writer: str = WRITER) -> dict | None:
    spelling = is_spelling(q)
    user = (f"OPEN QUESTION (Tahap {q['level']}):\nRumi: {q['question_rumi']}\nJawi: {q.get('question_jawi', '')}\n\n"
            f"REFERENCE ANSWER:\nRumi: {q.get('reference_answer_rumi', '')}\nJawi: {q.get('reference_answer_jawi', '')}\n\n"
            + (f"CORRECT SPELLING: {spelling_target(q)}\n\n" if spelling else "")
            + f"TEXTBOOK NOTE:\n<<<\n{_note(q)}\n>>>")
    if feedback:
        user += "\n\nA checker found these problems in your previous version; fix them:\n- " + "\n- ".join(feedback)
    c = complete(writer, [{"role": "system", "content": SPELLING_RULES if spelling else WRITE_RULES},
                          {"role": "user", "content": user}], schema=WRITE_SCHEMA, max_tokens=6000, tag="mcq:write")
    d = c.data
    if not d or len(d.get("distractors") or []) < 3:
        return None
    if spelling:
        d["correct"]["jawi"] = spelling_target(q)      # never trust the model with the key spelling
        d["correct"]["rumi"] = ""
        for x in d["distractors"]:
            x["rumi"] = ""
    return d


def check(q: dict, mcq: dict, checker: str = CHECKER) -> dict | None:
    opts = "\n".join(f"{LETTERS[i]}. {o['rumi'] or ''} | {o['jawi']}" for i, o in enumerate(mcq["options"]))
    c = complete(checker, [{"role": "system", "content": CHECK_RULES},
                           {"role": "user", "content": f"QUESTION: {mcq['stem_rumi']}\n\nOPTIONS:\n{opts}\n\nMARKED ANSWER: {LETTERS[mcq['answer']]}\n\n"
                                                       f"REFERENCE ANSWER: {q.get('reference_answer_rumi', '')} | {q.get('reference_answer_jawi', '')}\n\n"
                                                       f"TEXTBOOK NOTE:\n<<<\n{_note(q)}\n>>>"}],
                 schema=CHECK_SCHEMA, max_tokens=3000, tag="mcq:check")
    return c.data


ATTEMPTS = [(WRITER, CHECKER), (WRITER, CHECKER), (CHECKER, WRITER)]   # (writer, checker), never the same provider


def build(q: dict, position: int) -> dict | None:
    feedback, last = None, None
    for writer, checker in ATTEMPTS:
        d = write(q, feedback, writer)
        if d is None:
            continue
        distractors = [x for x in d["distractors"][:3]]
        if len({(o["rumi"].strip(), o["jawi"].strip()) for o in [d["correct"], *distractors]}) < 4:
            feedback = ["two or more options are the same"]
            continue
        jawi_problems = [w for t in [d["stem_jawi"], *(o["jawi"] for o in [d["correct"], *distractors])] for w in bad_jawi(t)]
        if d["stem_rumi"].strip().rstrip("?.") == q["question_rumi"].strip().rstrip("?.") and q.get("question_jawi"):
            d["stem_jawi"] = q["question_jawi"]          # unchanged stem: the bank's checked Jawi text
            jawi_problems = [w for o in [d["correct"], *distractors] for w in bad_jawi(o["jawi"])]
        if jawi_problems:
            feedback = [f"these Jawi words contain Latin letters, write them fully in Jawi letters: {', '.join(jawi_problems[:8])}"]
            continue
        rng = random.Random(q["id"])
        rng.shuffle(distractors)
        options = distractors[:position] + [d["correct"]] + distractors[position:]
        if jawi_only(q, d["stem_rumi"], options):
            options = [{"rumi": "", "jawi": o["jawi"]} for o in options]
        mcq = {"stem_rumi": d["stem_rumi"].strip(), "stem_jawi": d["stem_jawi"].strip(),
               "options": [{"rumi": o["rumi"].strip(), "jawi": o["jawi"].strip()} for o in options],
               "answer": position, "explanation_rumi": d["explanation_rumi"].strip(),
               "spelling": is_spelling(q), "generated_by": MODELS[writer].id, "checked_by": MODELS[checker].id,
               "verified": False}
        c = check(q, mcq, checker) or {}
        ok = c.get("exactly_one_correct") and c.get("correct_option") == LETTERS[position]
        if ok:
            mcq["check"] = "ok"
            return mcq
        feedback = (c.get("problems") or []) + ([f"the checker thinks the correct option is {c.get('correct_option')}"]
                                                 if c.get("correct_option") != LETTERS[position] else [])
        mcq["check"], mcq["check_problems"] = "needs_review", feedback
        last = mcq
    return last


def main(limit: int | None, force: bool, redo: list[str] | None = None) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    existing: dict[str, dict] = {}
    for p in OUT.glob("*.json"):
        existing.update(json.loads(p.read_text(encoding="utf-8")))
    for qid in redo or []:
        existing.pop(qid, None)
    qs0 = load_questions()
    for qid, m in list(existing.items()):
        if all(not o["rumi"] for o in m["options"]) and not jawi_only(qs0[qid], m["stem_rumi"], m["options"]):
            existing.pop(qid)          # statements lost their Rumi text earlier: make again
            print(f"  remake {qid}: its options are statements, they need their Rumi text", flush=True)
    todo = [q for q in pick() if force or q["id"] not in existing][: limit or None]
    print(f"{len(todo)} questions to convert ({len(existing)} already done)  (spent so far ${spent_usd():.4f})", flush=True)
    jobs = [(q, (len(existing) + i) % 4) for i, q in enumerate(todo)]
    done = 0

    def run(job):
        nonlocal done
        q, pos = job
        m = None
        for attempt in range(3):
            try:
                m = build(q, pos)
                break
            except Exception as e:  # noqa: BLE001 - one bad item must not stop the batch
                print(f"  {q['id']}: {type(e).__name__}: {e}" + (" (retrying in 30 s)" if attempt < 2 else ""), flush=True)
                if attempt < 2:
                    time.sleep(30)          # e.g. the internet connection dropped for a moment
        if m is None:
            return q, None
        with _rot_lock:
            done += 1
            if done % 25 == 0:
                print(f"  {done}/{len(todo)}  (spent ${spent_usd():.4f})", flush=True)
        return q, m

    with ThreadPoolExecutor(max_workers=4) as ex:
        results = list(ex.map(run, jobs))
    for q, m in results:
        if m:
            existing[q["id"]] = m
    by_subject: dict[str, dict] = defaultdict(dict)
    qs = load_questions()
    for qid, m in existing.items():
        if any(o["rumi"] for o in m["options"]) and jawi_only(qs[qid], m["stem_rumi"], m["options"]):
            m["options"] = [{"rumi": "", "jawi": o["jawi"]} for o in m["options"]]
    for qid, m in sorted(existing.items()):
        by_subject[qs[qid]["subject"]][qid] = m
    for subject, items in by_subject.items():
        (OUT / f"{subject}.json").write_text(json.dumps(items, indent=1, ensure_ascii=False), encoding="utf-8")
    review_sheet(existing, qs)
    n_ok = sum(m.get("check") == "ok" for m in existing.values())
    print(f"saved {len(existing)} objective questions ({n_ok} passed the check, {len(existing) - n_ok} need review) "
          f"-> {OUT}  (spent so far ${spent_usd():.4f})")
    failed = [q["id"] for q, m in results if not m]
    if failed:
        print("could not make:", failed)


def review_sheet(items: dict, qs: dict) -> None:
    """CSV for a teacher to check every objective question (Excel / Google Sheets)."""
    with (OUT / "semakan_mcq.csv").open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["question_id", "subject", "level", "check", "stem_rumi", "A", "B", "C", "D", "answer",
                    "explanation", "teacher_ok (ya/tidak)", "teacher_comment"])
        for qid, m in sorted(items.items()):
            q = qs[qid]
            opts = [(o["rumi"] + " | " if o["rumi"] else "") + o["jawi"] for o in m["options"]]
            w.writerow([qid, q["subject"], q["level"], m.get("check", ""), m["stem_rumi"], *opts, LETTERS[m["answer"]],
                        m["explanation_rumi"], "", ""])


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--redo", nargs="*", default=[], help="question ids to make again")
    a = ap.parse_args()
    main(a.limit or None, a.force, a.redo)
