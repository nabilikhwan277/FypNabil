"""Why constrained ReAct (A2) beats vanilla ReAct (A1), and what the Reflexion critic (A3) changes
(Experiment plan v3, Phase 1.3). Reads the saved Step 3 runs (GPT-6 Luna, R3, memory off) on the 50 teacher
answers, overall and per subject. No model is called.

  process  completion, steps, which tools A1 used and in what order (rubric and textbook read before marking?),
           repeated or unknown actions, calls / tokens / model time / cost per answer
  outcome  criterion verdicts vs the final teacher marks; where A1 and A2 disagree, who was right
  context  did A1 read the same textbook sections as A2 (it writes its own search query)?
  critic   A3: draft verdicts (before the critic) vs final; each change helped, hurt or was neutral

Usage: .venv\\Scripts\\python eval\\react_eval.py  -> eval/results/react_eval.json and .md
"""
from __future__ import annotations

import ast
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "eval"))

from teacher_compare import label_sets  # noqa: E402

RES = ROOT / "eval" / "results"
RUN = "step3__proposed_luna_R3_{}_off__teacherall.json"
TYPES = {"A1": "A1 Vanilla ReAct", "A2": "A2 Constrained ReAct", "A3": "A3 Reflexion"}
SUBJECTS = {"all": "All", "fiqh": "Ibadah", "jawi": "Jawi", "tajwid": "Tajwid"}
PRICE_IN, PRICE_OUT = 0.10 / 1e6, 0.50 / 1e6       # GPT-6 Luna, $ per token (OpenRouter, Oct 2026)
A1_TOOLS = {"get_rubric", "search_notes", "get_history", "submit_marks"}
ORDER = {"tidak": 0, "separa": 1, "ya": 2}


def load(react: str) -> dict[str, dict]:
    r = json.loads((RES / "experiments" / RUN.format(react)).read_text(encoding="utf-8"))
    return {it["answer_id"]: it for it in r["items"] if it["rep"] == 0}


def verdicts(obs) -> dict[int, str]:
    """Criterion verdicts from a score_rubric / submit_marks observation (a dict, or a dict as text)."""
    try:
        d = obs if isinstance(obs, dict) else ast.literal_eval(obs)
    except (ValueError, SyntaxError):
        return {}
    return {int(c["no"]): c["verdict"] for c in d.get("criteria", []) if "no" in c}


def subject(item: dict) -> str:
    return item["question_id"].split("_")[0]


def a1_process(items: list[dict]) -> dict:
    steps, orders, n_rubric, n_notes, n_both, repeats, unknown = [], Counter(), 0, 0, 0, 0, 0
    for it in items:
        acts = [s["action"] for s in it["trace"] if s["action"] != "hard_rules"]
        steps.append(len(acts))
        before = acts[: acts.index("submit_marks")] if "submit_marks" in acts else acts
        n_rubric += "get_rubric" in before
        n_notes += "search_notes" in before
        n_both += "get_rubric" in before and "search_notes" in before
        repeats += len(before) != len(set(before))
        unknown += any(a not in A1_TOOLS for a in acts)
        orders[" → ".join(acts)] += 1
    n = len(items)
    return {"steps_mean": round(float(np.mean(steps)), 2), "steps": dict(Counter(steps)),
            "read_rubric_first": n_rubric / n, "searched_textbook_first": n_notes / n, "did_both": n_both / n,
            "repeated_action": repeats, "unknown_action": unknown, "orders": dict(orders.most_common(5))}


def usage(items: list[dict]) -> dict:
    u = [it["usage"] for it in items]
    cost = [x["tokens_in"] * PRICE_IN + x["tokens_out"] * PRICE_OUT for x in u]
    return {"completed": float(np.mean([it["ok"] for it in items])), "calls": float(np.mean([x["calls"] for x in u])),
            "tokens": float(np.mean([x["tokens_in"] + x["tokens_out"] for x in u])),
            "model_seconds": float(np.mean([x["ms"] for x in u])) / 1000, "cost_per_100": 100 * float(np.mean(cost))}


