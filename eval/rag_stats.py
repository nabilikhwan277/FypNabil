"""RAG evaluation statistics (Experiment plan v3, Phase 1.1): 95% CIs and paired tests, overall and per subject.

Reads the per-question scores saved by rag_eval.py (no model is called):
  each RAG type x metric x (all, Ibadah, Jawi, Tajwid): mean with a 95% bootstrap interval
  paired differences between RAG types on the same questions: mean, 95% interval, p-value
Faithfulness exists only for answered questions, so its pairs use the questions both types answered.

Usage: .venv\\Scripts\\python eval\\rag_stats.py  -> eval/results/rag_stats.json and .md
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

import numpy as np

RES = Path(__file__).resolve().parent / "results"
REPS, SEED = 2000, 7
METRICS = [("context_precision", "Context precision"), ("context_recall", "Context recall"),
           ("faithfulness", "Faithfulness"), ("answer_relevancy", "Answer relevancy"),
           ("factual_correctness", "Factual correctness"), ("declined", "Declined (share)")]
GROUPS = {"all": "All", "fiqh": "Ibadah", "jawi": "Jawi", "tajwid": "Tajwid"}


def boot_mean(x: np.ndarray) -> list[float]:
    """Mean with a 95% percentile bootstrap interval."""
    b = x[np.random.default_rng(SEED).integers(0, len(x), (REPS, len(x)))].mean(axis=1)
    return [round(float(x.mean()), 3), round(float(np.percentile(b, 2.5)), 3), round(float(np.percentile(b, 97.5)), 3)]


def paired(a: np.ndarray, b: np.ndarray) -> dict:
    """Mean of (a - b) over the same questions, 95% interval and two-sided bootstrap p-value."""
    d = a - b
    bd = d[np.random.default_rng(SEED).integers(0, len(d), (REPS, len(d)))].mean(axis=1)
    p = 2 * min((bd <= 0).mean(), (bd >= 0).mean())
    lo, hi = float(np.percentile(bd, 2.5)), float(np.percentile(bd, 97.5))
    return {"diff": round(float(d.mean()), 3), "ci": [round(lo, 3), round(hi, 3)], "p": round(float(min(1.0, p)), 3),
            "n": len(d), "clear": lo > 0 or hi < 0}


def values(items: list[dict], metric: str) -> dict[str, float]:
    """question id -> value (declined counts as 1/0; faithfulness skipped when the question was declined)."""
    out = {}
    for it in items:
        v = float(it["declined"]) if metric == "declined" else it.get(metric)
        if v is not None:
            out[it["question_id"]] = float(v)
    return out


def main() -> None:
    d = json.loads((RES / "rag_eval.json").read_text(encoding="utf-8"))
    rags = {r["rag"]: r["items"] for r in d["rags"]}
    subject = {it["question_id"]: it["subject"] for it in next(iter(rags.values()))}
    in_group = lambda qid, g: g == "all" or subject[qid] == g  # noqa: E731

    summary, pairs = {}, {}
    for m, _ in METRICS:
        for rag, items in rags.items():
            vals = values(items, m)
            for g in GROUPS:
                x = np.array([v for q, v in vals.items() if in_group(q, g)])
                summary.setdefault(m, {}).setdefault(rag, {})[g] = boot_mean(x) + [len(x)] if len(x) else None
        for a, b in combinations(sorted(rags), 2):
            va, vb = values(rags[b], m), values(rags[a], m)          # b - a: e.g. R3 - R1
            for g in GROUPS:
                common = [q for q in va if q in vb and in_group(q, g)]
                if len(common) > 2:
                    pairs.setdefault(m, {}).setdefault(f"{b} - {a}", {})[g] = paired(
                        np.array([va[q] for q in common]), np.array([vb[q] for q in common]))

    res = {"date": datetime.now(timezone.utc).isoformat(timespec="seconds"), "source": "rag_eval.json",
           "questions": len(subject), "per_subject": {g: sum(s == g for s in subject.values()) for g in GROUPS if g != "all"},
           "resamples": REPS, "summary": summary, "pairs": pairs}
    (RES / "rag_stats.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    (RES / "rag_stats.md").write_text(markdown(res), encoding="utf-8")
    print(markdown(res))


def markdown(res: dict) -> str:
    md = [f"# RAG evaluation with 95% confidence intervals ({res['questions']} questions: "
          + ", ".join(f"{GROUPS[g]} {n}" for g, n in res["per_subject"].items()) + ")", "",
          "Mean [95% bootstrap interval]. Declined = share of answerable questions the system refused (lower is better).", ""]
    for m, label in METRICS:
        md += [f"## {label}", "", "| RAG type | " + " | ".join(GROUPS.values()) + " |", "|---|" + "---|" * len(GROUPS)]
        for rag, row in res["summary"][m].items():
            md.append(f"| {rag} | " + " | ".join(f"{v[0]:.3f} [{v[1]:.3f}, {v[2]:.3f}]" if v else "–" for v in row.values()) + " |")
        md += ["", "| Difference | " + " | ".join(GROUPS.values()) + " |", "|---|" + "---|" * len(GROUPS)]
        for pair, row in res["pairs"].get(m, {}).items():
            md.append(f"| {pair} | " + " | ".join(
                f"{v['diff']:+.3f} [{v['ci'][0]:+.3f}, {v['ci'][1]:+.3f}] p={v['p']}{' *' if v['clear'] else ''}" if v else "–"
                for v in (row.get(g) for g in GROUPS)) + " |")
        md.append("")
    md.append("\\* = clear difference: the 95% interval leaves out 0.")
    return "\n".join(md) + "\n"


if __name__ == "__main__":
    main()
