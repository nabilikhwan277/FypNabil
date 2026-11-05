"""One detailed table per RAG setting (behind each row of the summary table Setting | Options | Evidence | Selection).

For every setting of the settings study (rag_settings.json) and every option tested:
  retrieval: hit rate, evidence recall, precision, MRR (mean and 95% bootstrap CI), sections and characters read
  answers (chunk size, sections, context limit): faithfulness, factual correctness (mean, 95% CI), declined answers,
           out-of-syllabus declined
  change from the current option on the deciding metric (95% CI, p) and the deciding metric per subject
Minimum similarity gets its own table (rejections per threshold). No model is called.

Usage: .venv\\Scripts\\python eval\\rag_settings_detail.py  -> eval/results/rag_settings_detail.md
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

RES = Path(__file__).resolve().parent / "results"
REPS, SEED = 2000, 7
RETRIEVAL = [("hit_rate", "Hit rate"), ("evidence_recall", "Evidence recall"), ("precision", "Precision"), ("mrr", "MRR")]
ANSWERS = [("faithfulness", "Faithfulness"), ("factual_correctness", "Factual correctness")]


def ci(vals: list[float]) -> str:
    x = np.array([v for v in vals if v is not None], dtype=float)
    if not len(x):
        return "–"
    b = x[np.random.default_rng(SEED).integers(0, len(x), (REPS, len(x)))].mean(axis=1)
    return f"{x.mean():.3f} [{np.percentile(b, 2.5):.2f}, {np.percentile(b, 97.5):.2f}]"


def per(option: dict, metric: str, qids: list[str]) -> list:
    src = option.get("answer_items") if metric in dict(ANSWERS) else option.get("per_question")
    return [(src or {}).get(q, {}).get(metric) for q in qids]


def main() -> None:
    rs = json.loads((RES / "rag_settings.json").read_text(encoding="utf-8"))
    by_subj = {s["key"]: s for s in json.loads((RES / "rag_settings_by_subject.json").read_text(encoding="utf-8"))["settings"]}
    qids = [q["id"] for q in rs["questions"]]
    md = [f"# RAG settings study of {rs['rag']}: detailed tables", "",
          f"{rs['n']} answerable questions (15 per subject) + {sum(rs['oos'].values())} out-of-syllabus questions · answer model "
          f"{rs['generator']} · judge {rs['judge']}. Mean [95% bootstrap CI]. One setting is changed at a time; the others stay at "
          "the current value.", ""]
    for n, s in enumerate(rs["settings"], 1):
        md += [f"## {n}. {s['setting']}", "", f"*What it is:* {s['what']}.", ""]
        if s["key"] == "min_sim":
            steps = rs["similarity"]["steps"]
            md += ["| Threshold | Matched chunks removed | Answerable rejected (of 45) | Hit rate | Evidence recall | "
                   "General off-syllabus rejected (of 12) | Near-syllabus rejected (of 12) |", "|---|---|---|---|---|---|---|"]
            md += [f"| {t['threshold']:.2f}{' (current)' if t['threshold'] == 0 else ''} | {t['chunks_removed']:.0%} | "
                   f"{t['answerable_rejected']} | {t['hit_rate']:.3f} | {t.get('evidence_recall', 0):.3f} | {t['general_rejected']} | "
                   f"{t['near_rejected']} |" for t in steps]
            c = rs["similarity"]["top_cosine"]
            md += ["", f"Best-match cosine: answerable {c['answerable']['min']:.2f}–{c['answerable']['max']:.2f}, general "
                       f"off-syllabus up to {c['general']['max']:.2f}, near-syllabus up to {c['near']['max']:.2f}."]
        else:
            answers = any(o.get("answer_items") for o in s["options"])
            head = ["Option"] + [l for _, l in RETRIEVAL] + ["Sections read", "Characters read"]
            if answers:
                head += [l for _, l in ANSWERS] + ["Declined (of 45)", "Off-syllabus declined (of 24)"]
            md += ["| " + " | ".join(head) + " |", "|---" * len(head) + "|"]
            for o in s["options"]:
                row = [o["option"] + (" **(current)**" if o["current"] else "")]
                row += [ci(per(o, m, qids)) for m, _ in RETRIEVAL]
                row += [f"{o['metrics']['passages']:.2f}", f"{o['metrics']['chars']:,}"]
                if answers and o.get("answers"):
                    a = o["answers"]
                    row += [ci(per(o, m, qids)) for m, _ in ANSWERS]
                    row += [str(a["declined"]), str(sum(a["oos_declined"].values()))]
                md.append("| " + " | ".join(row) + " |")
            metric = "factual_correctness" if answers else "evidence_recall"
            md += ["", f"**Change from the current option ({metric.replace('_', ' ')})**", "",
                   "| Option | Change | 95% CI | Clear? (interval leaves out 0) |", "|---|---|---|---|"]
            for o in s["options"]:
                d = (o.get("diff") or {}).get(metric)
                if d:
                    clear = d[1] > 0 or d[2] < 0
                    md.append(f"| {o['option']} | {d[0]:+.3f} | [{d[1]:+.3f}, {d[2]:+.3f}] | {'yes' if clear else 'no'} |")
            if s["key"] in by_subj:
                b = by_subj[s["key"]]
                names = [x["label"] for x in b["subjects"].values()]
                md += ["", f"**Per subject ({b['metric'].replace('_', ' ')}; change from current in brackets)**", "",
                       "| Option | " + " | ".join(names) + " |", "|---|" + "---|" * len(names)]
                for name in [x["option"] for x in next(iter(b["subjects"].values()))["options"]]:
                    cells = []
                    for x in b["subjects"].values():
                        e = next(y for y in x["options"] if y["option"] == name)
                        cells.append(f"{e['mean']:.3f}" + ("" if e["current"] else
                                     f" ({e['vs_current']['diff']:+.3f}{', clear' if e['vs_current']['clear'] else ''})"))
                    md.append(f"| {name} | " + " | ".join(cells) + " |")
        md += ["", f"**Evidence:** {s['evidence']}", "", f"**Selection:** {s['selection']}", ""]
    (RES / "rag_settings_detail.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"-> {RES / 'rag_settings_detail.md'}  ({len(rs['settings'])} settings)")


if __name__ == "__main__":
    main()
