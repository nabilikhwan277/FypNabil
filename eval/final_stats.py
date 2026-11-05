"""E1 statistics on the final teacher marks: how sure are the results?

For every configuration run on the 50 teacher answers (first repeat):
  QWK with a 95% bootstrap interval (2,000 resamples of the 50 answers)
  paired bootstrap test against the final system (same answers): mean difference, 95% interval, p
  QWK against EACH teacher (guru_1, guru_2, guru_3) and their mean, beside the human baseline
  (mean QWK of the teacher pairs, with its interval)
  Cohen's kappa per criterion (ya / separa / tidak) against the final marks
For the final system also the 3x3 confusion matrix of criterion verdicts (system vs final).
The final system is the one chosen for the thesis (FINAL; "best" in the JSON), not simply the highest QWK;
hybrids simulated from saved runs (Phase 4) are marked ‡.
A difference counts as significant only when its 95% interval leaves out 0 (p < 0.05).
No model is called.

Usage: .venv\\Scripts\\python eval\\final_stats.py  -> eval/results/final_stats.json and .md
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "eval"))

from scoring_lib import band, qwk  # noqa: E402
from teacher_compare import _meta, _scored, label_sets, teacher_names  # noqa: E402

from backend.app.questions import load_questions  # noqa: E402

EXP = ROOT / "eval" / "results" / "experiments"
OUT = ROOT / "eval" / "results" / "final_stats.json"
REPS, SEED = 2000, 7
VERDICTS = ("tidak", "separa", "ya")
FINAL = "proposed:luna:R3:A2:off"   # the final system (decided on 2 Nov 2026, experiment plan Phase 6)


def _bands(items: list[dict]) -> tuple[list[int], list[int]]:
    return [band(i["gold"], i["max_marks"]) for i in items], [band(i["pred"], i["max_marks"]) for i in items]


def _qwk_of(idx, gold: list[int], pred: list[int]) -> float:
    return qwk([gold[i] for i in idx], [pred[i] for i in idx])


def _boot_idx(n: int) -> np.ndarray:
    return np.random.default_rng(SEED).integers(0, n, (REPS, n))


def _ci(vals) -> list[float]:
    return [round(float(np.percentile(vals, 2.5)), 3), round(float(np.percentile(vals, 97.5)), 3)]


def cohen(a: list[str], b: list[str]) -> float:
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum((a.count(v) / n) * (b.count(v) / n) for v in VERDICTS)
    return round((po - pe) / (1 - pe), 3) if pe < 1 else 1.0


SUBJECTS = {"all": "All", "fiqh": "Ibadah", "jawi": "Jawi", "tajwid": "Tajwid"}


def group_stats(items: list[dict]) -> dict:
    """QWK, exact and within-1-mark of a group of answers, each with a 95% bootstrap interval."""
    gold, pred = _bands(items)
    exact = np.array([abs(i["pred"] - i["gold"]) < 1e-9 for i in items], dtype=float)
    within = np.array([abs(i["pred"] - i["gold"]) <= 1 + 1e-9 for i in items], dtype=float)
    idx = _boot_idx(len(items))
    return {"n": len(items),
            "qwk": [round(qwk(gold, pred), 3)] + _ci([_qwk_of(i, gold, pred) for i in idx]),
            "exact": [round(float(exact.mean()), 3)] + _ci(exact[idx].mean(axis=1)),
            "within_1": [round(float(within.mean()), 3)] + _ci(within[idx].mean(axis=1))}


def runs() -> list[dict]:
    """One run per configuration on the final teacher marks (Steps 0-4 and the extra checks)."""
    out = {}
    for p in sorted(EXP.glob("*__teacherall*.json")):
        if p.name.endswith(".grounding.json") or p.name.startswith("admin__"):
            continue
        r = json.loads(p.read_text(encoding="utf-8"))
        if r.get("labels") == "teacher" and r.get("complete", True):
            out.setdefault(r["config"], r)         # the same configuration in several steps: same answers
    return list(out.values())


def main() -> None:
    qs, meta, sets, names = load_questions(), _meta(), label_sets(), teacher_names()
    teachers = sorted(k for k in sets if k.startswith("guru_"))
    order = sorted(sets["final"])                  # the 50 answer ids, fixed order for paired resampling
    idx = _boot_idx(len(order))

    # human baseline: teacher pairs, on the same answers
    pair_vals, pair_q = [], {}
    for a, b in combinations(teachers, 2):
        items = _scored(sets[a], sets[b], qs, meta)
        ga, pb = _bands(sorted(items, key=lambda i: i["answer_id"]))
        pair_q[f"{a} vs {b}"] = round(qwk(ga, pb), 3)
        pair_vals.append([_qwk_of(i, ga, pb) for i in idx])
    human = {"pairs": pair_q, "mean": round(float(np.mean(list(pair_q.values()))), 3),
             "ci": _ci(np.mean(pair_vals, axis=0))}

    rows = {}
    for r in runs():
        preds = {x["answer_id"]: [c["met"] for c in x["criteria"]] for x in r["items"] if x["rep"] == 0}
        items = {i["answer_id"]: i for i in _scored(preds, sets["final"], qs, meta)}
        if len(items) != len(order):
            continue
        gold, pred = _bands([items[a] for a in order])
        boot = np.array([_qwk_of(i, gold, pred) for i in idx])
        per = {t: round(qwk(*_bands(_scored(preds, sets[t], qs, meta))), 3) for t in teachers}
        crit_p = [v for a in order for v in preds[a]]
        crit_g = [v for a in order for v in sets["final"][a]]
        rows[r["config"]] = {
            "config": r["config"], "step": r["step"], "model": r.get("model_label", ""), "rag": r.get("rag", ""),
            "react": r.get("react", ""), "memory": r.get("memory", False),
            "simulated": r.get("system") == "hybrid",
            "qwk": round(qwk(gold, pred), 3), "ci": _ci(boot), "boot": boot,
            "per_teacher": per, "mean_teachers": round(float(np.mean(list(per.values()))), 3),
            "above_human": round(float(np.mean(list(per.values()))), 3) > human["mean"],
            "criterion_kappa": cohen(crit_p, crit_g),
            "criterion_acc": round(sum(p == g for p, g in zip(crit_p, crit_g)) / len(crit_g), 3),
            "exact": r["summary"]["overall"].get("item_exact"), "within_1": r["summary"]["overall"].get("within_1"),
            "cost_per_100": r["summary"].get("cost_per_100"),
            "by_subject": {g: group_stats([items[a] for a in order if g == "all" or items[a]["subject"] == g]) for g in SUBJECTS},
            "confusion": {g: {p: sum(1 for x, y in zip(crit_g, crit_p) if x == g and y == p) for p in VERDICTS} for g in VERDICTS},
        }
    best = rows.get(FINAL) or max(rows.values(), key=lambda x: x["qwk"])
    for x in rows.values():
        if x is best:
            continue
        d = x["boot"] - best["boot"]
        p = 2 * min((d >= 0).mean(), (d <= 0).mean())
        x["vs_best"] = {"diff": round(x["qwk"] - best["qwk"], 3), "ci": _ci(d), "p": round(float(min(1.0, p)), 3),
                        "significant": bool(np.percentile(d, 97.5) < 0 or np.percentile(d, 2.5) > 0)}
    table = sorted(rows.values(), key=lambda x: -x["qwk"])
    for x in table:
        x.pop("boot")
    res = {"date": datetime.now(timezone.utc).isoformat(timespec="seconds"), "answers": len(order),
           "teachers": {t: names.get(t, t) for t in teachers}, "resamples": REPS, "human": human,
           "best": best["config"], "runs": table}
    OUT.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    OUT.with_suffix(".md").write_text(markdown(res), encoding="utf-8")
    print(markdown(res))


def markdown(res: dict) -> str:
    t = list(res["teachers"])
    h = res["human"]
    md = [f"# E1 statistics on the final teacher marks ({res['answers']} answers, {len(t)} teachers)", "",
          f"Human baseline (teacher vs teacher QWK): mean {h['mean']} (95% CI {h['ci'][0]}–{h['ci'][1]}); "
          + ", ".join(f"{k} {v}" for k, v in h["pairs"].items()), "",
          f"Reference for the comparisons: the final system, **{res['best']}**.", "",
          "| Configuration | QWK (final) | 95% CI | vs final system: diff (95% CI), p | " + " | ".join(f"QWK {x}" for x in t)
          + " | Mean of teachers | Criterion kappa | Criterion accuracy |",
          "|---|---|---|---|" + "---|" * len(t) + "---|---|---|"]
    for x in res["runs"]:
        vs = x.get("vs_best")
        vs_txt = "final system" if not vs else f"{vs['diff']:+.3f} ({vs['ci'][0]:+.3f} to {vs['ci'][1]:+.3f}), p={vs['p']}{' *' if vs['significant'] else ''}"
        mark = " ‡" if x.get("simulated") else ""
        md.append(f"| {x['config']}{mark} | {x['qwk']} | {x['ci'][0]}–{x['ci'][1]} | {vs_txt} | "
                  + " | ".join(str(x["per_teacher"][k]) for k in t)
                  + f" | {x['mean_teachers']}{' ↑' if x['above_human'] else ''} | {x['criterion_kappa']} | {x['criterion_acc']} |")
    for key, label in (("qwk", "QWK"), ("exact", "Exact agreement"), ("within_1", "Within 1 mark")):
        n = res["runs"][0]["by_subject"]
        md += ["", f"## {label} by subject, with 95% CI", "",
               "| Configuration | " + " | ".join(f"{SUBJECTS[g]} (n={n[g]['n']})" for g in SUBJECTS) + " |",
               "|---|" + "---|" * len(SUBJECTS)]
        md += [f"| {x['config']} | " + " | ".join(
            f"{v[0]:.3f} [{v[1]:.3f}, {v[2]:.3f}]" for v in (x["by_subject"][g][key] for g in SUBJECTS)) + " |" for x in res["runs"]]
    b = next(x for x in res["runs"] if x["config"] == res["best"])
    md += ["", "\\* = significantly different from the final system (95% interval leaves out 0). ↑ = above the human baseline. "
           "‡ = hybrid simulated from saved runs (Phase 4).", "",
           f"## Confusion matrix of criterion verdicts: {b['config']} (rows = final teacher mark, columns = system)", "",
           "| Teacher \\ System | tidak | separa | ya |", "|---|---|---|---|"]
    md += [f"| {g} | " + " | ".join(str(b["confusion"][g][p]) for p in VERDICTS) + " |" for g in VERDICTS]
    return "\n".join(md) + "\n"


if __name__ == "__main__":
    main()
