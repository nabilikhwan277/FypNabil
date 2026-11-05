"""RAG settings per subject (Experiment plan v3, Phase 1.5). No model is called.

Re-scores the saved settings study (rag_settings.json: every question's result for every option) separately for
Ibadah, Jawi and Tajwid. For each setting and subject: each option's mean, its paired difference from the current
option (95% bootstrap interval, p), and the best option. A subject gets its own setting only when another option is
clearly better there (interval leaves out 0) and not clearly worse on faithfulness.
Deciding metric: factual correctness where the answers were run (chunk size, sections, context limit), else
evidence recall.

Usage: .venv\\Scripts\\python eval\\rag_settings_by_subject.py  -> eval/results/rag_settings_by_subject.json and .md
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

RES = Path(__file__).resolve().parent / "results"
SUBJECTS = {"fiqh": "Ibadah", "jawi": "Jawi", "tajwid": "Tajwid"}
REPS, SEED = 2000, 7


def paired(a: list[float], b: list[float]) -> dict:
    d = np.array(a) - np.array(b)
    bd = d[np.random.default_rng(SEED).integers(0, len(d), (REPS, len(d)))].mean(axis=1)
    lo, hi = float(np.percentile(bd, 2.5)), float(np.percentile(bd, 97.5))
    return {"diff": round(float(d.mean()), 3), "ci": [round(lo, 3), round(hi, 3)],
            "p": round(float(min(1.0, 2 * min((bd <= 0).mean(), (bd >= 0).mean()))), 3), "clear": lo > 0 or hi < 0}


def values(option: dict, metric: str, qids: list[str]) -> list[float] | None:
    src = option.get("answer_items") if metric in ("factual_correctness", "faithfulness") else option.get("per_question")
    if not src:
        return None
    vals = [src.get(q, {}).get(metric) for q in qids]
    return vals if all(v is not None for v in vals) else None


def main() -> None:
    rs = json.loads((RES / "rag_settings.json").read_text(encoding="utf-8"))
    qids = [q["id"] for q in rs["questions"]]
    out = {"settings": []}
    for s in rs["settings"]:
        if s["key"] == "min_sim":
            continue          # a threshold rejects questions; handled by the similarity table, not per option
        metric = "factual_correctness" if any(o.get("answer_items") for o in s["options"]) else "evidence_recall"
        cur = next(o for o in s["options"] if o["current"])
        row = {"key": s["key"], "setting": s["setting"], "metric": metric, "current": cur["option"], "subjects": {}}
        for subj, label in SUBJECTS.items():
            ids = [q for q in qids if q.startswith(subj)]
            base = values(cur, metric, ids)
            opts = []
            for o in s["options"]:
                v = values(o, metric, ids)
                if v is None or base is None:
                    continue
                entry = {"option": o["option"], "mean": round(float(np.mean(v)), 3), "current": o["current"]}
                if not o["current"]:
                    entry["vs_current"] = paired(v, base)
                    if metric == "factual_correctness":
                        fa, fb = values(o, "faithfulness", ids), values(cur, "faithfulness", ids)
                        pairs = [(x, y) for x, y in zip(fa or [], fb or []) if x is not None and y is not None]
                        if len(pairs) > 2:
                            entry["faithfulness_vs_current"] = paired([x for x, _ in pairs], [y for _, y in pairs])
                opts.append(entry)
            better = [o for o in opts if not o["current"] and not o["option"].startswith("Rumi")   # Rumi = reference row
                      and o["vs_current"]["clear"] and o["vs_current"]["diff"] > 0
                      and not (o.get("faithfulness_vs_current", {}).get("clear") and o["faithfulness_vs_current"]["diff"] < 0)]
            pick = max(better, key=lambda o: o["mean"]) if better else next(o for o in opts if o["current"])
            row["subjects"][subj] = {"label": label, "n": len(ids), "options": opts, "selected": pick["option"],
                                     "own_setting": pick["option"] != cur["option"]}
        out["settings"].append(row)
    (RES / "rag_settings_by_subject.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    (RES / "rag_settings_by_subject.md").write_text(markdown(out), encoding="utf-8")
    print(markdown(out))


def markdown(o: dict) -> str:
    md = ["# RAG settings per subject (R3)", "",
          "Value = mean of the deciding metric; under it the change from the current option (95% CI). "
          "**bold** = clearly better than the current option in that subject.", "",
          "## Selection per subject", "", "| Setting | Deciding metric | Current | Ibadah | Jawi | Tajwid |", "|---|---|---|---|---|---|"]
    for s in o["settings"]:
        md.append(f"| {s['setting']} | {s['metric'].replace('_', ' ')} | {s['current']} | "
                  + " | ".join((f"**{x['selected']}** (own)" if x["own_setting"] else "same as current")
                               for x in s["subjects"].values()) + " |")
    for s in o["settings"]:
        md += ["", f"## {s['setting']} ({s['metric'].replace('_', ' ')})", "",
               "| Option | " + " | ".join(f"{x['label']} (n={x['n']})" for x in s["subjects"].values()) + " |",
               "|---|" + "---|" * len(s["subjects"])]
        options = [x["option"] for x in next(iter(s["subjects"].values()))["options"]]
        for name in options:
            cells = []
            for x in s["subjects"].values():
                e = next(y for y in x["options"] if y["option"] == name)
                if e["current"]:
                    cells.append(f"{e['mean']:.3f} (current)")
                    continue
                v = e["vs_current"]
                txt = f"{e['mean']:.3f} ({v['diff']:+.3f} [{v['ci'][0]:+.2f}, {v['ci'][1]:+.2f}])"
                cells.append(f"**{txt}**" if v["clear"] and v["diff"] > 0 else txt)
            md.append(f"| {name} | " + " | ".join(cells) + " |")
    return "\n".join(md) + "\n"


if __name__ == "__main__":
    main()
