"""Load the silver answer sets (NOT teacher-marked; see data/silver/README.md)."""
from __future__ import annotations

import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SILVER = ROOT / "data" / "silver"


def load_silver(split: str, programmatic_sample: int | None = None, seed: int = 11) -> list[dict]:
    """Paraphrase items (all) + programmatic items (optionally sampled).

    Sampling keeps tuning fast: every paraphrase item is used; programmatic
    items are subsampled per kind so each failure mode stays represented.
    """
    if split == "teacher":   # teacher-marked answers imported by scripts/teacher_sheet.py
        items = json.loads((ROOT / "data" / "teacher" / "teacher_test.json").read_text(encoding="utf-8"))
        for it in items:
            it["family"] = "teacher"
        return items
    items: list[dict] = []
    for p in sorted(SILVER.glob(f"paraphrase_{split}_*.json")):
        items += json.loads(p.read_text(encoding="utf-8"))
    prog = json.loads((SILVER / f"programmatic_{split}.json").read_text(encoding="utf-8"))
    if programmatic_sample:
        rng = random.Random(seed)
        by_kind: dict[str, list] = {}
        for it in prog:
            by_kind.setdefault(it["kind"], []).append(it)
        per_kind = max(1, programmatic_sample // len(by_kind))
        prog = [it for k in sorted(by_kind) for it in rng.sample(by_kind[k], min(per_kind, len(by_kind[k])))]
    items += prog
    for it in items:
        it["family"] = "paraphrase" if it.get("label_source") == "silver_writer" else "programmatic"
    return items
