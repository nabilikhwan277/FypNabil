"""The marking system pupils get, chosen by the admin (Admin → Evaluation → System setup).

A configuration name is the same as in the experiments (eval/experiments.py), e.g. "b2" (local rules +
bge-m3, free) or "proposed:luna:R3:A2:on". The admin's choice is saved in runtime settings; without one,
KAFA_SCORER from .env is used. If the chosen model cannot answer, marking falls back to b2 (pipeline.py).
"""
from __future__ import annotations

from datetime import datetime, timezone

from . import remote_llm, runtime
from .assess.llm_marking import REACT_TYPES, MarkConfig
from .config import get_settings
from .kb.rag import RAG_TYPES
from .llm_api import MODELS, open_model_problem

SYSTEM_LABELS = {
    "b2": "B2 Rules + bge-m3 similarity (local, free)",
    "b1": "B1 Zero-shot LLM",
    "b3": "B3 RAG + rubric",
    "b4": "B4 RAG + rubric + verifier",
    "proposed": "Proposed system (hard rules + RAG + ReAct + memory)",
}
RAG_LABELS = {"R1": "R1 Naive dense", "R2": "R2 Hybrid + reranker", "R3": "R3 Parent-document"}
REACT_LABELS = {"A1": "A1 Vanilla ReAct (tool loop)", "A2": "A2 Constrained ReAct (fixed steps)",
                "A3": "A3 Reflexion (draft + critic)"}


def current() -> str:
    return runtime.load().get("scorer") or get_settings().scorer


def model_status(key: str) -> dict:
    """Can this model answer right now? API models need the OpenRouter key; Qwen needs its Colab link."""
    spec = MODELS[key]
    if spec.local:
        if problem := open_model_problem(spec):
            return {"ok": False, "where": "", "reason": problem}
        return {"ok": True, "where": "Google Colab" if remote_llm.endpoint() is not None else "this laptop"}
    if not get_settings().openrouter_api_key:
        return {"ok": False, "where": "", "reason": "KAFA_OPENROUTER_API_KEY is not set in .env"}
    return {"ok": True, "where": "OpenRouter API"}


def describe(name: str) -> dict:
    cfg = MarkConfig.parse(name)
    uses_llm = cfg.system != "b2"
    parts = {"system": cfg.system, "system_label": SYSTEM_LABELS[cfg.system],
             "model": cfg.model if uses_llm else "", "model_label": MODELS[cfg.model].label if uses_llm else "",
             "rag": cfg.rag if cfg.system in ("b3", "b4", "proposed") else "",
             "react": cfg.react if cfg.system == "proposed" else "",
             "memory": cfg.memory if cfg.system == "proposed" else None}
    parts["rag_label"] = RAG_LABELS.get(parts["rag"], "")
    parts["react_label"] = REACT_LABELS.get(parts["react"], "")
    return {"config": cfg.name, **parts}


def set_current(name: str) -> dict:
    cfg = MarkConfig.parse(name)   # ValueError for an unknown system or model
    if cfg.system != "b2":
        status = model_status(cfg.model)
        if not status["ok"]:
            raise ValueError(f"{MODELS[cfg.model].label} cannot answer now: {status['reason']}")
    runtime.update(scorer=cfg.name, scorer_set_at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    return describe(cfg.name)


def options() -> dict:
    return {
        "systems": [{"key": k, "label": v} for k, v in SYSTEM_LABELS.items()],
        "models": [{"key": k, "label": m.label, "provider": m.provider, **model_status(k)} for k, m in MODELS.items()],
        "rags": [{"key": k, "label": RAG_LABELS[k]} for k in RAG_TYPES],
        "reacts": [{"key": k, "label": REACT_LABELS[k]} for k in REACT_TYPES],
    }
