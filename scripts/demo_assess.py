"""End-to-end demo of one assessment with the real models and a throwaway DB.
Usage: .venv\\Scripts\\python scripts\\demo_assess.py
Writes eval/results/demo_assess.json (full feedback + ReAct trace)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.app.assess import pipeline  # noqa: E402
from backend.app.memory.db import MemoryStore  # noqa: E402

CASES = [
    ("tajwid_b3_mad_badal_q1", "2 harakat"),
    ("tajwid_b3_mad_badal_q1", "enam harakat"),
    ("jawi_b3_pinjaman_inggeris_q1", "تيكنولوݢي"),
    ("fiqh_b1_solat_dhuha_q6", "Dimurahkan rezeki dan dimudahkan urusan"),
]


def main() -> None:
    mem = MemoryStore(":memory:")
    sid = mem.get_or_create_student("Demo", "5 Bestari")["id"]
    out = []
    for qid, answer in CASES:
        r = pipeline.assess(sid, qid, answer, memory=mem)
        fb = r.feedback
        print(f"\n[{qid}] answer={answer!r}  ->  {r.score}/{r.max_marks} ({r.percent}%), {fb['stars']} stars, {r.latency_ms} ms")
        print("  verdict:", fb["verdict"]["rumi"])
        for m in fb["mistakes"]:
            print("  missed :", m["rumi"])
        print("  answer :", fb["correct_answer"]["rumi"][:100], "|", fb["source"]["rumi"])
        print("  next   :", fb["suggestion"]["rumi"])
        print("  cheer  :", fb["encouragement"]["rumi"], f"({fb['encouragement']['source']})")
        print("  layers :", [(c["layer"], c["met"]) for c in r.criteria])
        out.append({"question_id": qid, "answer": answer, **r.to_dict()})
    path = ROOT / "eval" / "results" / "demo_assess.json"
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nsaved {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
