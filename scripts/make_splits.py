"""Hold-out split of the question bank into train (80%) and test (20%).

Stratified by (subject, level) so each group keeps the same ratio.
Deterministic (seed 42). The test split must NOT be used for tuning.

Usage: .venv\\Scripts\\python scripts\\make_splits.py
Writes data/splits/train.json and data/splits/test.json (lists of question ids).
"""
import json
import random
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QB = ROOT / "data" / "questions"
OUT = ROOT / "data" / "splits"
SEED = 42
TEST_RATIO = 0.2


def main() -> None:
    groups: dict[tuple[str, int], list[str]] = defaultdict(list)
    for path in sorted(QB.glob("*/*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for q in data["questions"]:
            groups[(data["subject"], q["level"])].append(q["id"])

    rng = random.Random(SEED)
    train, test = [], []
    print(f"{'subject':<8}{'level':>6}{'total':>7}{'train':>7}{'test':>6}")
    for key in sorted(groups):
        ids = sorted(groups[key])
        rng.shuffle(ids)
        n_test = max(1, round(len(ids) * TEST_RATIO)) if len(ids) >= 2 else 0
        test += ids[:n_test]
        train += ids[n_test:]
        print(f"{key[0]:<8}{key[1]:>6}{len(ids):>7}{len(ids) - n_test:>7}{n_test:>6}")

    OUT.mkdir(parents=True, exist_ok=True)
    meta = {"seed": SEED, "test_ratio": TEST_RATIO, "stratify": ["subject", "level"]}
    for name, ids in (("train", train), ("test", test)):
        (OUT / f"{name}.json").write_text(
            json.dumps({**meta, "count": len(ids), "ids": sorted(ids)}, indent=1), encoding="utf-8"
        )
    print(f"\ntrain={len(train)} test={len(test)} -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
