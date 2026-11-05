"""Phase 7: final evaluation on the held-out TEST split (run once, after tuning).

Part A (offline, cached features): scoring agreement with the silver labels for
  the chosen configuration vs the Phase 4 baseline - overall, by subject,
  level, answer family/kind and answer script.
Part B (live pipeline, real models): consistency (same answer x3), latency by
  level, error rate, grounded-feedback checks, and that the live scores match
  the offline replay (proves Part A measures the production code).

Labels are SILVER (AI-written and AI-labelled), not teacher marks. Replace
with teacher-marked answers via scripts/import_teacher_marks.py for the final
thesis figures.

Usage: .venv\\Scripts\\python eval\\evaluate.py [live_sample=60]
Writes eval/results/evaluation_test.json and .md
"""
from __future__ import annotations

import json
import random
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "eval"))

from scoring_lib import PHASE4, grouped, load_features, metrics, score_items  # noqa: E402

from backend.app.assess.decision import load_config  # noqa: E402

RES = ROOT / "eval" / "results"


def part_a(items: list[dict]) -> dict:
    chosen = load_config()
    out = {"chosen": chosen.to_dict(), "configs": {}}
    for cfg in (PHASE4, chosen):
        sc = score_items(items, cfg)
        out["configs"][cfg.name] = {
            "overall": metrics(sc),
            "by_subject": grouped(sc, lambda i: i["subject"]),
            "by_level": grouped(sc, lambda i: f"Tahap {i['level']}"),
            "by_family": grouped(sc, lambda i: i["family"]),
            "by_kind": grouped(sc, lambda i: i["kind"]),
            "by_script": grouped(sc, lambda i: i["script"] or "?"),
        }
        if cfg is chosen:
            out["worst"] = sorted(
                ({"answer_id": i["answer_id"], "gold": i["gold"], "pred": i["pred"], "max": i["max_marks"]}
                 for i in sc if abs(i["pred"] - i["gold"]) > 0),
                key=lambda x: -abs(x["pred"] - x["gold"]) / x["max"])[:20]
            out["_scored"] = {i["answer_id"]: i["pred"] for i in sc}
    return out


