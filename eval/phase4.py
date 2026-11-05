"""Phase 4 of Experiment plan v3: fine-tuning the best open model, and a hybrid open + commercial marker.

Phase 3 chose Qwen3-4B (the laptop's model): the best open model on the 50 teacher answers.

  data    fine-tuning data for notebooks/finetune_marker.ipynb. Each silver answer (train split; validation: a sample
          of the test split) becomes the exact request of the proposed system (R3, A2, memory off) plus the reply to
          learn. No teacher answer is used, and no teacher question is in the train split. The verdicts are the silver
          labels; the reasons and the pupil feedback are GPT-6 Luna's, kept only when Luna's verdicts equal the silver
          labels on every criterion, so no target contradicts itself. API cost about $0.20 (cached calls are free).
          -> data/finetune/kafa_marker_sft.jsonl (uploaded in the notebook), eval/results/finetune_data.json/.md
  eval    with the notebook's server running: every LoRA adapter on the 50 teacher answers (lowest validation loss
          first) and on the Jawi reading test; the training log is saved too
  report  the hybrid routers (built from saved runs: no model is called), fine-tuned vs base Qwen, tables and figure
          -> eval/results/phase4.json/.md, docs/figures/results/fig_4_17_phase4.png

Usage: .venv\\Scripts\\python eval\\phase4.py data | eval [r8e1 r16e2 ...] | report
"""
from __future__ import annotations

import json
import random
import re
import subprocess
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "eval"))

from silver import load_silver  # noqa: E402

from backend.app.assess.llm_marking import (MARK_SCHEMA, MARKER_RULES, MarkConfig, _hard_rules,  # noqa: E402
                                            _retrieve, _user_prompt)
from backend.app.llm_api import LLMError, _schema_instruction, complete, spent_usd  # noqa: E402
from backend.app.questions import load_questions  # noqa: E402

DATA = ROOT / "data" / "finetune" / "kafa_marker_sft.jsonl"
RES = ROOT / "eval" / "results"
LUNA = MarkConfig("proposed", "luna", "R3", "A2", False)      # writes the reasons and the feedback to learn
SYSTEM = MARKER_RULES + _schema_instruction(MARK_SCHEMA)      # the system message the model receives (llm_api adds the schema)
SUBJ = {"fiqh": "Ibadah", "jawi": "Jawi", "tajwid": "Tajwid"}


# ------------------------------------------------------------------ data
def selection() -> list[tuple[str, dict]]:
    """Train: every paraphrase answer + 40 of each programmatic kind (so trivial answers do not dominate).
    Validation: 20 paraphrase answers per subject + 5 of each programmatic kind, from the test split's questions."""
    rng = random.Random(7)
    test = load_silver("test", programmatic_sample=40)
    para = [i for i in test if i["family"] == "paraphrase"]
    val = [x for s in SUBJ for x in rng.sample([i for i in para if i["question_id"].startswith(s + "_")], 20)]
    val += [i for i in test if i["family"] == "programmatic"]
    return [("train", i) for i in load_silver("train", programmatic_sample=320)] + [("val", i) for i in val]


def _by_no(data: dict | None) -> dict[int, dict]:
    out = {}
    for c in (data or {}).get("criteria") or []:
        try:
            out[int(c["no"])] = c
        except (KeyError, TypeError, ValueError):
            continue
    return out


def target(q: dict, data: dict | None, fixed: dict, gold: list[str]) -> dict | None:
    """Luna's reply as the reply to learn, or None when one of its verdicts differs from the silver label
    (or a criterion the exact rules decide differs from the label)."""
    if not data or not str(data.get("feedback", "")).strip() or len(gold) != len(q["rubric"]):
        return None
    got, crits = _by_no(data), []
    for n, g in enumerate(gold, 1):
        c = got.get(n, {})
        if c.get("verdict") != g or (n in fixed and fixed[n][0] != g):
            return None
        crits.append({"no": n, "verdict": g, "reason": str(c.get("reason", "")).strip()})
    return {"criteria": crits, "feedback": str(data["feedback"]).strip()}


