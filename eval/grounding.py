"""E2 automated grounding (RAGAS-style metrics), blueprint §4.3 Layer 3.

For every answer of an experiment run that has feedback:
  faithfulness       claims in the feedback that the support material backs / all claims
  unsupported claims the claims that are NOT backed (the main guard against wrong rulings)
  context recall     statements of the reference answer that the retrieved text contains
  context precision  are the retrieved chunks relevant, weighted by rank (RAGAS average precision)
Support material = the retrieved textbook text + the reference answer (both are official KAFA material).

The judge is a model from a DIFFERENT provider than the model under test, to avoid self-preference:
  Anthropic (Haiku) is judged by OpenAI (GPT-6 Luna); everything else is judged by Haiku.
The metrics are implemented here (not with the `ragas` package) so they run through OpenRouter and the
judge prompts can be shown in the thesis. `check` exports a sample of judgements to verify by hand.

Usage
  .venv\\Scripts\\python eval\\grounding.py run <experiment file or name fragment> [--n 30]
  .venv\\Scripts\\python eval\\grounding.py check <experiment file or fragment>   -> CSV for hand-checking
Results: eval/results/experiments/<run>.grounding.json
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.app.llm_api import MODELS, complete, spent_usd  # noqa: E402
from backend.app.questions import load_questions  # noqa: E402

EXP = ROOT / "eval" / "results" / "experiments"

FAITH_RULES = """You verify feedback that a marking system gave to a Year 5 KAFA pupil.
1. Split the feedback into short factual claims about the subject (rulings, numbers, definitions, spellings, what the correct answer is).
   Ignore encouragement, greetings and remarks about the pupil's effort.
2. For each claim decide if the SUPPORT MATERIAL (textbook text and reference answer) supports it.
   A claim about what the pupil wrote counts as supported if it matches the pupil's answer.
