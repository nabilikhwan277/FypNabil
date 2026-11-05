"""Re-score saved experiment runs against another reference (e.g. the final teacher marks).

The marking system's outputs do not depend on the reference marks, so a run made against guru_1's marks
can be scored against the settled final marks without calling any model again: the predictions are kept,
only `gold` changes. The E2 grounding file of a run (feedback vs textbook) is copied unchanged.
The provisional runs are moved to eval/results/experiments/provisional_<labels>/ (kept, not deleted),
so the dashboard shows only the final ones.

Usage: .venv\\Scripts\\python eval\\rescore.py guru_1      (runs on teacher:guru_1 -> final marks)
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "eval"))

import experiments as ex  # noqa: E402

from backend.app.assess.llm_marking import MarkConfig  # noqa: E402
from backend.app.questions import load_questions  # noqa: E402


def main(old_labels: str) -> None:
    qs = load_questions()
    final = {it["answer_id"]: [c["met"] for c in it["criteria"]] for it in ex.load_silver("teacher")}
    keep = ex.OUT / f"provisional_{old_labels}"
    keep.mkdir(exist_ok=True)
    for p in sorted(ex.OUT.glob(f"*__teacher-{old_labels}*.json")):
        if p.name.endswith(".grounding.json"):
            continue
        run = json.loads(p.read_text(encoding="utf-8"))
        items = [it | {"gold": final[it["answer_id"]]} for it in run["items"] if it["answer_id"] in final]
        new = run | {"labels": "teacher", "items": items, "summary": ex.summarise(items, qs),
                     "rescored_from": f"teacher:{old_labels}"}
        cfg = MarkConfig.parse(run["config"])
        out = ex.run_path(run["step"], cfg, "teacher", None, run["repeats"], "final")
        out.write_text(json.dumps(new, indent=1, ensure_ascii=False), encoding="utf-8")
        g = p.with_name(p.stem + ".grounding.json")
        if g.exists():
            shutil.copy2(g, out.with_name(out.stem + ".grounding.json"))
            shutil.move(g, keep / g.name)
        shutil.move(p, keep / p.name)
        print(f"{run['config']:<32} {run['step']}  QWK {run['summary']['overall'].get('qwk_band')} -> "
              f"{new['summary']['overall'].get('qwk_band')}  -> {out.name}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "guru_1")
