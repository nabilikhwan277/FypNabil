"""Phase 4 sanity check of the full ReAct scoring with the real models.

There are no teacher-marked student answers yet, so this uses synthetic
answers on the TRAIN split:
  correct_rumi - the question's own Rumi reference answer    -> expect full marks
  correct_jawi - the question's own Jawi reference answer    -> expect full marks
  wrong        - the reference answer of a random question
                 from another topic in the same subject      -> expect 0

This is a lower bar than the teacher-marked evaluation (Phase 7): it checks
that correct answers are not under-marked and irrelevant answers are not
rewarded. Real partial/paraphrased answers are harder.

Usage: .venv\\Scripts\\python eval\\sanity_scoring.py [limit]
Writes eval/results/sanity_scoring.json and .md
"""
import json
import random
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.app.assess.pipeline import llm_generate  # noqa: E402
from backend.app.assess.react import run_react  # noqa: E402
from backend.app.assess.rubric import is_spelling_criterion  # noqa: E402
from backend.app.embeddings import embed  # noqa: E402
from backend.app.kb.retriever import search_notes  # noqa: E402
from backend.app.memory.db import TopicHistory  # noqa: E402
from backend.app.notes import source_label  # noqa: E402
from backend.app.questions import load_questions, load_split  # noqa: E402

rng = random.Random(7)


def run_one(q, answer):
    t0 = time.perf_counter()
    res = run_react(q, answer, search=search_notes, embed=embed, history=lambda t: TopicHistory(t),
                    source=source_label, generate=llm_generate, use_llm_feedback=False)
    return res.rubric, int((time.perf_counter() - t0) * 1000)


def main(limit: int | None) -> None:
    qs = load_questions()
    ids = [i for i in load_split("train") if i in qs]
    if limit:
        rng.shuffle(ids)
        ids = sorted(ids[:limit])
    by_subject_topic = defaultdict(list)
    for q in qs.values():
        by_subject_topic[q["subject"]].append(q)

    rows = []
    t_start = time.perf_counter()
    for n, qid in enumerate(ids, 1):
        q = qs[qid]
        others = [o for o in by_subject_topic[q["subject"]]
                  if o["topic_id"] != q["topic_id"] and o.get("reference_answer_rumi")]
        # A Rumi answer to "write this in Jawi" SHOULD score 0, so that case is not a
        # valid "correct" answer for questions whose criteria are all Jawi spelling.
        spelling_only = all(is_spelling_criterion(q, c.get("keywords", [])) for c in q["rubric"])
        cases = {"correct_rumi": "" if spelling_only else q.get("reference_answer_rumi", ""),
                 "correct_jawi": q.get("reference_answer_jawi", ""),
                 "wrong": rng.choice(others)["reference_answer_rumi"] if others else ""}
        for case, ans in cases.items():
            if not ans.strip():
                continue
            r, ms = run_one(q, ans)
            rows.append({"id": qid, "subject": q["subject"], "level": q["level"], "case": case,
                         "percent": r.percent, "llm_calls": r.llm_calls, "ms": ms,
                         "layers": [c.layer for c in r.criteria],
                         "llm_sims": [c.similarity for c in r.criteria if c.layer in ("B-llm", "B-guard")],
                         "llm_verdicts": [c.llm_verdict for c in r.criteria if c.layer.startswith("B-")],
                         "missed": [c.criterion for c in r.criteria if c.awarded < c.marks],
                         "answer": ans[:120]})
        if n % 25 == 0:
            print(f"  {n}/{len(ids)} questions, {time.perf_counter() - t_start:.0f}s")

    def summary(sel):
        if not sel:
            return {}
        p = [r["percent"] for r in sel]
        ms = sorted(r["ms"] for r in sel)
        return {"n": len(sel), "mean_percent": round(sum(p) / len(p), 1),
                "full_marks": round(sum(x >= 100 for x in p) / len(p), 3),
                "zero": round(sum(x == 0 for x in p) / len(p), 3),
                "llm_calls_per_answer": round(sum(r["llm_calls"] for r in sel) / len(sel), 2),
                "median_ms": ms[len(ms) // 2], "p95_ms": ms[int(len(ms) * 0.95) - 1]}

    out = {"split": "train", "questions": len(ids), "results": {}}
    for case in ("correct_rumi", "correct_jawi", "wrong"):
        out["results"][case] = {"all": summary([r for r in rows if r["case"] == case])}
        for key, fn in (("subject", lambda r: r["subject"]), ("level", lambda r: f"L{r['level']}")):
            for val in sorted({fn(r) for r in rows}):
                out["results"][case][val] = summary([r for r in rows if r["case"] == case and fn(r) == val])
    out["layer_counts"] = {case: dict(Counter(layer for r in rows if r["case"] == case for layer in r["layers"]))
                           for case in ("correct_rumi", "correct_jawi", "wrong")}
    # Raw LLM judge verdicts (before the similarity guard): does the LLM discriminate?
    out["llm_verdicts"] = {case: dict(Counter(str(v) for r in rows if r["case"] == case for v in r["llm_verdicts"]))
                           for case in ("correct_rumi", "correct_jawi", "wrong")}
    out["failures"] = {
        "correct_not_full": [r for r in rows if r["case"].startswith("correct") and r["percent"] < 100][:60],
        "wrong_not_zero": [r for r in rows if r["case"] == "wrong" and r["percent"] > 0][:60],
    }
    res_dir = ROOT / "eval" / "results"
    res_dir.mkdir(parents=True, exist_ok=True)
    (res_dir / "sanity_scoring.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = ["# Scoring sanity check (train split, synthetic answers)", "",
             "| Case | Group | n | Mean % | Full marks | Zero | LLM calls/answer | Median ms | p95 ms |",
             "|---|---|---|---|---|---|---|---|---|"]
    for case, groups in out["results"].items():
        for g, s in groups.items():
            if s:
                lines.append(f"| {case} | {g} | {s['n']} | {s['mean_percent']} | {s['full_marks']:.3f} | "
                             f"{s['zero']:.3f} | {s['llm_calls_per_answer']} | {s['median_ms']} | {s['p95_ms']} |")
    lines += ["", "## Layer usage", ""]
    for case, cnt in out["layer_counts"].items():
        lines.append(f"- **{case}**: " + ", ".join(f"{k} {v}" for k, v in sorted(cnt.items(), key=lambda x: -x[1])))
    lines += ["", "## Raw LLM judge verdicts (before guard)", ""]
    for case, cnt in out["llm_verdicts"].items():
        lines.append(f"- **{case}**: " + (", ".join(f"{k} {v}" for k, v in sorted(cnt.items())) or "no LLM calls"))
    for name, items in out["failures"].items():
        lines += ["", f"## {name} ({len(items)} shown)", ""]
        for r in items[:25]:
            lines.append(f"- `{r['id']}` {r['case']} {r['percent']}% layers={r['layers']} missed={r['missed']}")
    (res_dir / "sanity_scoring.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    for case, groups in out["results"].items():
        s = groups["all"]
        print(f"{case:<13} n={s['n']:<4} mean={s['mean_percent']:>5}%  full={s['full_marks']:.3f}  "
              f"zero={s['zero']:.3f}  llm/ans={s['llm_calls_per_answer']}  median={s['median_ms']}ms")
    print("saved eval/results/sanity_scoring.json/.md")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else None)
