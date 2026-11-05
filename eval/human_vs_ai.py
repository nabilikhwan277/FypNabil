"""Human vs AI marking, by subject (Experiment plan v3, Phase 1.2). No model is called.

For Ibadah, Jawi and Tajwid separately:
  1. agreement: teacher vs teacher (human baseline) next to system vs each teacher and system vs final marks
     (QWK on the 0-4 band with 95% bootstrap intervals; criterion-level agreement and Cohen's kappa)
  2. partial marks: how often each teacher, the final marks and the system give "separa"
  3. where the system differs from the final marks: stricter or more lenient, decided by a hard rule or by the LLM
  4. examples: the criteria where they differ, with the pupil answer, the 3 teachers' marks and comments,
     and the system's mark and reason
System = the best configuration in final_stats.json (first repeat).

Usage: .venv\\Scripts\\python eval\\human_vs_ai.py  -> eval/results/human_vs_ai.json and .md
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "eval"))

from final_stats import _bands, _boot_idx, _ci, _qwk_of, cohen  # noqa: E402
from scoring_lib import qwk  # noqa: E402
from teacher_compare import _meta, _scored, label_sets  # noqa: E402

from backend.app.questions import load_questions  # noqa: E402

RES = ROOT / "eval" / "results"
TEACHER = ROOT / "data" / "teacher"
SUBJECTS = {"fiqh": "Ibadah", "jawi": "Jawi", "tajwid": "Tajwid"}
ORDER = {"tidak": 0, "separa": 1, "ya": 2}
EXAMPLES = 6


def comments() -> dict[tuple[str, str], str]:
    """(answer id, teacher key) -> comment written in the Google Form."""
    names = json.loads((TEACHER / "agreement.json").read_text(encoding="utf-8"))["names"]
    key = {n.strip().lower(): f"guru_{i}" for i, n in enumerate(names, 1)}
    out = {}
    with (TEACHER / "responses.csv").open(encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            t = key.get(row.get("Nama guru", "").strip().lower())
            for col, text in row.items():
                m = re.match(r"(T\d{3}) Komen", col or "")
                if t and m and text and text.strip():
                    out[(m.group(1), t)] = text.strip()
    return out


def qwk_ci(gold_items: list[dict]) -> list[float]:
    g, p = _bands(gold_items)
    return [round(qwk(g, p), 3)] + _ci([_qwk_of(i, g, p) for i in _boot_idx(len(g))])


def main() -> None:
    qs, meta, sets = load_questions(), _meta(), label_sets()
    teachers = sorted(k for k in sets if k.startswith("guru_"))
    st = json.loads((RES / "final_stats.json").read_text(encoding="utf-8"))
    best = st["best"]
    run = next(json.loads(p.read_text(encoding="utf-8")) for p in sorted((RES / "experiments").glob("*__teacherall*.json"))
               if not p.name.endswith(".grounding.json") and json.loads(p.read_text(encoding="utf-8"))["config"] == best)
    sys_items = {r["answer_id"]: r for r in run["items"] if r["rep"] == 0}
    preds = {a: [c["met"] for c in r["criteria"]] for a, r in sys_items.items()}
    with (TEACHER / "marking_final.csv").open(encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    notes = comments()

    report = {"system": best, "teachers": teachers, "subjects": {}}
    for subj, label in [("all", "All")] + list(SUBJECTS.items()):
        ids = sorted(a for a in sets["final"] if subj == "all" or meta[a]["question_id"].split("_")[0] == subj)
        sub = lambda d: {a: d[a] for a in ids if a in d}  # noqa: E731
        # 1. answer-level agreement (QWK on bands)
        pairs = {f"{a} vs {b}": qwk_ci(sorted(_scored(sub(sets[a]), sub(sets[b]), qs, meta), key=lambda i: i["answer_id"]))
                 for a, b in combinations(teachers, 2)}
        human_mean = round(float(np.mean([v[0] for v in pairs.values()])), 3)
        system = {t: qwk_ci(_scored(sub(preds), sub(sets[t]), qs, meta)) for t in teachers + ["final"]}
        # criterion level
        crit = [(r, sys_items[r["answer_id"]]["criteria"][int(r["criterion_no"]) - 1]) for r in rows if r["answer_id"] in ids]
        pair_agree = {f"{a} vs {b}": round(np.mean([r[a] == r[b] for r, _ in crit]), 3) for a, b in combinations(teachers, 2)}
        teacher_kappa = round(float(np.mean([cohen([r[a] for r, _ in crit], [r[b] for r, _ in crit]) for a, b in combinations(teachers, 2)])), 3)
        # 2. partial marks
        separa = {t: round(np.mean([r[t] == "separa" for r, _ in crit]), 3) for t in teachers}
        separa |= {"final": round(np.mean([r["teacher_met"] == "separa" for r, _ in crit]), 3),
                   "system": round(np.mean([c["met"] == "separa" for _, c in crit]), 3)}
        # 3. differences from the final marks
        diff = Counter()
        examples = []
        for r, c in crit:
            final, mine = r["teacher_met"], c["met"]
            if final == mine:
                continue
            way = "stricter" if ORDER[mine] < ORDER[final] else "more lenient"
            diff[(way, "hard rule" if c["layer"] == "rule" else "LLM")] += 1
            examples.append({"answer_id": r["answer_id"], "question": r["question"], "student_answer": r["student_answer"],
                             "reference": r["reference_answer"], "criterion": r["criterion"],
                             "teachers": {t: r[t] for t in teachers}, "final": final, "system": mine, "way": way,
                             "layer": c["layer"], "reason": c.get("reason", ""),
                             "comments": {t: notes[(r["answer_id"], t)] for t in teachers if (r["answer_id"], t) in notes}})
        all_split = sum(len({r[t] for t in teachers}) == 3 for r, _ in crit)
        report["subjects"][subj] = {
            "label": label, "answers": len(ids), "criteria": len(crit),
            "human": {"pairs": pairs, "mean_qwk": human_mean, "criterion_agreement": pair_agree, "criterion_kappa": teacher_kappa,
                      "all_three_same": round(np.mean([len({r[t] for t in teachers}) == 1 for r, _ in crit]), 3),
                      "all_three_different": all_split},
            "system": {"qwk": system, "mean_qwk_teachers": round(float(np.mean([system[t][0] for t in teachers])), 3),
                       "criterion_agreement_final": round(np.mean([r["teacher_met"] == c["met"] for r, c in crit]), 3),
                       "criterion_kappa_final": cohen([c["met"] for _, c in crit], [r["teacher_met"] for r, _ in crit])},
            "separa_rate": separa,
            "differences": {f"{w} ({l})": n for (w, l), n in sorted(diff.items())},
            "differences_total": sum(diff.values()),
            "examples": examples,
        }
    (RES / "human_vs_ai.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    (RES / "human_vs_ai.md").write_text(markdown(report), encoding="utf-8")
    print(markdown(report).split("\n## Examples")[0])


def markdown(rep: dict) -> str:
    s = rep["subjects"]
    cols = list(s)
    head = "| | " + " | ".join(f"{s[c]['label']} (n={s[c]['answers']})" for c in cols) + " |"
    sep = "|---|" + "---|" * len(cols)
    f = lambda v: f"{v[0]:.3f} [{v[1]:.3f}, {v[2]:.3f}]"  # noqa: E731
    md = [f"# Human vs AI marking by subject (system: {rep['system']})", "",
          "## 1. Agreement (QWK on the 0–4 band, 95% CI)", "", head, sep]
    for pair in s["all"]["human"]["pairs"]:
        md.append(f"| Teacher {pair.replace('guru_', 'G')} | " + " | ".join(f(s[c]["human"]["pairs"][pair]) for c in cols) + " |")
    md.append("| **Teachers (mean of pairs)** | " + " | ".join(f"**{s[c]['human']['mean_qwk']:.3f}**" for c in cols) + " |")
    for t in rep["teachers"] + ["final"]:
        md.append(f"| System vs {'final marks' if t == 'final' else t.replace('guru_', 'G')} | "
                  + " | ".join(f(s[c]["system"]["qwk"][t]) for c in cols) + " |")
    md.append("| **System (mean over teachers)** | " + " | ".join(f"**{s[c]['system']['mean_qwk_teachers']:.3f}**" for c in cols) + " |")
    md += ["", "## Criterion level (ya / separa / tidak)", "", head, sep,
           "| Teachers: all 3 the same | " + " | ".join(f"{s[c]['human']['all_three_same']:.0%}" for c in cols) + " |",
           "| Teachers: all 3 different | " + " | ".join(str(s[c]["human"]["all_three_different"]) for c in cols) + " |",
           "| Teachers: Cohen's kappa (mean of pairs) | " + " | ".join(f"{s[c]['human']['criterion_kappa']:.3f}" for c in cols) + " |",
           "| System vs final: agreement | " + " | ".join(f"{s[c]['system']['criterion_agreement_final']:.0%}" for c in cols) + " |",
           "| System vs final: Cohen's kappa | " + " | ".join(f"{s[c]['system']['criterion_kappa_final']:.3f}" for c in cols) + " |",
           "", "## 2. How often a partial mark (separa) is given", "", head, sep]
    for who in rep["teachers"] + ["final", "system"]:
        md.append(f"| {who.replace('guru_', 'Teacher G')} | " + " | ".join(f"{s[c]['separa_rate'][who]:.0%}" for c in cols) + " |")
    kinds = sorted({k for c in cols for k in s[c]["differences"]})
    md += ["", "## 3. Where the system differs from the final marks (number of criteria)", "", head, sep]
    md += [f"| {k} | " + " | ".join(str(s[c]["differences"].get(k, 0)) for c in cols) + " |" for k in kinds]
    md.append("| **Total** | " + " | ".join(f"**{s[c]['differences_total']} of {s[c]['criteria']}**" for c in cols) + " |")
    md += ["", "## Examples (criteria where the system and the final marks differ)", ""]
    for c in cols[1:]:
        md += [f"### {s[c]['label']}", ""]
        for e in s[c]["examples"][:EXAMPLES]:
            md += [f"**{e['answer_id']}** · {e['question']}", f"- Pupil answer: {e['student_answer']}",
                   f"- Criterion: {e['criterion']}",
                   f"- Teachers: " + ", ".join(f"{t.replace('guru_', 'G')} {v}" for t, v in e["teachers"].items())
                   + f" → final **{e['final']}** · System: **{e['system']}** ({e['way']}, {e['layer']})",
                   f"- System's reason: {e['reason'] or '–'}"]
            md += [f"- Comment {t.replace('guru_', 'G')}: {txt}" for t, txt in e["comments"].items()]
            md.append("")
    return "\n".join(md) + "\n"


if __name__ == "__main__":
    main()