def example(split: str, item: dict, q: dict) -> dict:
    """The proposed system's exact request for this answer (as llm_marking._single builds it) and Luna's reply."""
    fixed = _hard_rules(q, item["answer"])
    user = _user_prompt(q, item["answer"], context=_retrieve(LUNA, q, item["answer"]).context, memory=None, fixed=fixed)
    gold = [c["met"] for c in item["criteria"]]
    rec = {"id": item["answer_id"], "split": split, "subject": q["subject"], "family": item["family"],
           "kind": item["kind"], "gold": gold}
    try:
        c = complete("luna", [{"role": "system", "content": MARKER_RULES}, {"role": "user", "content": user}],
                     schema=MARK_SCHEMA, max_tokens=2000, tag="phase4:data")
    except LLMError as e:
        return rec | {"luna": [], "error": str(e)[:200], "messages": None}
    t = target(q, c.data, fixed, gold)
    return rec | {"luna": [_by_no(c.data).get(n, {}).get("verdict") for n in range(1, len(gold) + 1)],
                  "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user},
                               {"role": "assistant", "content": json.dumps(t, ensure_ascii=False)}] if t else None}


def build_data() -> None:
    qs = load_questions()
    jobs = [(s, i) for s, i in selection() if i["question_id"] in qs]
    print(f"{len(jobs)} silver answers -> GPT-6 Luna (R3, A2)  (spent so far ${spent_usd():.4f})", flush=True)
    with ThreadPoolExecutor(max_workers=4) as ex:
        recs = list(ex.map(lambda j: example(j[0], j[1], qs[j[1]["question_id"]]), jobs))
    DATA.parent.mkdir(parents=True, exist_ok=True)
    with DATA.open("w", encoding="utf-8") as fh:
        for r in recs:
            if r["messages"]:
                fh.write(json.dumps({k: r[k] for k in ("id", "split", "subject", "kind", "messages")}, ensure_ascii=False) + "\n")
    stats = data_stats(recs)
    (RES / "finetune_data.json").write_text(json.dumps(stats, indent=1, ensure_ascii=False), encoding="utf-8")
    (RES / "finetune_data.md").write_text(data_markdown(stats), encoding="utf-8")
    print(data_markdown(stats))
    print(f"-> {DATA.relative_to(ROOT)}  (spent so far ${spent_usd():.4f})")


def data_stats(recs: list[dict]) -> dict:
    def group(rs):
        crit = [(g, v) for r in rs for g, v in zip(r["gold"], r["luna"])]
        return {"answers": len(rs), "luna_replied": sum(bool(r["luna"]) for r in rs),
                "criteria_agree": round(sum(g == v for g, v in crit) / len(crit), 3) if crit else None,
                "kept": sum(bool(r["messages"]) for r in rs)}
    out = {"teacher_model": "GPT-6 Luna, proposed system R3 + A2, memory off", "groups": {}, "kept_verdicts": {}}
    for split in ("train", "val"):
        rs = [r for r in recs if r["split"] == split]
        out["groups"][split] = {"all": group(rs),
                                **{f"family:{f}": group([r for r in rs if r["family"] == f]) for f in ("paraphrase", "programmatic")},
                                **{f"subject:{s}": group([r for r in rs if r["subject"] == s]) for s in SUBJ}}
        out["kept_verdicts"][split] = dict(Counter(v for r in rs if r["messages"] for v in r["gold"]))
    out["dropped_kinds"] = dict(Counter(r["kind"] for r in recs if not r["messages"]).most_common())
    return out


def data_markdown(s: dict) -> str:
    md = ["# Fine-tuning data (Phase 4)", "",
          "Silver answers as the proposed system's marking request (R3, A2, memory off). Reply to learn: the silver verdicts "
          "with GPT-6 Luna's reasons and feedback, kept only where Luna gives the silver verdict on every criterion. "
          "No teacher answer is used; validation answers come from other questions than the training answers.", "",
          "| Split | Group | Answers | Luna criteria = silver label | Kept |", "|---|---|---|---|---|"]
    for split, groups in s["groups"].items():
        for g, v in groups.items():
            name = g.split(":", 1)[-1]
            name = SUBJ.get(name, name)
            agree = "–" if v["criteria_agree"] is None else f"{v['criteria_agree']:.0%}"
            md.append(f"| {split} | {name} | {v['answers']} | {agree} | {v['kept']} ({v['kept'] / max(1, v['answers']):.0%}) |")
    md += ["", "Verdicts in the kept replies: " + "; ".join(
        f"{split}: " + ", ".join(f"{k} {n}" for k, n in sorted(c.items())) for split, c in s["kept_verdicts"].items()),
           "", "Dropped answers by kind: " + ", ".join(f"{k} {n}" for k, n in s["dropped_kinds"].items())]
    return "\n".join(md) + "\n"


