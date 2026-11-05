"""Thesis figures and tables for every experiment, from the saved result files (no model is called).

  Step 1  LLM models                 fig_4_01_llm_models.png
  Step 0  baselines vs proposed      fig_4_02_baselines.png
  Step 2  RAG types (marking)        fig_4_03_rag_marking.png
  RAG     RAGAS metrics per type     fig_4_04_rag_ragas.png
  RAG     settings: sections, threshold   fig_4_05_rag_sections.png, fig_4_06_min_similarity.png
  Step 3  ReAct types                fig_4_07_react.png
  Step 4  memory on / off            fig_4_08_memory.png
  All     QWK vs API cost            fig_4_09_qwk_vs_cost.png
  E1      each teacher               fig_4_10_per_teacher.png
  E1      confusion matrix           fig_4_11_confusion.png
  E1      by subject and level       fig_4_12_subject_level.png
  + tables.md (one table per experiment)

Inputs: eval/results/final_stats.json (run eval/final_stats.py first), rag_eval.json, rag_settings.json,
eval/results/experiments/*.json.
Usage: .venv\\Scripts\\python eval\\make_figures.py   -> docs/figures/results/
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "eval" / "results"
EXP = RES / "experiments"
OUT = ROOT / "docs" / "figures" / "results"

# validated categorical palette (fixed order), text and grid colours; light background for print
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
INK, INK2, GRID, MUTED = "#0b0b0b", "#52514e", "#e6e5e0", "#9b9a95"
TARGET, HUMAN = 0.70, None

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": MUTED, "axes.labelcolor": INK2,
    "xtick.color": INK2, "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "axes.grid.axis": "y", "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
    "figure.dpi": 100, "savefig.dpi": 220, "savefig.bbox": "tight", "axes.titleweight": "bold", "axes.titlesize": 11,
    "axes.titlecolor": INK, "legend.frameon": False,
})

NAMES = {
    "b2": "B2 Rules + bge-m3", "b1:luna": "B1 Zero-shot", "b3:luna:R1": "B3 RAG + rubric", "b4:luna:R1": "B4 RAG + verifier",
}
MODEL = {"haiku": "Claude Haiku 5.5", "luna": "GPT-6 Luna", "llama": "Llama 3.1 8B", "qwen": "Qwen3-4B", "fanar": "Fanar 9B",
         "sealion": "SEA-LION v3 9B"}


def load(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def name(cfg: str) -> str:
    if cfg in NAMES:
        return NAMES[cfg]
    p = cfg.split(":")
    return f"{MODEL.get(p[1], p[1])} · {p[2]} · {p[3]}" + (" · memory on" if p[4] == "on" else "")


def save(fig, file: str) -> None:
    fig.savefig(OUT / file, facecolor="white")
    plt.close(fig)
    print("  ", file)


def bars_ci(ax, labels, rows, color=C[0], human=True, highlight=None):
    """QWK bars with 95% bootstrap intervals, the 0.70 target and the teacher-vs-teacher line."""
    vals = [r["qwk"] for r in rows]
    lo = [r["qwk"] - r["ci"][0] for r in rows]
    hi = [r["ci"][1] - r["qwk"] for r in rows]
    cols = [C[1] if highlight is not None and i == highlight else color for i in range(len(rows))]
    ax.bar(labels, vals, color=cols, width=0.6, edgecolor="white", linewidth=1.5, zorder=2)
    ax.errorbar(labels, vals, yerr=[lo, hi], fmt="none", ecolor=INK2, elinewidth=1, capsize=4, zorder=3)
    for i, v in enumerate(vals):
        ax.text(i, 0.03, f"{v:.3f}", ha="center", va="bottom", color="white", fontweight="bold", fontsize=9, zorder=4)
    ax.axhline(TARGET, color=INK, linestyle="--", linewidth=1, zorder=1, label="Target QWK 0.70")
    if human:
        ax.axhline(HUMAN, color=MUTED, linestyle=":", linewidth=1.4, zorder=1,
                   label=f"Teachers vs each other ({HUMAN:.3f})")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2, fontsize=8)
    ax.set_ylim(0, 1)
    ax.set_ylabel("QWK with the final teacher marks")


def main() -> None:
    global HUMAN
    OUT.mkdir(parents=True, exist_ok=True)
    st = load(RES / "final_stats.json")
    HUMAN = st["human"]["mean"]
    runs = {r["config"]: r for r in st["runs"]}
    tables: list[str] = ["# Result tables (final teacher marks, 50 answers, 3 teachers)", "",
                         f"QWK with a 95% bootstrap interval; * = significantly different from the final system ({st['best']}).", ""]

    def table(title, cfgs, extra=()):
        tables.extend([f"## {title}", "", "| Configuration | QWK | 95% CI | Exact | Within 1 mark (2+ marks) | vs final system (p) |"
                       + "".join(f" {h} |" for h, _ in extra), "|---|---|---|---|---|---|" + "---|" * len(extra)])
        for c in cfgs:
            r = runs[c]
            vs = r.get("vs_best")
            tables.append(f"| {name(c)} | {r['qwk']} | {r['ci'][0]}–{r['ci'][1]} | {r['exact']:.0%} | {r['within_1']:.0%} | "
                          + ("final system" if not vs else f"{vs['diff']:+.3f} (p={vs['p']}){' *' if vs['significant'] else ''}") + " |"
                          + "".join(f" {fn(c)} |" for _, fn in extra))
        tables.append("")

    # true API price per configuration: its first (paid) run; later runs of the same prompts came from the cache
    price: dict[str, float] = {}
    for p in list(EXP.glob("*.json")) + list(EXP.glob("provisional_*/*.json")):
        if p.name.endswith(".grounding.json"):
            continue
        r = load(p)
        price[r["config"]] = max(price.get(r["config"], 0.0), r["summary"].get("cost_per_100") or 0.0)
    run_file = {}
    for p in sorted(EXP.glob("*__teacherall*.json")):
        if not p.name.endswith(".grounding.json"):
            run_file.setdefault(load(p)["config"], load(p))
    cost = lambda c: f"${price.get(c, 0):.3f}"  # noqa: E731
    calls = lambda c: f"{run_file[c]['summary']['calls_per_answer']:.1f}"  # noqa: E731
    secs = lambda c: f"{run_file[c]['summary']['latency_ms']['mean'] / 1000:.1f} s"  # noqa: E731

    print("figures ->", OUT)
    # 1. LLM models
    s1 = ["proposed:haiku:R1:A2:off", "proposed:luna:R1:A2:off", "proposed:llama:R1:A2:off"]
    fig, ax = plt.subplots(figsize=(6.4, 4))
    bars_ci(ax, [MODEL[c.split(":")[1]] for c in s1], [runs[c] for c in s1])
    ax.set_title("Step 1 · LLM models (R1 · A2 · memory off)")
    save(fig, "fig_4_01_llm_models.png")
    table("Step 1 · LLM models (R1, A2, memory off)", s1, [("API cost / 100 answers", cost), ("Time / answer", secs)])

    # 2. baselines vs proposed
    best = st["best"]
    s0 = ["b2", "b1:luna", "b3:luna:R1", "b4:luna:R1", best]
    fig, ax = plt.subplots(figsize=(7.2, 4))
    bars_ci(ax, ["B2\nrules + bge-m3", "B1\nzero-shot", "B3\nRAG + rubric", "B4\nRAG + verifier", "Proposed\nLuna · R3 · A2"],
            [runs[c] for c in s0], highlight=len(s0) - 1)
    ax.set_title("Step 0 · Baselines vs the proposed system")
    save(fig, "fig_4_02_baselines.png")
    table("Step 0 · Baselines (GPT-6 Luna) vs the proposed system", s0, [("API cost / 100 answers", cost)])

    # 3. RAG types in marking
    s2 = ["proposed:luna:R1:A2:off", "proposed:luna:R2:A2:off", "proposed:luna:R3:A2:off"]
    fig, ax = plt.subplots(figsize=(6.4, 4))
    bars_ci(ax, ["R1\nnaive dense", "R2\nhybrid + reranker", "R3\nparent-document"], [runs[c] for c in s2], highlight=2)
    ax.set_title("Step 2 · RAG types in marking (GPT-6 Luna · A2)")
    save(fig, "fig_4_03_rag_marking.png")
    table("Step 2 · RAG types (GPT-6 Luna, A2)", s2, [("API cost / 100 answers", cost)])

    # 4. RAGAS metrics per RAG type
    rag = load(RES / "rag_eval.json")
    metrics = [("context_precision", "Context\nprecision"), ("context_recall", "Context\nrecall"), ("faithfulness", "Faithfulness"),
               ("answer_relevancy", "Answer\nrelevancy"), ("factual_correctness", "Factual\ncorrectness")]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    w = 0.26
    for k, r in enumerate(rag["rags"]):
        xs = [i + (k - 1) * w for i in range(len(metrics))]
        vals = [r["summary"][m] for m, _ in metrics]
        ax.bar(xs, vals, width=w - 0.02, color=C[k], edgecolor="white", linewidth=1, label={"R1": "R1 naive dense", "R2": "R2 hybrid + reranker", "R3": "R3 parent-document"}[r["rag"]])
        for x, v in zip(xs, vals):
            ax.text(x, v + 0.01, f"{v:.2f}", ha="center", va="bottom", fontsize=7, color=INK2)
    ax.set_xticks(range(len(metrics)), [m for _, m in metrics])
    ax.set_ylim(0, 1.08)
    ax.set_ylabel("Score (0–1)")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=3)
    ax.set_title(f"RAG evaluation · RAGAS metrics ({rag['n']} questions, judge {rag['judge']})")
    save(fig, "fig_4_04_rag_ragas.png")
    tables.extend(["## RAG evaluation (RAGAS, 45 questions + 24 out-of-syllabus)", "",
                   "| Metric | R1 | R2 | R3 |", "|---|---|---|---|"]
                  + [f"| {lbl.replace(chr(10), ' ')} | " + " | ".join(f"{r['summary'][m]:.3f}" for r in rag["rags"]) + " |" for m, lbl in metrics]
                  + ["| Declined answers (of 45) | " + " | ".join(str(r["summary"]["declined"]) for r in rag["rags"]) + " |",
                     "| Out-of-syllabus declined (of 24) | " + " | ".join(str(r["summary"]["out_of_syllabus_declined"]) for r in rag["rags"]) + " |",
                     "| Retrieval time | " + " | ".join(f"{r['summary']['retrieval_ms_mean']} ms" for r in rag["rags"]) + " |", ""])

    # 5. RAG settings: number of sections
    rs = load(RES / "rag_settings.json")
    sec = next(s for s in rs["settings"] if s["key"] == "sections")
    labels_k = [o["option"] for o in sec["options"]]
    ks = list(range(len(labels_k)))
    fig, ax = plt.subplots(figsize=(6.4, 4))
    for j, (key, lbl, src) in enumerate([("factual_correctness", "Factual correctness", "answers"), ("evidence_recall", "Evidence recall", "metrics")]):
        ys = [o[src][key] for o in sec["options"]]
        ax.plot(ks, ys, marker="o", markersize=7, linewidth=2, color=C[j], label=lbl)
        ax.annotate(lbl, (ks[-1], ys[-1]), xytext=(6, 0), textcoords="offset points", va="center", color=INK2, fontsize=8)
    ax.set_xticks(ks, labels_k)
    cur = next(i for i, o in enumerate(sec["options"]) if o["current"])
    ax.axvline(cur, color=MUTED, linestyle=":", linewidth=1.2)
    ax.text(cur, 0.52, " current (3)", color=INK2, fontsize=8)
    ax.set_ylim(0.5, 1)
    ax.set_xlabel("Number of textbook sections given to the answer model (k)")
    ax.set_ylabel("Score (0–1)")
    ax.set_title("RAG settings · number of sections (R3)")
    save(fig, "fig_4_05_rag_sections.png")

    # 6. minimum similarity
    steps = rs["similarity"]["steps"]
    th = [s["threshold"] for s in steps]
    fig, ax = plt.subplots(figsize=(7, 4))
    series = [("answerable_rejected", rs["n"], "Real textbook questions rejected (wrong)", C[1]),
              ("general_rejected", rs["oos"]["general"], "General off-syllabus rejected (right)", C[0]),
              ("near_rejected", rs["oos"]["near"], "Near-syllabus rejected (right)", C[2])]
    for key, n, lbl, col in series:
        ax.plot(th, [100 * s[key] / n for s in steps], marker="o", markersize=5, linewidth=2, color=col, label=lbl)
    for x, txt in ((0.35, "chosen 0.35"), (0.55, "chat now 0.55")):
        ax.axvline(x, color=MUTED, linestyle=":", linewidth=1.2)
        ax.text(x, 104, txt, color=INK2, fontsize=8, ha="center", va="bottom")
    ax.set_xlabel("Minimum bge-m3 cosine similarity")
    ax.set_ylabel("Questions rejected (%)")
    ax.set_ylim(0, 112)
    ax.set_yticks(range(0, 101, 20))
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=1)
    ax.set_title("RAG settings · minimum similarity threshold")
    save(fig, "fig_4_06_min_similarity.png")
    tables.extend(["## RAG settings study of R3", "", "| Setting | Options tested | Evidence | Selection |", "|---|---|---|---|"]
                  + [f"| {s['setting']} | {s['tested']} | {s['evidence']} | {s['selection']} |" for s in rs["settings"]] + [""])

    # 7. ReAct types
    s3 = ["proposed:luna:R3:A1:off", "proposed:luna:R3:A2:off", "proposed:luna:R3:A3:off"]
    fig, ax = plt.subplots(figsize=(6.4, 4))
    bars_ci(ax, [f"A1 vanilla\n{calls(s3[0])} calls/answer", f"A2 constrained\n{calls(s3[1])} call/answer",
                 f"A3 reflexion\n{calls(s3[2])} calls/answer"], [runs[c] for c in s3], highlight=1)
    ax.set_title("Step 3 · ReAct types (GPT-6 Luna · R3)")
    save(fig, "fig_4_07_react.png")
    table("Step 3 · ReAct types (GPT-6 Luna, R3)", s3, [("AI calls / answer", calls), ("API cost / 100 answers", cost), ("Time / answer", secs)])

    # 8. memory (two panels: accuracy and consistency; no second y-axis)
    s4 = ["proposed:luna:R3:A2:off", "proposed:luna:R3:A2:on"]
    rep = {c: load(next(EXP.glob(f"step4__{c.replace(':', '_')}__teacherallx3.json")))["summary"] for c in s4}
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(8, 3.8))
    bars_ci(a1, ["memory off", "memory on"], [runs[c] for c in s4], human=False)
    a1.set_title("Accuracy")
    same = [100 * rep[c]["same_score_all_repeats"] for c in s4]
    a2.bar(["memory off", "memory on"], same, color=C[2], width=0.6, edgecolor="white", linewidth=1.5)
    for i, v in enumerate(same):
        a2.text(i, v + 1, f"{v:.0f}%", ha="center", va="bottom", color=INK2, fontsize=9)
    a2.set_ylim(0, 105)
    a2.set_ylabel("Same score in all 3 runs (%)")
    a2.set_title("Consistency (3 repeats)")
    fig.suptitle("Step 4 · Pupil memory (GPT-6 Luna · R3 · A2)", fontweight="bold", color=INK, fontsize=11)
    fig.tight_layout()
    save(fig, "fig_4_08_memory.png")
    table("Step 4 · Memory (GPT-6 Luna, R3, A2; 3 repeats)", s4,
          [("Same score in 3 runs", lambda c: f"{rep[c]['same_score_all_repeats']:.0%}"), ("CoV", lambda c: f"{rep[c]['cov_pct']}%")])

    # 9. QWK vs cost
    fig, ax = plt.subplots(figsize=(7.4, 4.6))
    groups = [("Proposed · GPT-6 Luna", lambda c: c.startswith("proposed:luna"), C[0]),
              ("Proposed · Claude Haiku 5.5", lambda c: c.startswith("proposed:haiku"), C[1]),
              ("Proposed · Llama 3.1 8B", lambda c: c.startswith("proposed:llama"), C[3]),
              ("Baselines B1–B4", lambda c: c.split(":")[0] in ("b1", "b2", "b3", "b4"), C[2]),
              ("Hybrid: open model + GPT-6 Luna (Phase 4)", lambda c: c.startswith("hybrid:"), C[4])]
    for lbl, test, col in groups:
        pts = [(price.get(c, 0), runs[c]["qwk"], c) for c in runs if test(c)]
        ax.scatter([p[0] for p in pts], [p[1] for p in pts], s=60, color=col, edgecolor="white", linewidth=1.5, label=lbl, zorder=3)
    for c in (best, "b2", "proposed:llama:R1:A2:off", "proposed:luna:R3:A1:off", "proposed:haiku:R3:A2:off"):
        ax.annotate(name(c), (price.get(c, 0), runs[c]["qwk"]), xytext=(6, 4), textcoords="offset points", fontsize=7.5, color=INK2)
    ax.axhline(TARGET, color=INK, linestyle="--", linewidth=1)
    ax.set_xlabel("API cost per 100 answers (USD)")
    ax.set_ylabel("QWK with the final teacher marks")
    ax.set_ylim(0.4, 0.85)
    ax.grid(axis="x", color=GRID)
    ax.legend(loc="lower right", fontsize=8)
    ax.set_title("Accuracy vs cost of every configuration")
    save(fig, "fig_4_09_qwk_vs_cost.png")

    # 10. each teacher
    top = [best, "proposed:haiku:R3:A2:off", "b1:luna", "b2"]
    teachers = list(st["teachers"])
    fig, ax = plt.subplots(figsize=(8, 4.2))
    w = 0.2
    for k, c in enumerate(top):
        xs = [i + (k - 1.5) * w for i in range(len(teachers))]
        ax.bar(xs, [runs[c]["per_teacher"][t] for t in teachers], width=w - 0.02, color=C[k], edgecolor="white", label=name(c))
    ax.axhline(HUMAN, color=MUTED, linestyle=":", linewidth=1.4, label=f"Teachers vs each other (mean {HUMAN:.3f})")
    ax.set_xticks(range(len(teachers)), [f"{t.replace('_', ' ').title()}" for t in teachers])
    ax.set_ylim(0, 1)
    ax.set_ylabel("QWK with this teacher")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=3, fontsize=8)
    ax.set_title("E1 · Agreement with each teacher")
    save(fig, "fig_4_10_per_teacher.png")
    tables.extend([f"## E1 · Agreement with each teacher (human baseline {HUMAN}, 95% CI {st['human']['ci'][0]}–{st['human']['ci'][1]})", "",
                   "| Configuration | " + " | ".join(t.replace("_", " ") for t in teachers) + " | Mean | Criterion kappa |",
                   "|---|" + "---|" * (len(teachers) + 2)]
                  + [f"| {name(c)} | " + " | ".join(str(runs[c]["per_teacher"][t]) for t in teachers)
                     + f" | {runs[c]['mean_teachers']} | {runs[c]['criterion_kappa']} |" for c in runs] + [""])

    # 11. confusion matrix
    cm = runs[best]["confusion"]
    order = ["tidak", "separa", "ya"]
    import numpy as np

    m = np.array([[cm[g][p] for p in order] for g in order])
    fig, ax = plt.subplots(figsize=(4.8, 4.2))
    ax.imshow(m, cmap="Blues", vmin=0)
    ax.grid(False)
    for i in range(3):
        for j in range(3):
            ax.text(j, i, m[i, j], ha="center", va="center", fontsize=12, fontweight="bold",
                    color="white" if m[i, j] > m.max() * 0.55 else INK)
    ax.set_xticks(range(3), order)
    ax.set_yticks(range(3), order)
    ax.set_xlabel("System verdict")
    ax.set_ylabel("Final teacher verdict")
    ax.set_title(f"E1 · Criterion verdicts ({name(best)})")
    save(fig, "fig_4_11_confusion.png")

    # 12. by subject and level
    summ = run_file[best]["summary"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(8, 3.8), sharey=True)
    for ax, group, labels in ((a1, summ["by_subject"], {"fiqh": "Ibadah", "jawi": "Jawi", "tajwid": "Tajwid"}),
                              (a2, summ["by_level"], None)):
        keys = list(group)
        vals = [group[k]["qwk_band"] for k in keys]
        ax.bar([labels[k] if labels else k for k in keys], vals, color=C[0], width=0.6, edgecolor="white", linewidth=1.5)
        for i, (k, v) in enumerate(zip(keys, vals)):
            ax.text(i, v + 0.02, f"{v:.2f}\n(n={group[k]['items']})", ha="center", va="bottom", fontsize=8, color=INK2)
        ax.axhline(TARGET, color=INK, linestyle="--", linewidth=1)
        ax.set_ylim(0, 1.1)
    a1.set_ylabel("QWK with the final teacher marks")
    a1.set_title("By subject")
    a2.set_title("By level")
    fig.suptitle(f"E1 · {name(best)}", fontweight="bold", color=INK, fontsize=11)
    fig.tight_layout()
    save(fig, "fig_4_12_subject_level.png")

    (OUT / "tables.md").write_text("\n".join(tables) + "\n", encoding="utf-8")
    print("   tables.md")


if __name__ == "__main__":
    main()
