"""Experiment runner for the blueprint's staged comparison (§6.2 "How the matrix will be used").

  step1  models:   proposed:{haiku, luna, llama, qwen}:R1:A2:off
  step0  baselines on the best model: b2 (current scorer), b1, b3, b4
  step2  RAG:      proposed:<best model>:{R1, R2, R3}:A2:off
  step3  ReAct:    proposed:<best model>:<best RAG>:{A1, A2, A3}:off
  step4  final:    proposed:<best>:<best>:<best>:{off, on}, repeated 3 times (consistency, memory ablation)

"Best" = highest QWK with the reference marks, then exact agreement, then lower cost.

Data
  --data silver   development set (AI-written, AI-marked; stratified sample of the TEST split).
                  For building and checking only; never the thesis result.
  --data teacher  the 50 teacher-marked answers (data/teacher/teacher_test.json) = E1, the final result.

Usage
  .venv\\Scripts\\python eval\\experiments.py plan --data silver --n 40
  .venv\\Scripts\\python eval\\experiments.py run proposed:luna:R2:A2:off --data silver --n 40 [--repeats 3]
  .venv\\Scripts\\python eval\\experiments.py list
Results: eval/results/experiments/<step>__<config>__<data>.json (finished runs are reused, so a
stopped plan resumes where it left off). API money is capped by KAFA_LLM_BUDGET_USD.
"""
from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "eval"))

from scoring_lib import grouped, metrics  # noqa: E402
from silver import load_silver  # noqa: E402

from backend.app.assess import llm_marking  # noqa: E402
from backend.app.assess.decision import award  # noqa: E402
from backend.app.assess.llm_marking import MarkConfig, MarkResult, mark  # noqa: E402
from backend.app.llm_api import MODELS, BudgetExceeded, open_model_problem, spent_usd  # noqa: E402
from backend.app.questions import load_questions  # noqa: E402

OUT = ROOT / "eval" / "results" / "experiments"
SEED = 11
STEP1_MODELS = ("haiku", "luna", "llama", "qwen")


# ------------------------------------------------------------------ data
def teacher_split(labels: str) -> str:
    return "teacher" if labels in ("", "final") else f"teacher:{labels}"


def load_items(data: str, n: int | None, labels: str = "final") -> list[dict]:
    """Answers with reference marks per criterion ({question_id, answer, criteria[{met}], kind, ...}).
    For the teacher set, `labels` picks the reference: final (settled), guru_1, guru_2, ... or agreed."""
    if data == "teacher":
        items = load_silver(teacher_split(labels))
        return items[:n] if n else items
    items = load_silver("test")
    rng = random.Random(SEED)
    # stratified by subject x level x family, so a small sample still covers every case
    strata: dict[tuple, list] = defaultdict(list)
    qs = load_questions()
    for it in items:
        q = qs[it["question_id"]]
        strata[(q["subject"], q["level"], it["family"])].append(it)
    for v in strata.values():
        rng.shuffle(v)
    picked, keys = [], sorted(strata)
    while len(picked) < (n or len(items)) and any(strata[k] for k in keys):
        for k in keys:
            if strata[k] and len(picked) < (n or len(items)):
                picked.append(strata[k].pop())
    return picked


def simulated_memory(item: dict, pool: list[dict], qs: dict) -> dict:
    """A pupil history for the memory ablation, built from OTHER answers in the same topic:
    their missed criteria become 'past mistakes' and their scores give the mastery."""
    q = qs[item["question_id"]]
    same = [o for o in pool if o["answer_id"] != item["answer_id"] and qs[o["question_id"]]["topic_id"] == q["topic_id"]]
    mistakes: list[str] = []
    for o in same:
        for rc, c in zip(qs[o["question_id"]]["rubric"], o["criteria"]):
            if c["met"] == "tidak" and rc["criterion"] not in mistakes:
                mistakes.append(rc["criterion"])
    scores = [o["expected_score"] / qs[o["question_id"]]["max_marks"] for o in same if qs[o["question_id"]]["max_marks"]]
    by_topic: dict[str, list[float]] = defaultdict(list)
    for o in pool:
        oq = qs[o["question_id"]]
        if oq["subject"] == q["subject"] and oq["max_marks"]:
            by_topic[oq["topic_id"]].append(o["expected_score"] / oq["max_marks"])
    weak = sorted(by_topic, key=lambda t: statistics.mean(by_topic[t]))[:2]
    return {"mastery": round(statistics.mean(scores), 2) if scores else 0.0, "attempts": len(same),
            "recent_mistakes": mistakes[:3], "weak_topics": [t.split("_", 2)[-1].replace("_", " ") for t in weak]}