# ------------------------------------------------------------------ eval
def evaluate(names: list[str]) -> None:
    """Every adapter served by the fine-tuning notebook on the 50 teacher answers and the Jawi test."""
    import httpx
    import experiments as E

    from backend.app import remote_llm

    if (ep := remote_llm.endpoint()) is None:
        sys.exit("Paste the fine-tuning notebook's LINK and KEY first (Penilaian -> Qwen on Colab)")
    url, key = ep
    r = httpx.get(f"{url}/v1/training_log", headers=remote_llm._headers(key), timeout=30)
    r.raise_for_status()
    log = r.json()
    (RES / "finetune_training.json").write_text(json.dumps(log, indent=1), encoding="utf-8")
    for a in names or sorted(log["adapters"], key=lambda a: log["adapters"][a]["eval_loss"]):
        httpx.post(f"{url}/v1/adapter", json={"name": a}, headers=remote_llm._headers(key), timeout=120).raise_for_status()
        remote_llm._served.clear()            # the same link now serves another adapter
        print(f"adapter {a}", flush=True)
        E.run(MarkConfig("proposed", f"qwen_ft_{a}", "R3", "A2", False), step="phase4", data="teacher", n=None, workers=1)
        subprocess.run([sys.executable, str(ROOT / "eval" / "jawi_reading.py"), f"qwen_ft_{a}"], check=True)


# ------------------------------------------------------------------ report
EXP = RES / "experiments"
BASE, REF = "proposed:qwen:R3:A2:off", "proposed:luna:R3:A2:off"
ROUTERS = {
    "level": "Router A: Tahap 1 to the open model, Tahap 2-3 to GPT-6 Luna",
    "separa": "Router B: open model first; GPT-6 Luna when its reply is invalid or has a 'separa' verdict",
    "rules": "Router C: open model first; GPT-6 Luna when its reply is invalid or its score differs from the rule-based scorer (B2)",
}


def paid_run(config: str) -> dict | None:
    """The first (paid) run of a configuration on the teacher answers: its per-answer cost and time are real
    (later runs of the same prompts came from the cache)."""
    rs = [json.loads(p.read_text(encoding="utf-8")) for p in EXP.glob("*__teacherall.json") if not p.name.startswith("admin__")]
    rs = [r for r in rs if r["config"] == config and r.get("labels") == "teacher" and r.get("complete", True)]
    return max(rs, key=lambda r: r["summary"].get("cost_total", 0), default=None)


def escalate(router: str, rec: dict, q: dict, rule_rec: dict) -> bool:
    """Does this answer go to GPT-6 Luna?"""
    if router == "level":
        return q["level"] >= 2
    if not rec["ok"]:
        return True
    if router == "separa":
        return any(c["met"] == "separa" and c["layer"] == "llm" for c in rec["criteria"])
    return abs(float(rec["score"]) - float(rule_rec["score"])) > 1e-9