def main() -> None:
    runs = {t: load(t) for t in TYPES}
    final = label_sets()["final"]
    ids = sorted(final)
    out = {"system": "GPT-6 Luna, R3, memory off (Step 3)", "subjects": {}}
    for g, label in SUBJECTS.items():
        sel = [a for a in ids if g == "all" or subject(runs["A2"][a]) == g]
        s = {"label": label, "answers": len(sel), "types": {}}
        for t in TYPES:
            items = [runs[t][a] for a in sel]
            right = [c["met"] == final[a][i] for a in sel for i, c in enumerate(runs[t][a]["criteria"])]
            s["types"][t] = usage(items) | {"criterion_accuracy": float(np.mean(right)), "criteria": len(right)}
        s["a1_process"] = a1_process([runs["A1"][a] for a in sel])

        # A1 vs A2: criteria where they disagree, and who matches the final teacher mark
        dis = Counter()
        for a in sel:
            for i, (c1, c2) in enumerate(zip(runs["A1"][a]["criteria"], runs["A2"][a]["criteria"])):
                if c1["met"] != c2["met"]:
                    gold = final[a][i]
                    dis["A2 right" if c2["met"] == gold else "A1 right" if c1["met"] == gold else "both wrong"] += 1
        s["a1_vs_a2"] = dict(dis)

        # did A1 read the same textbook sections as A2?
        overlap = []
        for a in sel:
            s1 = {c["id"] for c in runs["A1"][a].get("context") or []}
            s2 = {c["id"] for c in runs["A2"][a].get("context") or []}
            if s2:
                overlap.append(len(s1 & s2) / len(s2))
        s["a1_same_sections_as_a2"] = float(np.mean(overlap)) if overlap else None

        # A3 critic: draft (score_rubric) vs final (after critic)
        crit = Counter()
        for a in sel:
            it = runs["A3"][a]
            draft = next((verdicts(st["observation"]) for st in it["trace"] if st["action"] == "score_rubric"), {})
            for i, c in enumerate(it["criteria"]):
                d = draft.get(i + 1)
                if c["layer"] == "rule" or d is None:
                    continue
                if d == c["met"]:
                    crit["unchanged"] += 1
                else:
                    gold = final[a][i]
                    crit["helped" if c["met"] == gold else "hurt" if d == gold else "changed, both wrong"] += 1
                    crit["more lenient" if ORDER[c["met"]] > ORDER[d] else "stricter"] += 1
        s["a3_critic"] = dict(crit)
        out["subjects"][g] = s
    (RES / "react_eval.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    (RES / "react_eval.md").write_text(markdown(out), encoding="utf-8")
    print(markdown(out))


def markdown(o: dict) -> str:
    s = o["subjects"]
    cols = list(s)
    head = "| | " + " | ".join(f"{s[c]['label']} (n={s[c]['answers']})" for c in cols) + " |"
    sep = "|---|" + "---|" * len(cols)
    row = lambda name, fn: f"| {name} | " + " | ".join(fn(s[c]) for c in cols) + " |"  # noqa: E731
    md = [f"# ReAct types: process and outcome ({o['system']})", ""]
    for t, label in TYPES.items():
        md += [f"## {label}", "", head, sep,
               row("Completed (valid marks)", lambda x: f"{x['types'][t]['completed']:.0%}"),
               row("Criterion verdicts = final teacher mark", lambda x: f"{x['types'][t]['criterion_accuracy']:.0%}"),
               row("Model calls per answer", lambda x: f"{x['types'][t]['calls']:.1f}"),
               row("Tokens per answer", lambda x: f"{x['types'][t]['tokens']:.0f}"),
               row("Model time per answer", lambda x: f"{x['types'][t]['model_seconds']:.1f} s"),
               row("Cost per 100 answers", lambda x: f"${x['types'][t]['cost_per_100']:.3f}"), ""]
    md += ["## A1: what the free tool loop did", "", head, sep,
           row("Steps (mean)", lambda x: f"{x['a1_process']['steps_mean']:.1f}"),
           row("Read the rubric before marking", lambda x: f"{x['a1_process']['read_rubric_first']:.0%}"),
           row("Searched the textbook before marking", lambda x: f"{x['a1_process']['searched_textbook_first']:.0%}"),
           row("Did both", lambda x: f"{x['a1_process']['did_both']:.0%}"),
           row("Repeated an action", lambda x: str(x["a1_process"]["repeated_action"])),
           row("Unknown action", lambda x: str(x["a1_process"]["unknown_action"])),
           row("Same textbook sections as A2", lambda x: f"{x['a1_same_sections_as_a2']:.0%}" if x["a1_same_sections_as_a2"] is not None else "–"),
           "", "Most common A1 step orders (all subjects):", ""]
    md += [f"- {k} ({v})" for k, v in s["all"]["a1_process"]["orders"].items()]
    keys = ["A2 right", "A1 right", "both wrong"]
    md += ["", "## A1 vs A2: criteria where they disagree, who matches the final teacher mark", "", head, sep]
    md += [row(k, lambda x, k=k: str(x["a1_vs_a2"].get(k, 0))) for k in keys]
    keys = ["unchanged", "helped", "hurt", "changed, both wrong", "more lenient", "stricter"]
    md += ["", "## A3: what the critic changed (LLM-marked criteria; draft → final)", "", head, sep]
    md += [row(k, lambda x, k=k: str(x["a3_critic"].get(k, 0))) for k in keys]
    return "\n".join(md) + "\n"


if __name__ == "__main__":
    main()
