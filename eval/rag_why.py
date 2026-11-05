"""Why each RAG type failed where it did (Experiment plan v3, Phase 1.4). No model is called.

A question "fails" when the answer was declined or its factual correctness is below 0.5. Its cause comes from the
gold evidence (rag_gold.json: the textbook lines that state each statement of the reference answer), checked
against the text the answer model actually read:
  limit cut        no evidence in the text read, and passages were dropped by the context limit
  wrong section    no evidence in the text read, nothing dropped: retrieval found the wrong sections
  partly found     some statements' evidence read, others missing (the answer is spread over sections)
  answer model     all evidence was read, yet the answer was declined or wrong (a generation problem)
Counts per RAG type and subject, with examples.

Usage: .venv\\Scripts\\python eval\\rag_why.py  -> eval/results/rag_why.json and .md
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

RES = Path(__file__).resolve().parent / "results"
SUBJECTS = {"all": "All", "fiqh": "Ibadah", "jawi": "Jawi", "tajwid": "Tajwid"}
CAUSES = ["limit cut", "wrong section", "partly found", "answer model"]
FAIL = 0.5


def evidence(item: dict, gold: dict) -> float | None:
    """Share of reference statements whose supporting line is in the text the model read (None: not in the notes)."""
    stmts = [s for s in gold["statements"] if s["lines"]]
    if not stmts:
        return None
    text = "\n\n".join(c["text"] for c in item["context"])
    return sum(any(ln in text for ln in s["lines"]) for s in stmts) / len(stmts)


def cause(item: dict, recall: float | None) -> str:
    if recall is None:
        return "not in the notes"
    if recall == 0:
        return "limit cut" if item.get("retrieved", 0) > item.get("passages_given", 0) else "wrong section"
    return "partly found" if recall < 1 else "answer model"


def main() -> None:
    gold = json.loads((RES / "rag_gold.json").read_text(encoding="utf-8"))
    rags = json.loads((RES / "rag_eval.json").read_text(encoding="utf-8"))["rags"]
    out = {"fail_rule": f"declined, or factual correctness < {FAIL}", "rags": {}}
    for r in rags:
        counts = {g: Counter() for g in SUBJECTS}
        examples = []
        for it in r["items"]:
            failed = it["declined"] or (it.get("factual_correctness") or 0) < FAIL
            if not failed:
                continue
            rec = evidence(it, gold[it["question_id"]])
            c = cause(it, rec)
            counts["all"][c] += 1
            counts[it["subject"]][c] += 1
            examples.append({"question_id": it["question_id"], "subject": it["subject"], "question": it["question"],
                             "cause": c, "evidence_read": rec, "declined": it["declined"],
                             "passages": f"{it.get('passages_given')} of {it.get('retrieved')} read",
                             "answer": it["answer"][:200], "reference": it["reference"][:200]})
        out["rags"][r["rag"]] = {"failed": {g: sum(c.values()) for g, c in counts.items()},
                                 "questions": {g: sum(i["subject"] == g or g == "all" for i in r["items"]) for g in SUBJECTS},
                                 "causes": {g: dict(c) for g, c in counts.items()}, "examples": examples}
    (RES / "rag_why.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    (RES / "rag_why.md").write_text(markdown(out), encoding="utf-8")
    print(markdown(out).split("\n## Examples")[0])


def markdown(o: dict) -> str:
    md = [f"# Why the RAG types failed (a failure = {o['fail_rule']})", "",
          "| RAG type | Cause | " + " | ".join(SUBJECTS.values()) + " |", "|---|---|" + "---|" * len(SUBJECTS)]
    for rag, d in o["rags"].items():
        md.append(f"| **{rag}** | **failed / questions** | " + " | ".join(
            f"**{d['failed'][g]} / {d['questions'][g]}**" for g in SUBJECTS) + " |")
        for c in CAUSES + ["not in the notes"]:
            if any(d["causes"][g].get(c) for g in SUBJECTS):
                md.append(f"| | {c} | " + " | ".join(str(d["causes"][g].get(c, 0)) for g in SUBJECTS) + " |")
    md += ["", "Causes: *limit cut* = the evidence was retrieved but dropped by the context limit; *wrong section* = "
           "retrieval missed it; *partly found* = the answer is spread over sections and only some were read; "
           "*answer model* = everything was read but the answer was declined or wrong.", "", "## Examples", ""]
    for rag, d in o["rags"].items():
        md += [f"### {rag}", ""]
        for e in d["examples"]:
            ev = "–" if e["evidence_read"] is None else f"{e['evidence_read']:.0%}"
            md += [f"- **{e['question_id']}** ({e['cause']}; evidence read {ev}; {e['passages']}"
                   f"{'; declined' if e['declined'] else ''}): {e['question']}",
                   f"  - Answer: {e['answer']}", f"  - Reference: {e['reference']}"]
        md.append("")
    return "\n".join(md) + "\n"


if __name__ == "__main__":
    main()
