"""E1 with more than one teacher: compare the system with EACH teacher, and with the human baseline.

When teachers disagree, one "correct" mark is itself uncertain. The standard check in automated
marking is therefore:
  human baseline   teacher vs teacher agreement (how far two real markers agree)
  system vs each   the system's agreement with every teacher separately
  human level      the system agrees with the teachers at least as well as they agree with each other
plus the clear cases: answers (and criteria) where every teacher gave the same mark.

Reads the experiment runs on the teacher set (eval/results/experiments/*__teacher*.json) and the
label sets written by `scripts/teacher_sheet.py labels` (data/teacher/labels/). The system's marks
are re-scored against each label set, so nothing is re-run and no API credit is used.

Usage: .venv\\Scripts\\python eval\\teacher_compare.py   -> eval/results/teacher_compare.json (+ .md)
"""
from __future__ import annotations

import csv
import json
import re
import sys
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "eval"))

from scoring_lib import metrics  # noqa: E402

from backend.app.assess.decision import award  # noqa: E402
from backend.app.questions import load_questions  # noqa: E402

TEACHER = ROOT / "data" / "teacher"
LABELS = TEACHER / "labels"
EXP = ROOT / "eval" / "results" / "experiments"
OUT = ROOT / "eval" / "results" / "teacher_compare.json"


def label_sets() -> dict[str, dict[str, list[str]]]:
    """{set name: {answer_id: [met per criterion]}} for guru_1.., agreed and final (if settled)."""
    sets = {}
    for p in sorted(LABELS.glob("*.json")):
        sets[p.stem] = {it["answer_id"]: [c["met"] for c in it["criteria"]] for it in json.loads(p.read_text(encoding="utf-8"))}
    final = TEACHER / "teacher_test.json"
    if final.exists():
        sets["final"] = {it["answer_id"]: [c["met"] for c in it["criteria"]] for it in json.loads(final.read_text(encoding="utf-8"))}
    if not any(k.startswith("guru_") for k in sets):
        raise FileNotFoundError("no per-teacher labels: run scripts/teacher_sheet.py labels")
    return sets


def teacher_names() -> dict[str, str]:
    a = TEACHER / "agreement.json"
    names = json.loads(a.read_text(encoding="utf-8")).get("names", []) if a.exists() else []
    return {f"guru_{i}": n for i, n in enumerate(names, 1)}


def _scored(preds: dict[str, list[str]], gold: dict[str, list[str]], qs: dict, meta: dict) -> list[dict]:
    """Items in scoring_lib format for the answers present in both."""
    out = []
    for aid, g in gold.items():
        p = preds.get(aid)
        if p is None:
            continue
        qid = meta[aid]["question_id"]
        q = qs[qid]
        marks = [float(c["marks"]) for c in q["rubric"]]
        crits = [{"label": gm, "marks": m, "a_layer": None} for gm, m in zip(g, marks)]
        out.append({"answer_id": aid, "subject": q["subject"], "level": q["level"], "kind": meta[aid].get("kind", ""),
                    "max_marks": float(q["max_marks"]), "criteria": crits, "pred_mets": p,
                    "pred": sum(award(m, v) for m, v in zip(marks, p)), "gold": sum(award(m, v) for m, v in zip(marks, g))})
    return out


def _meta() -> dict:
    return {it["answer_id"]: it for it in json.loads((TEACHER / "teacher_set_key.json").read_text(encoding="utf-8"))}


def per_teacher_qwk(run: dict) -> float | None:
    """Mean QWK of one experiment run against every teacher (used to pick the best configuration)."""
    sets, qs, meta = label_sets(), load_questions(), _meta()
    preds = {r["answer_id"]: [c["met"] for c in r["criteria"]] for r in run["items"] if r["rep"] == 0}
    vals = [metrics(_scored(preds, sets[k], qs, meta)).get("qwk_band") for k in sets if k.startswith("guru_")]
    vals = [v for v in vals if v is not None]
    return round(sum(vals) / len(vals), 4) if vals else None


