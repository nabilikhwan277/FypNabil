"""Programmatic 'silver' answers whose correct mark is known by construction.

These do NOT replace teacher-marked answers. They test specific failure modes:
  ref_rumi / ref_jawi  - the reference answer itself            -> full marks
  jawi_typo            - Jawi spelling with one wrong letter      -> 0   (spelling items)
  rumi_for_jawi        - Rumi word given for a "write in Jawi" item -> 0
  number_swap          - the reference with a different number   -> 0   (1-criterion, numeric)
  tf_flip              - the opposite Betul/Salah                 -> 0
  dont_know            - "saya tidak tahu"                        -> 0
  other_topic          - reference answer of another topic        -> 0

Usage: .venv\\Scripts\\python scripts\\make_silver_programmatic.py
Writes data/silver/programmatic_{train,test}.json
"""
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.app.assess.matching import is_true_false  # noqa: E402
from backend.app.assess.rubric import is_spelling_criterion  # noqa: E402
from backend.app.questions import load_questions, load_split  # noqa: E402

rng = random.Random(2026)

# Jawi letter -> a plausible wrong letter a child might write.
LOOKALIKE = {"ڤ": "ف", "ݢ": "ك", "چ": "ج", "ڠ": "غ", "ۏ": "و", "ڽ": "ث", "ة": "ت", "ت": "ة",
             "ء": "ا", "ى": "ي", "ق": "ك", "ك": "ق", "ص": "س", "س": "ص", "ه": "ة"}
NUM_WORDS = ["dua", "empat", "lima", "enam", "tujuh", "tiga"]
NUM_RE = re.compile(r"\b(" + "|".join(NUM_WORDS) + r"|\d+)\b", re.I)


def typo(word: str) -> str | None:
    chars = list(word)
    idx = [i for i, c in enumerate(chars) if c in LOOKALIKE]
    if idx:
        i = rng.choice(idx)
        chars[i] = LOOKALIKE[chars[i]]
        return "".join(chars)
    letters = [i for i, c in enumerate(chars) if "\u0600" <= c <= "\u06FF"]
    if len(letters) > 3:
        del chars[rng.choice(letters[1:-1])]
        return "".join(chars)
    return None


def swap_number(text: str) -> str | None:
    m = NUM_RE.search(text)
    if not m:
        return None
    old = m.group(0).lower()
    choices = [w for w in NUM_WORDS if w != old and not (old.isdigit() and w == {"2": "dua", "4": "empat", "5": "lima", "6": "enam"}.get(old))]
    return text[: m.start()] + rng.choice(choices) + text[m.end():]


def item(q, kind, answer, script, expected):
    crit = [{"criterion": c["criterion"], "met": "ya" if expected == "full" else "tidak"} for c in q["rubric"]]
    score = q["max_marks"] if expected == "full" else 0
    return {"question_id": q["id"], "answer_id": f"{q['id']}::{kind}", "kind": kind, "script": script,
            "answer": answer, "criteria": crit, "expected_score": score, "label_source": "construction"}


def build(split: str) -> list[dict]:
    qs = load_questions()
    ids = [i for i in load_split(split) if i in qs]
    by_subject = {}
    for q in qs.values():
        by_subject.setdefault(q["subject"], []).append(q)
    out = []
    for qid in ids:
        q = qs[qid]
        kws_all = [c.get("keywords", []) for c in q["rubric"]]
        spelling_only = all(is_spelling_criterion(q, k) for k in kws_all)
        ref_r, ref_j = q.get("reference_answer_rumi", ""), q.get("reference_answer_jawi", "")
        if ref_j:
            out.append(item(q, "ref_jawi", ref_j, "jawi", "full"))
        if ref_r and not spelling_only:
            out.append(item(q, "ref_rumi", ref_r, "rumi", "full"))
        if spelling_only and len(q["rubric"]) == 1 and ref_j:
            bad = typo(ref_j.split()[0] if len(ref_j.split()) == 1 else ref_j)
            if bad and all(bad != k for k in kws_all[0]):
                out.append(item(q, "jawi_typo", bad, "jawi", "zero"))
            if ref_r:
                out.append(item(q, "rumi_for_jawi", ref_r, "rumi", "zero"))
        if len(q["rubric"]) == 1 and not spelling_only and not is_true_false(kws_all[0]):
            sw = swap_number(ref_r)
            if sw:
                out.append(item(q, "number_swap", sw, "rumi", "zero"))
        if len(q["rubric"]) == 1 and is_true_false(kws_all[0]):
            flip = "Betul" if "salah" in ref_r.lower() else "Salah"
            out.append(item(q, "tf_flip", flip, "rumi", "zero"))
        out.append(item(q, "dont_know", "saya tidak tahu", "rumi", "zero"))
        others = [o for o in by_subject[q["subject"]] if o["topic_id"] != q["topic_id"] and o.get("reference_answer_rumi")]
        if others:
            o = rng.choice(others)
            out.append(item(q, "other_topic", o["reference_answer_rumi"], "rumi", "zero"))
    return out


def main() -> None:
    d = ROOT / "data" / "silver"
    d.mkdir(parents=True, exist_ok=True)
    for split in ("train", "test"):
        items = build(split)
        (d / f"programmatic_{split}.json").write_text(json.dumps(items, indent=1, ensure_ascii=False), encoding="utf-8")
        print(split, len(items), dict(Counter(i["kind"] for i in items)))


if __name__ == "__main__":
    main()