def hybrid_run(local: dict, luna: dict, rule: dict, router: str, qs: dict) -> dict:
    """The hybrid system's run, built from the two models' runs on the same answers (both are deterministic and
    cached, so this is exactly what the hybrid would return): no model is called."""
    import experiments as E
    from datetime import datetime, timezone

    first = lambda run: {r["answer_id"]: r for r in run["items"] if r["rep"] == 0}  # noqa: E731
    loc, lun, rul = first(local), first(luna), first(rule)
    name = f"hybrid:{local['model']}+luna:R3:A2:{router}"
    records = []
    for aid, rec in loc.items():
        up = escalate(router, rec, qs[rec["question_id"]], rul[aid])
        own = not (up and router == "level")      # Router A decides from the question alone: no open-model call
        out = dict(lun[aid] if up else rec)
        out["usage"] = {k: (rec["usage"].get(k, 0) if own else 0) + (lun[aid]["usage"].get(k, 0) if up else 0)
                        for k in ("calls", "tokens_in", "tokens_out", "cost", "list_cost", "ms", "cached")}
        out["wall_ms"] = (rec["wall_ms"] if own else 0) + (lun[aid]["wall_ms"] if up else 0)
        records.append(out | {"config": name, "route": "luna" if up else local["model"]})
    return {"step": "phase4", "config": name, "system": "hybrid", "model": f"{local['model']}+luna",
            "model_id": f"{local['model_id']} + {luna['model_id']}",
            "model_label": f"{local['model_label']} + GPT-6 Luna ({ROUTERS[router].split(':')[0]})",
            "rag": "R3", "react": "A2", "memory": False, "data": "teacher", "n": len(records), "repeats": 1,
            "labels": "teacher", "date": datetime.now(timezone.utc).isoformat(timespec="seconds"), "complete": True,
            "router": ROUTERS[router], "to_luna": round(sum(r["route"] == "luna" for r in records) / len(records), 3),
            "simulated_from": [local["config"], luna["config"], rule["config"]],
            "summary": E.summarise(records, qs), "items": records}


def chosen_adapter() -> str | None:
    """The adapter picked BEFORE the teacher test: the lowest validation loss (silver answers to other questions)."""
    p = RES / "finetune_training.json"
    if not p.exists():
        return None
    ad = json.loads(p.read_text(encoding="utf-8"))["adapters"]
    return f"qwen_ft_{min(ad, key=lambda a: ad[a]['eval_loss'])}" if ad else None


def paired(a: str, b: str, runs: dict) -> dict:
    """QWK(a) - QWK(b) on the same 50 answers with the same 2,000 resamples as final_stats.py."""
    import numpy as np

    import final_stats as FS
    from teacher_compare import _meta, _scored, label_sets

    qs, meta, sets = load_questions(), _meta(), label_sets()
    order = sorted(sets["final"])
    idx = FS._boot_idx(len(order))

    def bands(cfg):
        preds = {x["answer_id"]: [c["met"] for c in x["criteria"]] for x in runs[cfg]["items"] if x["rep"] == 0}
        items = {i["answer_id"]: i for i in _scored(preds, sets["final"], qs, meta)}
        return FS._bands([items[x] for x in order])
    ga, pa = bands(a)
    gb, pb = bands(b)
    d = np.array([FS._qwk_of(i, ga, pa) - FS._qwk_of(i, gb, pb) for i in idx])
    return {"diff": round(FS.qwk(ga, pa) - FS.qwk(gb, pb), 3), "ci": FS._ci(d),
            "significant": bool(np.percentile(d, 97.5) < 0 or np.percentile(d, 2.5) > 0)}


