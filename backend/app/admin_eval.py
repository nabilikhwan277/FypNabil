"""Run an evaluation of one marking configuration from the admin page (Admin → Evaluation → System setup).

It is the same run as `python eval\\experiments.py run <config> --data ...`, started as a background job,
saved as eval/results/experiments/admin__<config>__<data>.json and shown with the other results.
Answers already marked by the same configuration come from the cache and cost nothing.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from . import jobs, live_config
from .assess.llm_marking import MarkConfig
from .config import ROOT

TEACHER = ROOT / "data" / "teacher"
EXP = ROOT / "eval" / "results" / "experiments"
DEFAULT_PER_ANSWER = 0.0006      # $ per answer when no earlier run of a similar configuration exists


def datasets() -> list[dict]:
    """The answer sets with reference marks that an evaluation can use."""
    out = []
    if (TEACHER / "teacher_test.json").exists():
        out.append({"data": "teacher", "labels": "final", "label": "Teacher set, settled marks (final E1)"})
    for p in sorted((TEACHER / "labels").glob("*.json")):
        name = p.stem
        text = "answers both teachers agreed on" if name == "agreed" else f"marks of {name.replace('_', ' ')}"
        out.append({"data": "teacher", "labels": name, "label": f"Teacher set, {text}"})
    out.append({"data": "silver", "labels": "final", "label": "Silver development set (100 AI-written answers)"})
    for d in out:
        d["answers"] = _count(d["data"], d["labels"])
    return [d for d in out if d["answers"]]


def _count(data: str, labels: str) -> int:
    if data == "silver":
        return 100
    path = TEACHER / "teacher_test.json" if labels == "final" else TEACHER / "labels" / f"{labels}.json"
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return 0
    return len(d.get("items", d) if isinstance(d, dict) else d)


def _experiments():
    if str(ROOT / "eval") not in sys.path:
        sys.path.insert(0, str(ROOT / "eval"))
    import experiments

    return experiments


def _runs() -> list[dict]:
    out = []
    for p in EXP.glob("*.json"):
        if p.name.endswith(".grounding.json"):
            continue
        try:
            r = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        out.append({"config": r["config"], "system": r["system"], "model": r.get("model", ""), "react": r.get("react", ""),
                    "data": r["data"], "labels": r["labels"], "n": r["n"], "repeats": r["repeats"],
                    "cost_total": r["summary"].get("cost_total") or 0.0,
                    "tokens": r["summary"].get("tokens_per_answer") or 0, "file": p.name})
    return out


def estimate(config: str, data: str, labels: str) -> dict:
    cfg = MarkConfig.parse(config)
    answers = 100 if data == "silver" else _count(data, labels)
    if cfg.system == "b2":
        return {"answers": answers, "cost": 0.0, "note": "Runs on this laptop: free"}
    ref = "teacher" if data == "teacher" and labels == "final" else (f"teacher:{labels}" if data == "teacher" else "silver")
    runs = _runs()
    if any(r["config"] == cfg.name and r["data"] == data and r["labels"] == ref and r["repeats"] == 1 for r in runs):
        return {"answers": answers, "cost": 0.0, "note": "Already evaluated on this set: the answers come from the cache (free)"}
    # the most expensive earlier first run of the most similar configuration (later reruns hit the cache)
    for same in (lambda r: r["system"] == cfg.system and r["model"] == cfg.model and r["react"] == (cfg.react if cfg.system == "proposed" else ""),
                 lambda r: r["system"] == cfg.system and r["model"] == cfg.model,
                 lambda r: r["model"] == cfg.model):
        per = [r["cost_total"] / (r["n"] * r["repeats"]) for r in runs if same(r) and r["n"]]
        if per and max(per) > 0:
            return {"answers": answers, "cost": round(max(per) * answers, 4), "note": "Estimated from a similar earlier run"}
    return {"answers": answers, "cost": round(DEFAULT_PER_ANSWER * answers, 4), "note": "Rough estimate"}


def start(config: str, data: str, labels: str) -> jobs.Job:
    cfg = MarkConfig.parse(config)
    if data not in ("teacher", "silver"):
        raise ValueError("data must be teacher or silver")
    if cfg.system != "b2" and not (status := live_config.model_status(cfg.model))["ok"]:
        raise ValueError(status["reason"])
    n = 100 if data == "silver" else None

    def work(job: jobs.Job) -> dict:
        ex = _experiments()
        res = ex.run(cfg, step="admin", data=data, n=n, labels=labels, on_progress=job.progress)
        s = res["summary"]
        return {"config": cfg.name, "complete": res["complete"], "file": Path(ex.run_path("admin", cfg, data, n, 1, labels)).name,
                "overall": s.get("overall", {}), "cost_total": s.get("cost_total", 0.0), "success_rate": s.get("success_rate")}

    return jobs.start("evaluation", f"Evaluate {cfg.name} on the {data} set", work)