# ------------------------------------------------------------------ one run
def _model_id(cfg: MarkConfig, spec) -> str:
    """Model name for the result file; for Qwen also where it ran (Google Colab or this laptop)."""
    if cfg.system == "b2" or spec is None:
        return ""
    if spec.local:
        from backend.app import remote_llm
        from backend.app.config import get_settings

        return f"colab:{remote_llm.served_model()}" if remote_llm.endpoint() else f"local:{get_settings().llm_model_id}"
    return spec.id


def run_path(step: str, cfg: MarkConfig, data: str, n: int | None, repeats: int, labels: str = "final") -> Path:
    tag = f"{data}{'' if data != 'teacher' or labels == 'final' else '-' + labels}{n or 'all'}" + (f"x{repeats}" if repeats > 1 else "")
    return OUT / f"{step}__{cfg.name.replace(':', '_')}__{tag}.json"


def _one(item: dict, q: dict, cfg: MarkConfig, memory: dict | None) -> dict:
    t0 = time.perf_counter()
    try:
        r = mark(q, item["answer"], cfg, memory=memory)
    except BudgetExceeded:
        raise
    except Exception as e:  # noqa: BLE001 - an API or model failure is a result (success rate), not a crash
        crits = [{"no": i, "criterion": c["criterion"], "marks": float(c["marks"]), "met": "tidak", "awarded": 0.0,
                  "layer": "error", "reason": ""} for i, c in enumerate(q["rubric"], 1)]
        r = MarkResult(cfg.name, crits, 0.0, float(sum(c["marks"] for c in q["rubric"])), "", ok=False,
                       error=f"{type(e).__name__}: {e}"[:300],
                       usage={"calls": 0, "tokens_in": 0, "tokens_out": 0, "cost": 0.0, "ms": 0, "cached": 0})
    d = r.to_dict()
    d["wall_ms"] = int((time.perf_counter() - t0) * 1000)
    return d


def run(cfg: MarkConfig, *, step: str = "adhoc", data: str = "silver", n: int | None = 40, repeats: int = 1,
        workers: int = 4, force: bool = False, labels: str = "final", on_progress=None) -> dict:
    """`on_progress(done, total)` is called after every marked answer (the admin page shows it)."""
    path = run_path(step, cfg, data, n, repeats, labels)
    if path.exists() and not force:
        res = json.loads(path.read_text(encoding="utf-8"))
        if res.get("complete"):
            print(f"  reuse {path.name}: QWK {res['summary']['overall'].get('qwk_band')}")
            return res
    spec = MODELS.get(cfg.model)
    if cfg.system != "b2" and spec is not None and spec.local and (problem := open_model_problem(spec)):
        sys.exit(f"{spec.label} cannot run: {problem}.")
    qs = load_questions()
    # questions of a book the admin removed from the syllabus are left out
    items = [it for it in load_items(data, n, labels) if it["question_id"] in qs]
    pool = [it for it in (load_silver(teacher_split(labels)) if data == "teacher" else load_silver("test"))
            if it["question_id"] in qs]
    done, total, tick_lock = [0], len(items) * repeats, threading.Lock()

    def marked(j):
        out = _one(*j)
        with tick_lock:
            done[0] += 1
            if on_progress:
                on_progress(done[0], total)
        return out
    local = cfg.system == "b2" or (spec is not None and spec.local)
    print(f"  run {cfg.name} on {len(items)} {data} answers x{repeats}  (spent so far ${spent_usd():.4f})", flush=True)
    t0 = time.perf_counter()
    records, complete_run = [], True
    try:
        for rep in range(repeats):
            jobs = [(it, qs[it["question_id"]], cfg, simulated_memory(it, pool, qs) if cfg.memory else None) for it in items]
            # repeats must not be answered from the cache, otherwise consistency is trivially perfect
            llm_marking.CALL_OPTIONS.clear()
            if rep:
                llm_marking.CALL_OPTIONS.update(seed=7 + rep, use_cache=False)
            try:
                if local:
                    outs = [marked(j) for j in jobs]
                else:
                    with ThreadPoolExecutor(max_workers=workers) as ex:
                        outs = list(ex.map(marked, jobs))
            finally:
                llm_marking.CALL_OPTIONS.clear()
            for it, o in zip(items, outs):
                records.append({"rep": rep, "answer_id": it["answer_id"], "question_id": it["question_id"],
                                "kind": it.get("kind", ""), "family": it.get("family", ""), "script": it.get("script", ""),
                                "answer": it["answer"], "gold": [c["met"] for c in it["criteria"]], **o})
            print(f"    repeat {rep + 1}/{repeats} done in {time.perf_counter() - t0:.0f}s", flush=True)
    except BudgetExceeded as e:
        print(f"  STOPPED: {e}")
        complete_run = False
    res = {"step": step, "config": cfg.name, "system": cfg.system, "model": cfg.model,
           "model_id": _model_id(cfg, spec), "model_label": spec.label if spec and cfg.system != "b2" else "",
           "rag": cfg.rag if cfg.system not in ("b1", "b2") else "", "react": cfg.react if cfg.system == "proposed" else "",
           "memory": cfg.memory, "data": data, "n": len(items), "repeats": repeats,
           "labels": ("teacher" if labels == "final" else f"teacher:{labels}") if data == "teacher" else "silver",
           "date": datetime.now(timezone.utc).isoformat(timespec="seconds"), "complete": complete_run,
           "summary": summarise(records, qs), "items": records}
    if spec is not None and spec.local and cfg.system != "b2":
        from backend.app import remote_llm
        if remote_llm.endpoint() is not None:     # GPU and precision of the Colab server (the thesis must state them)
            res["colab"] = {k: v for k, v in remote_llm.check().items() if k != "ok"}
    OUT.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    o = res["summary"]["overall"]
    print(f"  -> QWK {o.get('qwk_band')}  exact {o.get('item_exact')}  within1 {o.get('within_1')}  "
          f"ok {res['summary']['success_rate']}  ${res['summary']['cost_total']:.4f}  -> {path.name}", flush=True)
    return res


