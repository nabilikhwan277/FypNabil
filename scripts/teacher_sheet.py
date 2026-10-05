"""Teacher marking kit: replace the silver labels with real teacher marks.

1) export: write a CSV the teacher can open in Excel / Google Sheets.
   One row per (answer, rubric criterion). The teacher fills column
   `teacher_met` with ya / separa / tidak. Answers are taken from the TEST
   silver set by default (so teachers mark realistic answers); real student
   answers can be added as extra rows with a new answer_id.

       .venv\\Scripts\\python scripts\\teacher_sheet.py export [out.csv]

2) import: read the filled CSV back into data/teacher/teacher_test.json,
   in the same format as the silver sets, then run the evaluation on it:

       .venv\\Scripts\\python scripts\\teacher_sheet.py import filled.csv
       .venv\\Scripts\\python eval\\scoring_features.py teacher
       .venv\\Scripts\\python eval\\evaluate.py 0 teacher

Rows with an empty `teacher_met` are skipped (partially marked sheets work).
The silver label is NOT included in the sheet, so the teacher marks blind.
"""
from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "eval"))

from backend.app.assess.decision import award  # noqa: E402
from backend.app.questions import load_questions  # noqa: E402

FIELDS = ["answer_id", "question_id", "subject", "level", "question", "reference_answer", "student_answer",
          "criterion_no", "criterion", "marks", "teacher_met", "teacher_comment"]
OUT_DIR = ROOT / "data" / "teacher"
VALID = {"ya", "separa", "tidak"}


def export(path: Path) -> None:
    from silver import load_silver

    qs = load_questions()
    items = [i for i in load_silver("test") if i["family"] == "paraphrase" or i["kind"] in ("ref_rumi", "other_topic")]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as fh:   # BOM so Excel shows Jawi correctly
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        for it in items:
            q = qs[it["question_id"]]
            for n, c in enumerate(q["rubric"], 1):
                w.writerow({"answer_id": it["answer_id"], "question_id": q["id"], "subject": q["subject"],
                            "level": q["level"], "question": q["question_rumi"],
                            "reference_answer": q.get("reference_answer_rumi", ""), "student_answer": it["answer"],
                            "criterion_no": n, "criterion": c["criterion"], "marks": c["marks"],
                            "teacher_met": "", "teacher_comment": ""})
    print(f"wrote {path} ({len(items)} answers)")


def import_(path: Path) -> None:
    qs = load_questions()
    rows: dict[str, list[dict]] = defaultdict(list)
    with path.open(encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            rows[r["answer_id"]].append(r)
    out, skipped = [], 0
    for aid, rs in rows.items():
        q = qs.get(rs[0]["question_id"])
        mets = {int(r["criterion_no"]): r["teacher_met"].strip().lower() for r in rs}
        if q is None or len(mets) != len(q["rubric"]) or any(m not in VALID for m in mets.values()):
            skipped += 1
            continue
        crit = [{"criterion": c["criterion"], "met": mets[n]} for n, c in enumerate(q["rubric"], 1)]
        out.append({"question_id": q["id"], "answer_id": aid, "kind": aid.split("::")[-1], "script": "",
                    "answer": rs[0]["student_answer"], "criteria": crit,
                    "expected_score": sum(award(c["marks"], m["met"]) for c, m in zip(q["rubric"], crit)),
                    "label_source": "teacher", "comment": " | ".join(r["teacher_comment"] for r in rs if r["teacher_comment"])})
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    dest = OUT_DIR / "teacher_test.json"
    dest.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"imported {len(out)} fully-marked answers -> {dest} (skipped {skipped} incomplete)")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "export"
    if cmd == "export":
        export(Path(sys.argv[2]) if len(sys.argv) > 2 else OUT_DIR / "teacher_marking_sheet.csv")
    elif cmd == "import":
        import_(Path(sys.argv[2]))
    else:
        sys.exit(__doc__)