def report() -> None:
    import contextlib
    import io

    import final_stats as FS

    qs = load_questions()
    luna, rule = paid_run(REF), paid_run("b2")
    chosen = chosen_adapter()
    for m in ["qwen"] + ([chosen] if chosen else []):
        if (local := paid_run(f"proposed:{m}:R3:A2:off")) is None:
            continue
        for router in ROUTERS:
            h = hybrid_run(local, luna, rule, router, qs)
            (EXP / f"phase4__{h['config'].replace(':', '_')}__teacherall.json").write_text(
                json.dumps(h, indent=1, ensure_ascii=False), encoding="utf-8")
    with contextlib.redirect_stdout(io.StringIO()):
        FS.main()                                   # every table now includes the fine-tuned and hybrid runs
    stats = {r["config"]: r for r in json.loads((RES / "final_stats.json").read_text(encoding="utf-8"))["runs"]}
    runs = {r["config"]: r for r in FS.runs()}
    jawi_p = RES / "jawi_reading.json"
    jawi = json.loads(jawi_p.read_text(encoding="utf-8"))["models"] if jawi_p.exists() else {}
    train_p, data_p = RES / "finetune_training.json", RES / "finetune_data.json"

    def row(cfg: str, vs: str | None) -> dict:
        s, r = stats[cfg], runs[cfg]
        conf = s["confusion"]
        total = sum(sum(v.values()) for v in conf.values())
        m = cfg.split(":")[1]
        return {"config": cfg, "label": r.get("model_label") or cfg, "qwk": s["qwk"], "ci": s["ci"],
                "vs": paired(cfg, vs, runs) if vs and cfg != vs else None,
                "exact": s["by_subject"]["all"]["exact"][0], "within_1": s["by_subject"]["all"]["within_1"][0],
                "by_subject": {g: s["by_subject"][g]["qwk"][0] for g in SUBJ},
                "separa_given": round(sum(v["separa"] for v in conf.values()) / total, 3),
                "separa_teachers": round(sum(conf["separa"].values()) / total, 3),
                "valid": r["summary"]["success_rate"], "seconds": round(r["summary"]["latency_ms"]["mean"] / 1000, 1),
                "cost_per_100": r["summary"].get("cost_per_100") or 0.0, "to_luna": r.get("to_luna"),
                "jawi": jawi[m]["exact_all"] if m in jawi else None}

    ft = [c for c in (f"proposed:qwen_ft_r{r}e{e}:R3:A2:off" for r in (8, 16) for e in (1, 2)) if c in stats]
    hyb = sorted((c for c in stats if c.startswith("hybrid:")),
                 key=lambda c: (c.split(":")[1] != "qwen+luna", list(ROUTERS).index(c.rsplit(":", 1)[1])))
    out = {"chosen_adapter": chosen, "data": json.loads(data_p.read_text(encoding="utf-8")) if data_p.exists() else None,
           "training": json.loads(train_p.read_text(encoding="utf-8")) if train_p.exists() else None,
           "finetune": [row(c, BASE) for c in [BASE] + ft] + [row(REF, BASE)],
           "hybrid": [row(c, REF) for c in [REF, BASE] + ([f"proposed:{chosen}:R3:A2:off"] if chosen and f"proposed:{chosen}:R3:A2:off" in stats else []) + hyb],
           "routers": ROUTERS}
    (RES / "phase4.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    (RES / "phase4.md").write_text(markdown(out), encoding="utf-8")
    figure(out)
    print(markdown(out))


def _ci(x: dict) -> str:
    return f"{x['qwk']:.3f} [{x['ci'][0]:.2f}, {x['ci'][1]:.2f}]"


def _vs(x: dict) -> str:
    v = x["vs"]
    if not v:
        return "–"
    t = f"{v['diff']:+.3f} [{v['ci'][0]:+.2f}, {v['ci'][1]:+.2f}]"
    return f"**{t}**" if v["significant"] else t


def markdown(o: dict) -> str:
    md = ["# Phase 4: fine-tuning and a hybrid model", "",
          "All on the 50 teacher answers with the proposed system (R3, A2, memory off). QWK [95% bootstrap CI]; a change is "
          "a paired difference on the same answers (**bold** = significant, its interval leaves out 0).", ""]
    if o["data"]:
        g = o["data"]["groups"]
        md += [f"Training data: {g['train']['all']['kept']} answers for training and {g['val']['all']['kept']} for validation "
               "(silver answers; reply to learn = silver verdicts with GPT-6 Luna's reasons and feedback; see finetune_data.md).", ""]
    if o["training"]:
        t, ad = o["training"], o["training"]["adapters"]
        md += ["## Training: validation loss (lower is better)", "",
               f"QLoRA on {t['base']}, learning rate {t['learning_rate']} ({t['schedule']}), {t['answers_per_update']} answers per "
               f"update, {t['lora']}. The adapter used for the hybrid is chosen by this loss, before the teacher test: "
               f"**{(o['chosen_adapter'] or '').replace('qwen_ft_', '')}**.", "",
               "| LoRA rank | After 1 epoch | After 2 epochs | Training time |", "|---|---|---|---|"]
        for r in sorted({v["rank"] for v in ad.values()}):
            md.append(f"| {r} | " + " | ".join(f"{ad[f'r{r}e{e}']['eval_loss']:.4f}" if f"r{r}e{e}" in ad else "–" for e in (1, 2))
                      + f" | {t['runs'].get(f'r{r}', {}).get('minutes', '–')} min |")
        md.append("")
    md += ["## Marking: fine-tuned vs base Qwen3-4B", "",
           "| Model | QWK [95% CI] | Change from base | Exact | Within 1 | " + " | ".join(f"QWK {v}" for v in SUBJ.values())
           + " | 'separa' given (teachers) | Valid marks | s / answer | Jawi test |", "|---|---|---|---|---|" + "---|" * len(SUBJ) + "---|---|---|---|"]
    md += [f"| {x['label']} | {_ci(x)} | {_vs(x)} | {x['exact']:.0%} | {x['within_1']:.0%} | "
           + " | ".join(f"{x['by_subject'][g]:.3f}" for g in SUBJ)
           + f" | {x['separa_given']:.0%} ({x['separa_teachers']:.0%}) | {x['valid']:.0%} | {x['seconds']:.1f} | "
           + ("–" if x["jawi"] is None else f"{x['jawi']:.0%}") + " |" for x in o["finetune"]]
    md += ["", "## Hybrid: open model + GPT-6 Luna", "", *(f"- {v}" for v in o["routers"].values()), "",
           "| System | QWK [95% CI] | Change from GPT-6 Luna alone | Answers sent to Luna | $ / 100 answers | s / answer |",
           "|---|---|---|---|---|---|"]
    md += [f"| {x['label']} | {_ci(x)} | {_vs(x)} | "
           + ("100%" if x["config"] == REF else "0%" if x["to_luna"] is None else f"{x['to_luna']:.0%}")
           + f" | ${x['cost_per_100']:.3f} | {x['seconds']:.1f} |" for x in o["hybrid"]]
    md += ["", "Open-model times are on a Colab L4 GPU; a hybrid's time is the open model's plus Luna's for the answers it sends on."]
    return "\n".join(md) + "\n"


def figure(o: dict) -> None:
    import make_figures as MF

    plt = MF.plt
    MF.OUT.mkdir(parents=True, exist_ok=True)
    MF.HUMAN = json.loads((RES / "final_stats.json").read_text(encoding="utf-8"))["human"]["mean"]
    fig, (a, b) = plt.subplots(1, 2, figsize=(11, 3.9), gridspec_kw={"width_ratios": [1.15, 1]})
    # "Qwen3-4B fine-tuned (LoRA r8, 2 epochs)" -> "FT r8e2" (scatter) or "FT r8 / 2 epochs" (bars), so labels do not overlap
    ft = re.compile(r"Qwen3-4B fine-tuned \(LoRA r(\d+), (\d) epochs?\)")
    short = lambda x: ft.sub(r"FT r\1e\2", x["label"]).replace(" (open-weight)", "").replace("GPT-6 ", "")  # noqa: E731
    bar = lambda x: ft.sub(lambda m: f"FT r{m[1]}\n{m[2]} epoch{'s' if m[2] != '1' else ''}", x["label"]).replace(  # noqa: E731
        " (open-weight)", "\nbase").replace("GPT-6 ", "GPT-6\n")
    MF.bars_ci(a, [bar(x) for x in o["finetune"]], o["finetune"], highlight=None)
    a.set_title("Fine-tuning: QWK with the final teacher marks (95% CI)")
    a.tick_params(axis="x", labelsize=8)
    for i, x in enumerate(o["hybrid"]):
        b.scatter(x["cost_per_100"], x["qwk"], s=55, color=MF.C[min(i, len(MF.C) - 1)], edgecolor="white", zorder=3)
        b.annotate(short(x).replace(" + Luna", "+Luna"), (x["cost_per_100"], x["qwk"]), xytext=(5, 3),
                   textcoords="offset points", fontsize=7)
    b.set_xlabel("API cost per 100 answers (USD)")
    b.set_ylabel("QWK")
    b.set_title("Hybrid: accuracy vs API cost")
    MF.save(fig, "fig_4_17_phase4.png")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "data":
        build_data()
    elif cmd == "eval":
        evaluate(sys.argv[2:])
    elif cmd == "report":
        report()
    else:
        sys.exit(__doc__)