If there are no factual claims, return an empty list."""
FAITH_SCHEMA = {"type": "object", "properties": {"claims": {"type": "array", "items": {
    "type": "object", "properties": {"claim": {"type": "string"}, "supported": {"type": "boolean"}},
    "required": ["claim", "supported"], "additionalProperties": False}}},
    "required": ["claims"], "additionalProperties": False}

CONTEXT_RULES = """You judge the textbook passages that a retrieval system found for marking one question.
A. Split the REFERENCE ANSWER into short statements and decide for each whether the PASSAGES contain that information ("attributed").
B. For each passage (by its number) decide whether it is relevant, i.e. useful for marking this question."""
CONTEXT_SCHEMA = {"type": "object", "properties": {
    "statements": {"type": "array", "items": {"type": "object", "properties": {
        "statement": {"type": "string"}, "attributed": {"type": "boolean"}},
        "required": ["statement", "attributed"], "additionalProperties": False}},
    "passages": {"type": "array", "items": {"type": "object", "properties": {
        "index": {"type": "integer"}, "relevant": {"type": "boolean"}},
        "required": ["index", "relevant"], "additionalProperties": False}}},
    "required": ["statements", "passages"], "additionalProperties": False}


def judge_for(model_key: str) -> str:
    provider = MODELS[model_key].provider if model_key in MODELS else ""
    return "luna" if provider == "anthropic" else "haiku"


def _reference(q: dict) -> str:
    return q.get("reference_answer_rumi", "") or q.get("reference_answer_jawi", "")


def _support(item: dict, q: dict) -> str:
    ctx = "\n\n".join(c["text"] for c in item.get("context") or [])
    return f"TEXTBOOK TEXT:\n<<<\n{ctx or '(none)'}\n>>>\n\nREFERENCE ANSWER:\n{_reference(q)}"


def judge_item(item: dict, q: dict, judge: str) -> dict:
    out = {"answer_id": item["answer_id"], "question_id": item["question_id"], "feedback": item["feedback"]}
    f = complete(judge, [{"role": "system", "content": FAITH_RULES},
                         {"role": "user", "content": f"QUESTION: {q.get('question_rumi', '')}\n\nPUPIL ANSWER:\n{item['answer']}\n\n"
                                                     f"{_support(item, q)}\n\nFEEDBACK:\n<<<\n{item['feedback']}\n>>>"}],
                 schema=FAITH_SCHEMA, max_tokens=900, tag="e2:faithfulness")
    claims = (f.data or {}).get("claims") or []
    out["claims"] = claims
    out["faithfulness"] = sum(bool(c.get("supported")) for c in claims) / len(claims) if claims else None
    out["unsupported"] = [c.get("claim", "") for c in claims if not c.get("supported")]
    ctx = item.get("context") or []
    if ctx:
        passages = "\n\n".join(f"[{i}] {c['text']}" for i, c in enumerate(ctx, 1))
        c = complete(judge, [{"role": "system", "content": CONTEXT_RULES},
                             {"role": "user", "content": f"QUESTION: {q.get('question_rumi', '')}\n\nREFERENCE ANSWER:\n{_reference(q)}\n\n"
                                                         f"PASSAGES:\n{passages}"}],
                     schema=CONTEXT_SCHEMA, max_tokens=900, tag="e2:context")
        d = c.data or {}
        st = d.get("statements") or []
        out["context_recall"] = sum(bool(s.get("attributed")) for s in st) / len(st) if st else None
        rel = {int(p.get("index", 0)): bool(p.get("relevant")) for p in d.get("passages") or []}
        flags = [rel.get(i, False) for i in range(1, len(ctx) + 1)]
        hits, ap = 0, 0.0
        for k, r in enumerate(flags, 1):   # RAGAS context precision = average precision over relevant ranks
            if r:
                hits += 1
                ap += hits / k
        out["context_precision"] = ap / hits if hits else 0.0
        out["relevant_flags"] = flags
    out["cost"] = f.cost + (c.cost if ctx else 0.0)
    return out


def _find(name: str) -> Path:
    p = Path(name)
    if p.exists():
        return p
    hits = [x for x in EXP.glob(f"*{name}*.json") if not x.name.endswith(".grounding.json")]
    if len(hits) != 1:
        sys.exit(f"{len(hits)} experiment files match '{name}': {[h.name for h in hits]}")
    return hits[0]


def _mean(xs: list) -> float | None:
    xs = [x for x in xs if x is not None]
    return round(statistics.mean(xs), 3) if xs else None


def run(name: str, n: int | None, workers: int = 4) -> dict:
    path = _find(name)
    exp = json.loads(path.read_text(encoding="utf-8"))
    qs = load_questions()
    items = [it for it in exp["items"] if it["rep"] == 0 and it.get("feedback")][: n or None]
    judge = judge_for(exp["model"])
    print(f"E2 on {path.name}: {len(items)} answers, judge {MODELS[judge].label} (spent so far ${spent_usd():.4f})")
    with ThreadPoolExecutor(max_workers=workers) as ex:
        res = list(ex.map(lambda it: judge_item(it, qs[it["question_id"]], judge), items))
    summary = {"faithfulness": _mean([r["faithfulness"] for r in res]),
               "context_recall": _mean([r.get("context_recall") for r in res]),
               "context_precision": _mean([r.get("context_precision") for r in res]),
               "unsupported_per_answer": round(sum(len(r["unsupported"]) for r in res) / len(res), 3) if res else None,
               "answers_with_unsupported": round(sum(bool(r["unsupported"]) for r in res) / len(res), 3) if res else None,
               "n": len(res), "judge": MODELS[judge].label, "judge_model": MODELS[judge].id,
               "cost": round(sum(r["cost"] for r in res), 6)}
    out = {"experiment": path.name, "config": exp["config"], "labels": exp["labels"], "summary": summary, "items": res}
    dest = path.with_name(path.stem + ".grounding.json")
    dest.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"  faithfulness {summary['faithfulness']}  recall {summary['context_recall']}  precision {summary['context_precision']}"
          f"  unsupported/answer {summary['unsupported_per_answer']}  ${summary['cost']:.4f} -> {dest.name}")
    return out


def check(name: str, k: int = 20) -> None:
    """Export k claim judgements for a person to verify (the blueprint's hand-checked sample)."""
    g = json.loads(_find(name).with_name(_find(name).stem + ".grounding.json").read_text(encoding="utf-8"))
    rows = [(it["answer_id"], it["feedback"], c["claim"], "ya" if c["supported"] else "tidak")
            for it in g["items"] for c in it.get("claims", [])][:k]
    dest = EXP / f"{_find(name).stem}.grounding_check.csv"
    with dest.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["answer_id", "feedback", "claim", "judge_supported", "your_check (ya/tidak)"])
        w.writerows([*r, ""] for r in rows)
    print(f"{len(rows)} judgements -> {dest}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["run", "check"])
    ap.add_argument("experiment")
    ap.add_argument("--n", type=int, default=30)
    a = ap.parse_args()
    run(a.experiment, a.n or None) if a.cmd == "run" else check(a.experiment)
