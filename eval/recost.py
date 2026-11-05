"""Put list-price costs into saved experiment results that counted cached calls as free.

Before the fix in llm_api.Completion.usage(), a rerun served from the cache showed $0, so the cost tables of
re-run configurations were too low. This tool repairs the saved files:
  - an answer whose calls were all fresh keeps its real billed cost (exact);
  - any other answer is priced from its token counts at each model's rate, fitted by least squares from the
    billed calls in the API log (storage/llm_calls.jsonl).
It first checks the fitted rates on the answers that were billed in full, and prints the error.
Dry run by default; --write updates summary.cost_total / cost_per_100 and adds cost_paid and cost_basis.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.config import get_settings  # noqa: E402

RESULTS = ROOT / "eval" / "results" / "experiments"
BASIS = "list price: billed where every call was fresh, else estimated from tokens (eval/recost.py)"


def fresh_answers() -> dict[str, list[tuple[int, int, float]]]:
    """(tokens in, tokens out, real cost) of every answer whose calls were all billed, per model."""
    by: dict[str, list[tuple[int, int, float]]] = defaultdict(list)
    for p in RESULTS.glob("*.json"):
        r = json.loads(p.read_text(encoding="utf-8"))
        for it in r.get("items", []):
            u = it.get("usage") or {}
            if u.get("calls") and not u.get("cached") and u.get("cost"):
                by[r.get("model")].append((u["tokens_in"], u["tokens_out"], u["cost"]))
    return by


def _lstsq(v: list[tuple[int, int, float]]) -> tuple[float, float]:
    a = np.array([[i, o] for i, o, _ in v], float)
    (pi, po), *_ = np.linalg.lstsq(a, np.array([c for *_, c in v]), rcond=None)
    return float(pi), float(po)


def fit_rates() -> dict[str, tuple[float, float]]:
    """Dollars per input and per output token for each API model, fitted on whole answers that were billed in full
    (an answer is the unit that gets priced, and it includes the provider's own input-caching discount)."""
    return {m: _lstsq(v) for m, v in fresh_answers().items() if len(v) >= 20}


def cross_check(folds: int = 5) -> dict[str, float]:
    """Out-of-sample error of the fitted rates: fit on 4/5 of the billed answers, price the other 1/5."""
    out = {}
    for m, v in fresh_answers().items():
        if len(v) < 20:
            continue
        est = real = 0.0
        for k in range(folds):
            train = [x for i, x in enumerate(v) if i % folds != k]
            rt = _lstsq(train)
            for i, o, c in (x for i, x in enumerate(v) if i % folds == k):
                est += i * rt[0] + o * rt[1]
                real += c
        out[m] = (est - real) / real
    return out


def price(u: dict, rate: tuple[float, float]) -> float:
    return u.get("tokens_in", 0) * rate[0] + u.get("tokens_out", 0) * rate[1]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    from backend.app.llm_api import MODELS
    rates = fit_rates()
    rate_of = {k: rates.get(k) for k, s in MODELS.items() if not s.local}
    for m, err in cross_check().items():
        print(f"check on answers the fit did not see: {m} {err:+.1%} (5-fold)")
    print(f"{'file':64s} {'recorded':>9s} {'list price':>10s}")
    for p in sorted(RESULTS.glob("*.json")):
        r = json.loads(p.read_text(encoding="utf-8"))
        rt = rate_of.get(r.get("model"))
        if not rt or all("list_cost" in (it.get("usage") or {}) for it in r["items"]):
            continue
        total = paid = 0.0
        for it in r["items"]:
            u = it["usage"]
            paid += u.get("cost", 0.0)
            u["list_cost"] = round(u["cost"] if (u.get("calls") and not u.get("cached")) else price(u, rt), 6)
            total += u["list_cost"]
        n = len(r["items"])
        s = r["summary"]
        print(f"{p.name:64s} {s['cost_total']:9.4f} {total:10.4f}")
        if args.write:
            s.update(cost_total=round(total, 6), cost_paid=round(paid, 6),
                     cost_per_100=round(total / n * 100, 4), cost_basis=BASIS)
            p.write_text(json.dumps(r, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
