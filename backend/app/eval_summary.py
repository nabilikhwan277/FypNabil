"""Everything the evaluation page (📊 Penilaian) shows, read from the result files.

Read-only: nothing here calls a model or spends API credit. Sources
  eval/results/experiments/*.json            experiment runs (eval/experiments.py)
  eval/results/experiments/*.grounding.json  E2 grounding (eval/grounding.py)
  data/teacher/agreement.json                agreement between teachers (scripts/teacher_sheet.py)
  data/teacher/ab_results.json               E3 blind A/B + Likert (scripts/ab_form.py)
  eval/results/sus.json                      SUS (scripts/sus_score.py)
Each block says whether its numbers come from the silver development set or the teacher-marked set.
"""
from __future__ import annotations

import json
from pathlib import Path

from .config import ROOT, get_settings
from .llm_api import MODELS, spent_usd

EXP = ROOT / "eval" / "results" / "experiments"
TEACHER = ROOT / "data" / "teacher"

# Blueprint §4.4 success targets
TARGETS = {
    "qwk": 0.70, "within_1": 0.85, "faithfulness": 0.85, "context_recall": 0.80,
    "win_rate": 0.65, "likert": 4.0, "sus": 68.0,
}


def _read(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _runs() -> list[dict]:
    runs = []
    for p in sorted(EXP.glob("*.json")):
        if p.name.endswith(".grounding.json") or p.name.startswith(("dry__", "adhoc__")):
            continue
        r = _read(p)
        if not r:
            continue
        g = _read(p.with_name(p.stem + ".grounding.json"))
        s = r["summary"]
        runs.append({
            "file": p.name, "step": r["step"], "config": r["config"], "system": r["system"],
            "model": r.get("model", ""), "model_label": r.get("model_label") or ("Local rules + bge-m3" if r["system"] == "b2" else ""),
            "rag": r.get("rag", ""), "react": r.get("react", ""), "memory": r.get("memory", False),
            "data": r["data"], "labels": r["labels"], "n": r["n"], "repeats": r["repeats"], "date": r["date"],
            "complete": r.get("complete", True),
            "overall": s.get("overall", {}), "by_subject": s.get("by_subject", {}), "by_level": s.get("by_level", {}),
            "keyword_illusion": s.get("by_kind", {}).get("keyword_illusion"),
            "success_rate": s.get("success_rate"), "latency_ms": s.get("latency_ms"), "cost_total": s.get("cost_total"),
            "cost_per_100": s.get("cost_per_100"), "calls_per_answer": s.get("calls_per_answer"),
            "tokens_per_answer": s.get("tokens_per_answer"), "cov_pct": s.get("cov_pct"),
            "same_score_all_repeats": s.get("same_score_all_repeats"), "worst": s.get("worst", [])[:8],
            "grounding": g["summary"] if g else None,
            "unsupported_examples": [u for it in (g or {}).get("items", []) for u in it.get("unsupported", [])][:6],
        })
    return runs


def _final(runs: list[dict], data: str) -> dict | None:
    """Final configuration = step 4 with memory on (the full proposed system), for the given data."""
    s4 = [r for r in runs if r["step"] == "step4" and r["data"] == data]
    return next((r for r in s4 if r["memory"]), s4[0] if s4 else None)


def _target(value, target, higher=True) -> dict:
    met = None if value is None else (value >= target if higher else value <= target)
    return {"value": value, "target": target, "met": met}


def summary() -> dict:
    s = get_settings()
    runs = _runs()
    teacher_ready = (TEACHER / "teacher_test.json").exists() or (TEACHER / "labels").exists()
    data = "teacher" if any(r["data"] == "teacher" for r in runs) else "silver"
    # teacher runs are final only once the disputed marks are settled (data/teacher/teacher_test.json)
    labels = "teacher" if data == "teacher" and (TEACHER / "teacher_test.json").exists() else (
        "teacher-provisional" if data == "teacher" else "silver")
    final = _final(runs, data)
    agreement = _read(TEACHER / "agreement.json")
    ab = _read(TEACHER / "ab_results.json")
    sus = _read(ROOT / "eval" / "results" / "sus.json")
    compare = _read(ROOT / "eval" / "results" / "teacher_compare.json")
    rag = _read(ROOT / "eval" / "results" / "rag_eval.json")
    if rag:   # summaries only; a few example answers per RAG type
        rag = {k: v for k, v in rag.items() if k != "questions"} | {"rags": [
            {"rag": r["rag"], "summary": r["summary"],
             "examples": [{"question": it["question"], "answer": it["answer"], "reference": it["reference"]}
                          for it in r["items"][:3]]} for r in rag["rags"]]}
    rag_settings = _read(ROOT / "eval" / "results" / "rag_settings.json")
    if rag_settings:   # the settings study of R3: summaries only (no per-question rows)
        rag_settings = {k: v for k, v in rag_settings.items() if k != "questions"} | {"settings": [
            s | {"options": [{k: v for k, v in o.items() if k not in ("per_question", "answer_items", "config")}
                             for o in s["options"]]} for s in rag_settings["settings"]]}
    g = (final or {}).get("grounding") or {}
    o = (final or {}).get("overall") or {}
    sus_teachers = ((sus or {}).get("groups") or {}).get("guru") or ((sus or {}).get("groups") or {}).get("Semua")
    targets = {
        "qwk": _target(o.get("qwk_band"), TARGETS["qwk"]),
        "within_1": _target(o.get("within_1"), TARGETS["within_1"]),
        "faithfulness": _target(g.get("faithfulness"), TARGETS["faithfulness"]),
        "context_recall": _target(g.get("context_recall"), TARGETS["context_recall"]),
        "win_rate": _target((ab or {}).get("win_rate"), TARGETS["win_rate"]),
        "likert": _target(((ab or {}).get("likert_mean") or {}).get("on"), TARGETS["likert"]),
        "sus": _target((sus_teachers or {}).get("mean"), TARGETS["sus"]),
        "cov": {"value": (final or {}).get("cov_pct"), "target": "lower than between teachers", "met": None},
    }
    if compare and compare.get("runs"):
        # E1 with several teachers: the system should agree with the teachers at least as well as they agree with each other
        fr = next((r for r in compare["runs"] if final and r["config"] == final["config"]), compare["runs"][0])
        targets["human_level"] = {"value": fr["mean_qwk_teachers"], "target": compare.get("human_qwk"),
                                  "met": fr.get("human_level"), "config": fr["config"]}
    return {
        "labels": labels,
        "teacher_data_ready": teacher_ready,
        "final": final,
        "targets": targets,
        "runs": runs,
        "agreement": agreement,
        "teacher_compare": compare,
        "rag_eval": rag,
        "rag_settings": rag_settings,
        "ab": ab,
        "sus": sus,
        "models": [{"key": m.key, "label": m.label, "id": m.id, "provider": m.provider, "local": m.local} for m in MODELS.values()],
        "spend": {"spent": spent_usd(), "budget": s.llm_budget_usd},
        "live_scorer": s.scorer,
    }
