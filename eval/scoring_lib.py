"""Offline scoring over cached features (eval/cache/features_<split>.jsonl),
using the production decision logic (backend/app/assess/decision.py).
Shared by tune_scoring.py and evaluate.py."""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.app.assess.decision import (  # noqa: E402,F401
    PHASE4, Rule, ScoringConfig, award, credit, decide)

CACHE = ROOT / "eval" / "cache"
Config = ScoringConfig


def load_features(split: str) -> list[dict]:
    path = CACHE / f"features_{split}.jsonl"
    items = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    for it in items:
        for f in it["criteria"]:
            f["n_criteria"] = len(it["criteria"])
    return items


def score_items(items: list[dict], cfg: ScoringConfig) -> list[dict]:
    out = []
    for it in items:
        rule = cfg.rule_for(it["level"])
        mets = [decide(f, rule) for f in it["criteria"]]
        pred = sum(award(f["marks"], m) for f, m in zip(it["criteria"], mets))
        gold = sum(award(f["marks"], f["label"]) for f in it["criteria"])
        out.append({**it, "pred_mets": mets, "pred": pred, "gold": gold})
    return out


# ---------------------------------------------------------------- metrics
def qwk(a: list[int], b: list[int]) -> float:
    """Quadratic weighted kappa for integer ratings."""
    lo, hi = min(a + b), max(a + b)
    n = hi - lo + 1
    if n <= 1:
        return 1.0
    obs = [[0.0] * n for _ in range(n)]
    for x, y in zip(a, b):
        obs[x - lo][y - lo] += 1
    total = len(a)
    ra = [sum(r) for r in obs]
    rb = [sum(obs[i][j] for i in range(n)) for j in range(n)]
    num = den = 0.0
    for i in range(n):
        for j in range(n):
            wgt = (i - j) ** 2 / (n - 1) ** 2
            num += wgt * obs[i][j]
            den += wgt * ra[i] * rb[j] / total
    return 1.0 - num / den if den else 1.0


def band(score: float, max_marks: float) -> int:
    """0-4 band of the percentage score, comparable across questions."""
    return min(4, int(score / max_marks * 4 + 1e-9))


def metrics(scored: list[dict]) -> dict:
    if not scored:
        return {}
    n = len(scored)
    crit = [(f["label"], m, f["marks"], f["a_layer"]) for it in scored for f, m in zip(it["criteria"], it["pred_mets"])]
    unres = [c for c in crit if c[3] is None]
    err_marks = sum(abs(award(mk, p) - award(mk, g)) for g, p, mk, _ in crit)
    tot_marks = sum(mk for _, _, mk, _ in crit)
    # A 1-mark answer can never be more than 1 mark out, so it would always count as "within 1 mark" and inflate the
    # rate: within_1 counts only answers worth more than 1 mark; within_1_all keeps the old all-answers value.
    multi = [it for it in scored if it["max_marks"] > 1]
    return {
        "items": n, "criteria": len(crit), "unresolved_criteria": len(unres),
        "crit_acc": round(sum(g == p for g, p, _, _ in crit) / len(crit), 3),
        "unres_acc": round(sum(g == p for g, p, _, _ in unres) / len(unres), 3) if unres else None,
        "mark_err_rate": round(err_marks / tot_marks, 3),
        "item_exact": round(sum(abs(it["pred"] - it["gold"]) < 1e-9 for it in scored) / n, 3),
        "within_1": round(sum(abs(it["pred"] - it["gold"]) <= 1 + 1e-9 for it in multi) / len(multi), 3) if multi else None,
        "n_within_1": len(multi),
        "within_1_all": round(sum(abs(it["pred"] - it["gold"]) <= 1 + 1e-9 for it in scored) / n, 3),
        "mae_marks": round(sum(abs(it["pred"] - it["gold"]) for it in scored) / n, 3),
        "mae_pct": round(sum(abs(it["pred"] - it["gold"]) / it["max_marks"] for it in scored) / n * 100, 1),
        "qwk_units": round(qwk([round(it["gold"] * 2) for it in scored], [round(it["pred"] * 2) for it in scored]), 3),
        "qwk_band": round(qwk([band(it["gold"], it["max_marks"]) for it in scored],
                              [band(it["pred"], it["max_marks"]) for it in scored]), 3),
        "over_marked": round(sum(it["pred"] > it["gold"] + 1e-9 for it in scored) / n, 3),
        "under_marked": round(sum(it["pred"] < it["gold"] - 1e-9 for it in scored) / n, 3),
    }


def grouped(scored: list[dict], key) -> dict[str, dict]:
    g: dict[str, list] = defaultdict(list)
    for it in scored:
        g[key(it)].append(it)
    return {k: metrics(v) for k, v in sorted(g.items())}


def auc(pos: list[float], neg: list[float]) -> float | None:
    """P(score_pos > score_neg); ties count 0.5."""
    if not pos or not neg:
        return None
    wins = sum((p > q) + 0.5 * (p == q) for p in pos for q in neg)
    return round(wins / (len(pos) * len(neg)), 3)
