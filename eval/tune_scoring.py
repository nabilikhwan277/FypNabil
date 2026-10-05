"""Phase 5: compare scoring configurations on the TRAIN split and pick the best.

Selection metric: mark-weighted criterion error rate (lower is better),
ties broken by criterion accuracy. Tahap 1 and Tahap 2/3 rules are tuned
independently (they never share criteria). The test split is not touched.

Usage: .venv\\Scripts\\python eval\\tune_scoring.py
Writes eval/results/tuning.csv, eval/results/tuning.md and
backend/app/assess/scoring_config.json (the chosen configuration).
"""
from __future__ import annotations

import csv
import json
import sys
from itertools import product
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "eval"))

from scoring_lib import Config, Rule, auc, credit, grouped, load_features, metrics, score_items  # noqa: E402,F401

RES = ROOT / "eval" / "results"
CONFIG_OUT = ROOT / "backend" / "app" / "assess" / "scoring_config.json"
GRID = [round(x * 0.05, 2) for x in range(2, 20)]          # 0.10 .. 0.95
WEIGHTS = [0.3, 0.5, 0.7]

from scoring_lib import PHASE4 as BASELINE  # noqa: E402


def objective(scored) -> tuple:
    m = metrics(scored)
    return (m["mark_err_rate"], -m["crit_acc"])


def candidate_rules(methods: list[str]) -> list[Rule]:
    rules = []
    for m in methods:
        ws = WEIGHTS if m in ("mix", "sims", "hybrid_zs", "hybrid_fs") else [0.5]
        for w, hi in product(ws, GRID):
            rules.append(Rule(m, hi=hi, lo=1.1, w=w))              # no separa
            rules += [Rule(m, hi=hi, lo=lo, w=w) for lo in GRID if lo < hi]
    return rules


def best_rule(items, rules, fixed_other: Rule, level_filter) -> tuple[Rule, tuple]:
    sub = [it for it in items if level_filter(it["level"])]
    best = None
    for r in rules:
        cfg = Config("tmp", l1=r, l23=r) if level_filter(1) else Config("tmp", l1=fixed_other, l23=r)
        obj = objective(score_items(sub, cfg))
        if best is None or obj < best[1]:
            best = (r, obj)
    return best


def signal_auc(items) -> dict:
    """How well each raw signal separates ya from tidak on unresolved Tahap 2/3 criteria."""
    crit = [f for it in items if it["level"] >= 2 for f in it["criteria"] if f["a_layer"] is None]
    out = {}
    for m in ("sim", "ans_sim", "sims", "overlap", "mix", "prob_zs", "prob_fs"):
        pos = [credit(f, m, 0.5) for f in crit if f["label"] == "ya" and credit(f, m, 0.5) is not None]
        neg = [credit(f, m, 0.5) for f in crit if f["label"] == "tidak" and credit(f, m, 0.5) is not None]
        out[m] = auc(pos, neg)
    gen_ya = [f for f in crit if f.get("llm_gen")]
    out["gen_says_ya_when_gold_ya"] = round(sum(f["llm_gen"] == "ya" for f in gen_ya if f["label"] == "ya")
                                            / max(1, sum(f["label"] == "ya" for f in gen_ya)), 3)
    out["gen_says_ya_when_gold_tidak"] = round(sum(f["llm_gen"] == "ya" for f in gen_ya if f["label"] == "tidak")
                                               / max(1, sum(f["label"] == "tidak" for f in gen_ya)), 3)
    out["n_unresolved_l23"] = len(crit)
    return out