def summarise(records: list[dict], qs: dict) -> dict:
    if not records:
        return {"overall": {}, "success_rate": 0, "cost_total": 0}
    first = [r for r in records if r["rep"] == 0]
    scored = []
    for r in first:
        q = qs[r["question_id"]]
        crits = [{"label": g, "marks": float(c["marks"]), "a_layer": "rule" if c["layer"] == "rule" else None}
                 for g, c in zip(r["gold"], r["criteria"])]
        scored.append({"answer_id": r["answer_id"], "subject": q["subject"], "level": q["level"], "kind": r["kind"],
                       "family": r["family"], "script": r["script"], "max_marks": float(q["max_marks"]),
                       "criteria": crits, "pred_mets": [c["met"] for c in r["criteria"]],
                       "pred": float(r["score"]), "gold": float(sum(award(c["marks"], c["label"]) for c in crits))})
    lat = sorted(r["wall_ms"] for r in records)
    cost = sum(r["usage"].get("list_cost", r["usage"].get("cost", 0)) for r in records)   # list price, cache or not
    paid = sum(r["usage"].get("cost", 0) for r in records)
    reps = max(r["rep"] for r in records) + 1
    cov = None
    if reps > 1:
        per: dict[str, list[float]] = defaultdict(list)
        for r in records:
            per[r["answer_id"]].append(float(r["score"]))
        vals = [statistics.pstdev(v) / statistics.mean(v) * 100 for v in per.values() if len(v) > 1 and statistics.mean(v) > 0]
        cov = round(statistics.mean(vals), 2) if vals else 0.0
        same = sum(len(set(v)) == 1 for v in per.values()) / len(per)
    worst = sorted(scored, key=lambda s: -abs(s["pred"] - s["gold"]) / s["max_marks"])[:15]
    return {
        "overall": metrics(scored),
        "by_subject": grouped(scored, lambda i: i["subject"]),
        "by_level": grouped(scored, lambda i: f"Tahap {i['level']}"),
        "by_kind": grouped(scored, lambda i: i["kind"]),
        "success_rate": round(sum(r["ok"] for r in records) / len(records), 3),
        "errors": [r["error"] for r in records if r["error"]][:10],
        "latency_ms": {"mean": int(statistics.mean(lat)), "p95": lat[min(len(lat) - 1, int(0.95 * len(lat)))]},
        "cost_total": round(cost, 6), "cost_paid": round(paid, 6),
        "cost_per_100": round(cost / len(records) * 100, 4),
        "calls_per_answer": round(sum(r["usage"].get("calls", 0) for r in records) / len(records), 2),
        "tokens_per_answer": int(sum(r["usage"].get("tokens_in", 0) + r["usage"].get("tokens_out", 0) for r in records) / len(records)),
        "cov_pct": cov, "same_score_all_repeats": round(same, 3) if reps > 1 else None,
        "worst": [{"answer_id": s["answer_id"], "gold": s["gold"], "pred": s["pred"], "max": s["max_marks"], "kind": s["kind"]}
                  for s in worst if s["pred"] != s["gold"]],
    }


