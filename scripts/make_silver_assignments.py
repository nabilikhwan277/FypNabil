"""Pick questions for hand-written (paraphrased) silver answers and write one
assignment file per split x subject for the answer writers.

train: per subject ~20 L2/L3 + 10 L1 (sampled)   test: all L2/L3 + ~7 L1 per subject
Writes data/silver/_assign/<split>_<subject>.json
"""
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.app.questions import load_questions, load_split  # noqa: E402

rng = random.Random(99)
PLAN = {"train": {"high": 20, "l1": 10}, "test": {"high": None, "l1": 7}}  # None = all


def main() -> None:
    qs = load_questions()
    out_dir = ROOT / "data" / "silver" / "_assign"
    out_dir.mkdir(parents=True, exist_ok=True)
    for split, plan in PLAN.items():
        ids = [i for i in load_split(split) if i in qs]
        for subject in ("fiqh", "jawi", "tajwid"):
            sub = [qs[i] for i in ids if qs[i]["subject"] == subject]
            high = sorted((q for q in sub if q["level"] >= 2), key=lambda q: q["id"])
            l1 = sorted((q for q in sub if q["level"] == 1), key=lambda q: q["id"])
            rng.shuffle(high)
            rng.shuffle(l1)
            chosen = (high if plan["high"] is None else high[: plan["high"]]) + l1[: plan["l1"]]
            items = [{
                "question_id": q["id"], "topic_id": q["topic_id"], "level": q["level"], "type": q["type"],
                "note_file": f"data/knowledge/{subject}/{q['topic_id']}.md",
                "question_rumi": q.get("question_rumi", ""), "question_jawi": q.get("question_jawi", ""),
                "reference_answer_rumi": q.get("reference_answer_rumi", ""),
                "reference_answer_jawi": q.get("reference_answer_jawi", ""),
                "rubric": [{"criterion": c["criterion"], "marks": c["marks"], "keywords": c.get("keywords", [])}
                           for c in q["rubric"]],
                "max_marks": q["max_marks"],
            } for q in sorted(chosen, key=lambda q: q["id"])]
            path = out_dir / f"{split}_{subject}.json"
            path.write_text(json.dumps(items, indent=1, ensure_ascii=False), encoding="utf-8")
            print(f"{path.name}: {len(items)} questions")


if __name__ == "__main__":
    main()