def agreed_criteria() -> dict[tuple[str, int], str]:
    """Criteria where every teacher gave the same mark (from marking_final.csv)."""
    path = TEACHER / "marking_final.csv"
    with path.open(encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    cols = [c for c in rows[0] if re.fullmatch(r"guru_\d+", c)]
    out = {}
    for r in rows:
        v = {r[c].strip().lower() for c in cols}
        if len(v) == 1:
            out[(r["answer_id"], int(r["criterion_no"]))] = v.pop()
    return out


def compare() -> dict:
    sets, qs, meta = label_sets(), load_questions(), _meta()
    names = teacher_names()
    gurus = [k for k in sets if k.startswith("guru_")]
    pick = lambda o: {k: o.get(k) for k in ("items", "qwk_band", "item_exact", "within_1", "mae_marks", "crit_acc",  # noqa: E731
                                           "over_marked", "under_marked")}
    human = {}
    for a, b in combinations(gurus, 2):
        human[f"{a} vs {b}"] = pick(metrics(_scored(sets[b], sets[a], qs, meta)))
    human_qwk = sum(h["qwk_band"] for h in human.values()) / len(human) if human else None
    human_exact = sum(h["item_exact"] for h in human.values()) / len(human) if human else None
    agreed_c = agreed_criteria()

    runs, seen = [], set()
    # the same configuration can appear in several steps (identical, cached marks): keep the latest step only
    files = sorted(EXP.glob("*__teacher*.json"), key=lambda f: f.name.split("__")[0], reverse=True)
    for p in files:
        if p.name.endswith(".grounding.json"):
            continue
        r = json.loads(p.read_text(encoding="utf-8"))
        if r["config"] in seen or not r.get("complete", True):
            continue
        seen.add(r["config"])
        preds = {it["answer_id"]: [c["met"] for c in it["criteria"]] for it in r["items"] if it["rep"] == 0}
        vs = {k: pick(metrics(_scored(preds, gold, qs, meta))) for k, gold in sets.items()}
        mean_qwk = sum(vs[g]["qwk_band"] for g in gurus) / len(gurus)
        mean_exact = sum(vs[g]["item_exact"] for g in gurus) / len(gurus)
        hits = [preds[aid][n - 1] == v for (aid, n), v in agreed_c.items() if aid in preds]
        runs.append({"file": p.name, "step": r["step"], "config": r["config"], "system": r["system"],
                     "model_label": r.get("model_label", ""), "rag": r.get("rag", ""), "react": r.get("react", ""),
                     "memory": r.get("memory", False), "n": r["n"], "vs": vs,
                     "mean_qwk_teachers": round(mean_qwk, 3), "mean_exact_teachers": round(mean_exact, 3),
                     "agreed_criteria_acc": round(sum(hits) / len(hits), 3) if hits else None,
                     "agreed_criteria_n": len(hits),
                     "human_level": None if human_qwk is None else mean_qwk >= human_qwk})
    runs.sort(key=lambda x: -x["mean_qwk_teachers"])
    res = {"date": datetime.now(timezone.utc).isoformat(timespec="seconds"), "teachers": {g: names.get(g, g) for g in gurus},
           "answers": len(meta), "agreed_answers": len(sets.get("agreed", {})), "agreed_criteria": len(agreed_c),
           "final_ready": "final" in sets, "human": human,
           "measure": "QWK of the answer score band (0-4), the same scale for teacher-vs-teacher and system-vs-teacher",
           "human_qwk": round(human_qwk, 3) if human_qwk is not None else None,
           "human_exact": round(human_exact, 3) if human_exact is not None else None, "runs": runs}
    OUT.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    _markdown(res)
    return res


def _markdown(res: dict) -> None:
    gurus = list(res["teachers"])
    head = "| Configuration | " + " | ".join(f"QWK vs {res['teachers'][g]}" for g in gurus) + \
           " | Mean QWK | Exact (mean) | Agreed criteria correct | Human level? |"
    md = ["# E1: system vs each teacher", "",
          f"Answers: {res['answers']} · fully agreed answers: {res['agreed_answers']} · agreed criteria: {res['agreed_criteria']}", "",
          "## Human baseline (teacher vs teacher)", "", "| Pair | QWK | Exact | Within 1 mark | MAE |", "|---|---|---|---|---|"]
    md += [f"| {k} | {v['qwk_band']:.3f} | {v['item_exact']:.1%} | {v['within_1']:.1%} | {v['mae_marks']:.2f} |" for k, v in res["human"].items()]
    md += ["", "## System vs teachers", "", head, "|" + "---|" * (len(gurus) + 5)]
    for r in res["runs"]:
        cells = " | ".join(f"{r['vs'][g]['qwk_band']:.3f}" for g in gurus)
        acc = f"{r['agreed_criteria_acc']:.1%}" if r["agreed_criteria_acc"] is not None else "-"
        md.append(f"| {r['config']} | {cells} | {r['mean_qwk_teachers']:.3f} | {r['mean_exact_teachers']:.1%} | {acc} | "
                  f"{'yes' if r['human_level'] else 'no'} |")
    md += ["", "Human level = the system's mean QWK with the teachers is at least the teachers' QWK with each other."]
    OUT.with_suffix(".md").write_text("\n".join(md) + "\n", encoding="utf-8")


if __name__ == "__main__":
    r = compare()
    print(f"human baseline QWK {r['human_qwk']}  (teachers: {', '.join(r['teachers'].values())})")
    for x in r["runs"]:
        print(f"  {x['config']:32s} mean QWK {x['mean_qwk_teachers']:.3f}  agreed-criteria acc {x['agreed_criteria_acc']}"
              f"  human level: {x['human_level']}")
    print("->", OUT)