# ------------------------------------------------------------------ staged plan
def _rank(res: dict) -> tuple:
    """Higher is better. On the teacher set with several teachers, use the MEAN agreement with every
    teacher (eval/teacher_compare.py) so the choice does not depend on one teacher's marking style."""
    o = res["summary"]["overall"]
    if res.get("data") == "teacher":
        try:
            from teacher_compare import per_teacher_qwk

            mean = per_teacher_qwk(res)
            if mean is not None:
                return (mean, o.get("item_exact", 0), -res["summary"]["cost_total"])
        except FileNotFoundError:
            pass
    return (o.get("qwk_band", -1), o.get("item_exact", 0), -res["summary"]["cost_total"])


def qwen_available() -> bool:
    """Qwen can run: its Google Colab link is saved, or local loading is allowed."""
    from backend.app import remote_llm
    from backend.app.config import get_settings

    return remote_llm.endpoint() is not None or get_settings().local_llm


def plan(data: str, n: int | None, workers: int, models: tuple[str, ...] = STEP1_MODELS, labels: str = "final") -> None:
    if "qwen" in models and not qwen_available():
        print("NOTE: Qwen skipped - start notebooks/qwen_colab_server.ipynb and paste its link on the Penilaian page,"
              " then run the plan again (finished runs are reused).")
        models = tuple(m for m in models if m != "qwen")
    print(f"== Step 1: models ({data}) ==")
    s1 = [run(MarkConfig("proposed", m, "R1", "A2", False), step="step1", data=data, n=n, workers=workers, labels=labels) for m in models]
    best_m = max(s1, key=_rank)["model"]
    print(f"   best model: {best_m}")

    print("== Step 0: baselines on the best model ==")
    for cfg in (MarkConfig("b2"), MarkConfig("b1", best_m), MarkConfig("b3", best_m, "R1"), MarkConfig("b4", best_m, "R1")):
        run(cfg, step="step0", data=data, n=n, workers=workers, labels=labels)

    print("== Step 2: RAG types ==")
    s2 = [run(MarkConfig("proposed", best_m, r, "A2", False), step="step2", data=data, n=n, workers=workers, labels=labels) for r in ("R1", "R2", "R3")]
    best_r = max(s2, key=_rank)["rag"]
    print(f"   best RAG: {best_r}")

    print("== Step 3: ReAct types ==")
    s3 = [run(MarkConfig("proposed", best_m, best_r, a, False), step="step3", data=data, n=n, workers=workers, labels=labels) for a in ("A1", "A2", "A3")]
    best_a = max(s3, key=_rank)["react"]
    print(f"   best ReAct: {best_a}")

    print("== Step 4: final configuration, memory off/on, 3 repeats ==")
    for mem in (False, True):
        run(MarkConfig("proposed", best_m, best_r, best_a, mem), step="step4", data=data, n=n, repeats=3, workers=workers, labels=labels)
    print(f"done. final configuration: proposed:{best_m}:{best_r}:{best_a}  (spent ${spent_usd():.4f})")


def list_runs() -> None:
    for p in sorted(OUT.glob("*.json")):
        if p.name.endswith(".grounding.json"):
            continue
        r = json.loads(p.read_text(encoding="utf-8"))
        o = r["summary"]["overall"]
        print(f"{r['step']:6s} {r['config']:32s} {r['data']:7s} n={r['n']:3d} QWK={o.get('qwk_band')} exact={o.get('item_exact')} "
              f"w1={o.get('within_1')} ok={r['summary']['success_rate']} cov={r['summary'].get('cov_pct')} ${r['summary']['cost_total']:.4f}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["plan", "run", "list"])
    ap.add_argument("config", nargs="?", help="e.g. proposed:luna:R2:A2:off, b3:haiku:R1, b2")
    ap.add_argument("--data", default="silver", choices=["silver", "teacher"])
    ap.add_argument("--n", type=int, default=40, help="answers to use (0 = all)")
    ap.add_argument("--repeats", type=int, default=1)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--step", default="adhoc")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--labels", default="final",
                    help="teacher set only: final (settled marks), guru_1, guru_2, ... or agreed")
    a = ap.parse_args()
    n = a.n or None
    if a.cmd == "plan":
        plan(a.data, n, a.workers, labels=a.labels)
    elif a.cmd == "run":
        run(MarkConfig.parse(a.config), step=a.step, data=a.data, n=n, repeats=a.repeats, workers=a.workers, force=a.force,
            labels=a.labels)
    else:
        list_runs()