def part_b(sample: int, offline_pred: dict[str, float]) -> dict:
    from silver import load_silver

    from backend.app.assess import pipeline
    from backend.app.memory.db import MemoryStore

    rng = random.Random(5)
    items = load_silver("test")
    by_level: dict[int, list] = {}
    qs = pipeline.load_questions()
    for it in items:
        by_level.setdefault(qs[it["question_id"]]["level"], []).append(it)
    pick = [it for lv in sorted(by_level) for it in rng.sample(by_level[lv], min(sample // 3, len(by_level[lv])))]
    mem = MemoryStore(":memory:")
    sid = mem.get_or_create_student("Eval", "test")["id"]
    pipeline.assess(sid, pick[0]["question_id"], pick[0]["answer"], memory=mem, save=False)  # warm-up

    rows, errors = [], 0
    for it in pick:
        runs = []
        for _ in range(3):
            try:
                t0 = time.perf_counter()
                r = pipeline.assess(sid, it["question_id"], it["answer"], memory=mem, save=False)
                runs.append((r.score, int((time.perf_counter() - t0) * 1000), r))
            except Exception as e:  # noqa: BLE001 - counted as a processing failure
                errors += 1
                print("  error", it["answer_id"], e)
        if not runs:
            continue
        q = qs[it["question_id"]]
        fb = runs[0][2].feedback
        rows.append({
            "answer_id": it["answer_id"], "level": q["level"],
            "scores": [s for s, _, _ in runs], "ms": [m for _, m, _ in runs],
            "consistent": len({s for s, _, _ in runs}) == 1,
            "matches_offline": it["answer_id"] not in offline_pred or abs(runs[0][0] - offline_pred[it["answer_id"]]) < 1e-9,
            "grounded": fb["correct_answer"]["rumi"] == q.get("reference_answer_rumi", "")
                        and bool(fb["source"]["book_pages"]) and len(runs[0][2].trace) == 5,
        })
    lat = {}
    for lv in (1, 2, 3):
        ms = sorted(m for r in rows if r["level"] == lv for m in r["ms"])
        if ms:
            lat[f"Tahap {lv}"] = {"n": len(ms), "median_ms": ms[len(ms) // 2],
                                  "p95_ms": ms[min(len(ms) - 1, int(len(ms) * 0.95))],
                                  "mean_ms": int(statistics.mean(ms))}
    n = len(rows)
    compared = [r for r in rows if r["answer_id"] in offline_pred]
    return {
        "answers": n, "runs": n * 3, "errors": errors,
        "success_rate": round((n * 3 - errors) / (n * 3 + errors), 3) if n else 0,
        "consistency": round(sum(r["consistent"] for r in rows) / n, 3) if n else None,
        "offline_match": round(sum(r["matches_offline"] for r in compared) / len(compared), 3) if compared else None,
        "grounded_feedback": round(sum(r["grounded"] for r in rows) / n, 3) if n else None,
        "latency": lat, "rows": rows,
    }


def fmt_row(name: str, m: dict) -> str:
    return (f"| {name} | {m['items']} | {m['item_exact']:.3f} | {m['within_1']:.3f} | {m['mae_marks']:.2f} | "
            f"{m['mae_pct']} | {m['qwk_band']:.3f} | {m['crit_acc']:.3f} | {m['over_marked']:.3f} | {m['under_marked']:.3f} |")


def main(sample: int, split: str = "test") -> None:
    feats = load_features(split)
    a = part_a(feats)
    offline = a.pop("_scored")
    b = part_b(sample, offline) if sample else {}
    RES.mkdir(parents=True, exist_ok=True)
    (RES / f"evaluation_{split}.json").write_text(json.dumps({"part_a": a, "part_b": b}, indent=1, ensure_ascii=False),
                                              encoding="utf-8")

    head = ("| Group | n | Exact | Within 1 mark | MAE (marks) | MAE % | QWK | Criterion acc | Over-marked | Under-marked |\n"
            "|---|---|---|---|---|---|---|---|---|---|")
    chosen = a["chosen"]["name"]
    label_note = ("> Labels are **teacher marks**: two KAFA teachers marked each answer independently and settled "
                  "disagreements together (see data/teacher/agreement.md)." if split == "teacher" else
                  "> Labels are **silver**: AI-written answers marked by an AI 'strict teacher', plus rule-built "
                  "answers whose mark is known by construction. They are NOT teacher marks. Treat these as a "
                  "development estimate; the thesis figures must come from teacher-marked answers.")
    md = [f"# Phase 7 evaluation ({split} split)", "", label_note, "",
          f"Chosen configuration: `{chosen}` (Tahap 1 `{a['chosen']['l1']['method']}`, "
          f"Tahap 2/3 `{a['chosen']['l23']['method']}`), tuned on train only.", "",
          "## Overall", "", head]
    for name, c in a["configs"].items():
        md.append(fmt_row(name, c["overall"]))
    for group in ("by_level", "by_subject", "by_family", "by_script", "by_kind"):
        md += ["", f"## {group.replace('by_', 'By ').title()} ({chosen})", "", head]
        for k, m in a["configs"][chosen][group].items():
            md.append(fmt_row(k, m))
    if b:
        md += ["", "## Live pipeline (real models)", "",
               f"- Answers run: {b['answers']} x 3 = {b['runs']} assessments, errors: {b['errors']} "
               f"(success rate {b['success_rate']})",
               f"- Consistency (same answer, same score in all 3 runs): **{b['consistency']}**",
               f"- Live score = offline replay: {b['offline_match']}",
               f"- Feedback grounded (correct answer = reference, textbook page given, 5-step trace): {b['grounded_feedback']}",
               "", "| Level | runs | median ms | p95 ms | mean ms |", "|---|---|---|---|---|"]
        md += [f"| {k} | {v['n']} | {v['median_ms']} | {v['p95_ms']} | {v['mean_ms']} |" for k, v in b["latency"].items()]
    md += ["", "## Largest disagreements", ""]
    md += [f"- `{w['answer_id']}` silver {w['gold']} / predicted {w['pred']} (max {w['max']})" for w in a["worst"]]
    (RES / f"evaluation_{split}.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    for name, c in a["configs"].items():
        o = c["overall"]
        print(f"{name:<22} exact={o['item_exact']:.3f} within1={o['within_1']:.3f} mae%={o['mae_pct']} "
              f"qwk={o['qwk_band']:.3f} over={o['over_marked']:.3f}")
    if b:
        print("live:", {k: v for k, v in b.items() if k != "rows"})


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 60, sys.argv[2] if len(sys.argv) > 2 else "test")
