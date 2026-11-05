"""Open-weight models next to the API models (Experiment plan v3, Phase 3). No model is called.

Every model with the same setup on the 50 teacher answers: proposed system, R3, A2, memory off.
  marking      QWK [95% CI], paired difference from the best run (final_stats.py), exact, within 1 mark,
               QWK per subject (Ibadah / Jawi / Tajwid)
  reliability  answers with valid marks (the reply followed the marking format), failed answers
  cost         seconds per answer, $ per 100 answers, and for open models the GPU and precision used on Colab
  Jawi         the Jawi reading test (jawi_reading.py): spelling and reading, exact match
Run final_stats.py first (it reads every finished run).

Usage: .venv\\Scripts\\python eval\\open_models.py  -> eval/results/open_models.json/.md, docs/figures/results/fig_4_16_open_models.png
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "eval"))

from backend.app.llm_api import MODELS  # noqa: E402

RES = ROOT / "eval" / "results"
EXP = RES / "experiments"
ORDER = ("luna", "haiku", "llama", "qwen", "fanar", "sealion")
SUBJ = {"fiqh": "Ibadah", "jawi": "Jawi", "tajwid": "Tajwid"}


def config(model: str) -> str:
    return f"proposed:{model}:R3:A2:off"


def run_file(model: str) -> dict | None:
    """The finished run of this model's configuration on the 50 teacher answers."""
    for p in sorted(EXP.glob(f"*__proposed_{model}_R3_A2_off__teacherall.json")):
        r = json.loads(p.read_text(encoding="utf-8"))
        if r.get("complete", True) and r.get("labels") == "teacher":
            return r
    return None


def main() -> None:
    stats = {r["config"]: r for r in json.loads((RES / "final_stats.json").read_text(encoding="utf-8"))["runs"]}
    jawi_path = RES / "jawi_reading.json"
    jawi = json.loads(jawi_path.read_text(encoding="utf-8"))["models"] if jawi_path.exists() else {}
    rows = []
    for m in ORDER:
        r, s = run_file(m), stats.get(config(m))
        if not r or not s:
            continue
        summ = r["summary"]
        rows.append({
            "model": m, "label": MODELS[m].label, "open": MODELS[m].local, "colab": r.get("colab"),
            "qwk": s["qwk"], "ci": s["ci"], "vs_best": s.get("vs_best"), "exact": s["by_subject"]["all"]["exact"], "within_1": s["by_subject"]["all"]["within_1"],
            "by_subject": {g: s["by_subject"][g]["qwk"] for g in SUBJ},
            "valid_marks": summ.get("success_rate"), "failed": sum(not it["ok"] for it in r["items"] if it["rep"] == 0),
            "seconds_per_answer": round(summ["latency_ms"]["mean"] / 1000, 1), "cost_per_100": summ.get("cost_per_100"),
            "jawi": ({"spell": jawi[m]["summary"]["spell"]["exact"], "read": jawi[m]["summary"]["read"]["exact"],
                      "all": jawi[m]["exact_all"]} if m in jawi else None)})
    out = {"setup": "proposed system, R3 Parent-Document RAG, A2 Constrained ReAct, memory off; 50 teacher answers",
           "rows": rows}
    (RES / "open_models.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    (RES / "open_models.md").write_text(markdown(out), encoding="utf-8")
    figure(rows)
    print(markdown(out))


def _pct(v) -> str:
    return "–" if v is None else f"{v:.0%}"


def markdown(o: dict) -> str:
    md = ["# Open-weight vs API models (Phase 3)", "", f"Same setup for every model: {o['setup']}. QWK [95% bootstrap CI]; "
          "change = paired difference from the best run of all experiments (**bold** = significant).", "",
          "## Marking", "", "| Model | Where it ran | QWK [95% CI] | Change from best | Exact | Within 1 mark (2+ marks) | "
          + " | ".join(f"QWK {v}" for v in SUBJ.values()) + " |", "|---|---|---|---|---|---|" + "---|" * len(SUBJ)]
    for x in o["rows"]:
        c = x["colab"] or {}
        where = (f"Colab {c.get('gpu', '')}, {c.get('precision', '')}".strip(", ") if x["open"] else "OpenRouter API")
        v = x["vs_best"]
        ch = "best" if not v else (f"**{v['diff']:+.3f} [{v['ci'][0]:+.2f}, {v['ci'][1]:+.2f}]**" if v["significant"]
                                   else f"{v['diff']:+.3f} [{v['ci'][0]:+.2f}, {v['ci'][1]:+.2f}]")
        md.append(f"| {x['label']} | {where} | {x['qwk']:.3f} [{x['ci'][0]:.2f}, {x['ci'][1]:.2f}] | {ch} | "
                  f"{x['exact'][0]:.0%} | {x['within_1'][0]:.0%} | "
                  + " | ".join(f"{x['by_subject'][g][0]:.3f}" for g in SUBJ) + " |")
    md += ["", "## Reliability, speed and cost", "", "| Model | Valid marks (format followed) | Failed answers | Seconds / answer | $ / 100 answers |",
           "|---|---|---|---|---|"]
    md += [f"| {x['label']} | {_pct(x['valid_marks'])} | {x['failed']} | {x['seconds_per_answer']:.1f} | "
           f"{'free (Colab)' if x['open'] else '$' + format(x['cost_per_100'], '.3f')} |"
           for x in o["rows"]]
    md += ["", "## Jawi reading test (30 textbook words)", "", "| Model | Spelling (Rumi → Jawi) | Reading (Jawi → Rumi) | All |", "|---|---|---|---|"]
    md += [f"| {x['label']} | {_pct(x['jawi']['spell'])} | {_pct(x['jawi']['read'])} | {_pct(x['jawi']['all'])} |"
           for x in o["rows"] if x["jawi"]]
    return "\n".join(md) + "\n"


def figure(rows: list[dict]) -> None:
    import make_figures as MF
    plt = MF.plt
    MF.OUT.mkdir(parents=True, exist_ok=True)
    fig, (a, b) = plt.subplots(1, 2, figsize=(11, 3.8), gridspec_kw={"width_ratios": [1.3, 1]})
    labels = [x["label"].replace(" (open-weight)", "\n(open)") for x in rows]
    MF.HUMAN = json.loads((RES / "final_stats.json").read_text(encoding="utf-8"))["human"]["mean"]
    MF.bars_ci(a, labels, rows, highlight=None)
    a.set_title("Marking: QWK with the final teacher marks (95% CI)")
    a.tick_params(axis="x", labelsize=8)
    j = [x for x in rows if x["jawi"]]
    w = 0.38
    for k, (key, name) in enumerate((("spell", "Spelling (Rumi → Jawi)"), ("read", "Reading (Jawi → Rumi)"))):
        b.bar([i + (k - 0.5) * w for i in range(len(j))], [x["jawi"][key] for x in j], w * 0.92, color=MF.C[k], label=name,
              zorder=2)
    b.set_xticks(range(len(j)), [x["label"].replace(" (open-weight)", "\n(open)") for x in j], fontsize=8)
    b.set_ylim(0, 1)
    b.set_title("Jawi reading test: exact answers")
    b.legend(fontsize=8, loc="upper right")
    MF.save(fig, "fig_4_16_open_models.png")


if __name__ == "__main__":
    main()