def main() -> None:
    items = load_features("train")
    RES.mkdir(parents=True, exist_ok=True)
    rows = []

    def log(cfg: Config, note: str = ""):
        m = metrics(score_items(items, cfg))
        rows.append({"config": cfg.name, "l1": cfg.l1.label(), "l23": cfg.l23.label(), "note": note, **m})
        return m

    log(BASELINE, "Phase 4 behaviour")
    for g in (0.50, 0.55, 0.60, 0.65, 0.70, 0.75):
        log(Config(f"gen_guard_{g:.2f}", l1=BASELINE.l1, l23=Rule("gen", guard=g)), "guard sweep")

    # Tahap 1: no LLM; tune a similarity/overlap rule
    l1_best, _ = best_rule(items, candidate_rules(["ans_sim", "sim", "sims", "overlap", "mix"]), BASELINE.l23,
                           lambda lv: lv == 1)
    log(Config("l1_tuned+baseline_l23", l1=l1_best, l23=BASELINE.l23), "Tahap 1 tuned")

    # Tahap 2/3: each method family tuned on its own, Tahap 1 fixed to l1_best
    families = {"no_llm_sim": ["sim"], "no_llm_sims": ["sims"], "no_llm_overlap": ["overlap"], "no_llm_mix": ["mix"],
                "llm_prob_zeroshot": ["prob_zs"], "llm_prob_fewshot": ["prob_fs"],
                "hybrid_zeroshot": ["hybrid_zs"], "hybrid_fewshot": ["hybrid_fs"]}
    best_by_family = {}
    for fam, methods in families.items():
        r, _ = best_rule(items, candidate_rules(methods), l1_best, lambda lv: lv >= 2)
        best_by_family[fam] = r
        log(Config(fam, l1=l1_best, l23=r), "Tahap 2/3 tuned")
    gen_best = min((Rule("gen", guard=g) for g in (0.5, 0.55, 0.6, 0.65, 0.7, 0.75)),
                   key=lambda r: objective(score_items([i for i in items if i["level"] >= 2],
                                                       Config("t", l1=l1_best, l23=r))))
    best_by_family["llm_generative"] = gen_best
    log(Config("llm_generative", l1=l1_best, l23=gen_best), "Tahap 2/3 tuned")

    # pick the overall winner (or a forced choice: --choose <family>)
    winner = min((r for r in rows if r["config"] in best_by_family),
                 key=lambda r: (r["mark_err_rate"], -r["crit_acc"]))
    forced = sys.argv[sys.argv.index("--choose") + 1] if "--choose" in sys.argv else None
    name = forced or winner["config"]
    chosen = Config(name, l1=l1_best, l23=best_by_family[name])
    (RES / "tuning_candidates.json").write_text(json.dumps(
        {"best_by_error": winner["config"], "chosen": name,
         "candidates": {fam: Config(fam, l1=l1_best, l23=r).to_dict() for fam, r in best_by_family.items()}},
        indent=1), encoding="utf-8")
    scored = score_items(items, chosen)
    base_scored = score_items(items, BASELINE)
    aucs = signal_auc(items)

    with (RES / "tuning.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    if "--dry-run" not in sys.argv:
        CONFIG_OUT.write_text(json.dumps({**chosen.to_dict(), "tuned_on": "train silver",
                                          "selection": "min mark-weighted criterion error"}, indent=2),
                              encoding="utf-8")

    cols = ["config", "l23", "unresolved_criteria", "crit_acc", "unres_acc", "mark_err_rate", "item_exact", "mae_pct",
            "qwk_band", "over_marked", "under_marked"]
    md = ["# Phase 5 tuning (train split, silver labels)", "",
          f"Items: {len(items)} (paraphrase {sum(i['family'] == 'paraphrase' for i in items)}, "
          f"programmatic {sum(i['family'] == 'programmatic' for i in items)}). "
          "Labels are silver (AI-written, not teacher-marked).", "",
          f"Tahap 1 rule chosen: `{l1_best.label()}`", "",
          "| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in rows:
        md.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
    md += ["", f"**Lowest error:** `{winner['config']}`. **Deployed:** `{chosen.name}` - Tahap 1 "
           f"`{chosen.l1.label()}`, Tahap 2/3 `{chosen.l23.label()}`", "",
           "## Signal quality (AUC, ya vs tidak, unresolved Tahap 2/3 criteria)", "",
           "| signal | value |", "|---|---|"]
    md += [f"| {k} | {v} |" for k, v in aucs.items()]
    md += ["", "## Chosen vs baseline by answer kind", "", "| kind | baseline mae_pct | chosen mae_pct | "
           "baseline exact | chosen exact |", "|---|---|---|---|---|"]
    gb, gc = grouped(base_scored, lambda i: i["kind"]), grouped(scored, lambda i: i["kind"])
    for k in gc:
        md.append(f"| {k} | {gb[k]['mae_pct']} | {gc[k]['mae_pct']} | {gb[k]['item_exact']} | {gc[k]['item_exact']} |")
    (RES / "tuning.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    for r in rows:
        print(f"{r['config']:<24} {r['l23']:<44} err={r['mark_err_rate']:.3f} acc={r['crit_acc']:.3f} "
              f"exact={r['item_exact']:.3f} qwk={r['qwk_band']:.3f}")
    print("AUC:", aucs)
    print("chosen:", chosen.to_dict())


if __name__ == "__main__":
    main()
