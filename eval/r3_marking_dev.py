"""Do the RAG settings study's R3 choices help MARKING? A check on the silver development answers
(Experiment plan v3, Phase 6).

The settings study (rag_settings.py) measured how well a model ANSWERS questions from the R3 text. Marking was not
measured. The teacher set is the final test, so the R3 setting for marking is chosen here, on silver answers that are
not part of the test. Decision rule (fixed before the run): marking keeps the earlier R3 unless a study setting scores
at least as high on these silver answers.

GPT-6 Luna, proposed system (R3, A2, memory off), on the silver test answers whose marking depends on the text read
(paraphrases, misconceptions, partial answers, number swaps), with four R3 settings:
  earlier   4 chunks, 3 sections, no minimum      (the original R3)
  study     6 chunks, 5 sections, minimum 0.35    (the settings study's choices)
  sections  6 chunks, 5 sections, no minimum
  minimum   4 chunks, 3 sections, minimum 0.35
QWK of the score bands against the silver labels, criterion accuracy, and the paired bootstrap difference from the
earlier setting (2,000 resamples of the answers, seed 7). Cost about $0.20 (the earlier setting is partly cached).

Usage: .venv\\Scripts\\python eval\\r3_marking_dev.py   -> eval/results/r3_marking_dev.json and .md
"""
from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "eval"))

import experiments as E  # noqa: E402
from scoring_lib import band, qwk  # noqa: E402

from backend.app.assess.decision import award  # noqa: E402
from backend.app.assess.llm_marking import MarkConfig  # noqa: E402
from backend.app.kb import rag  # noqa: E402
from backend.app.llm_api import spent_usd  # noqa: E402
from backend.app.questions import load_questions  # noqa: E402

KINDS = ("paraphrase_full", "misconception", "partial", "number_swap")
STUDY_RUNS = ROOT / "eval" / "results" / "archive" / "r3_study_settings_2nov"   # the teacher-set runs with the study's R3
TEACHER_RUNS = ("step2__proposed_luna_R3_A2_off__teacherall.json", "step4__proposed_luna_R3_A2_on__teacherallx3.json",
                "step3__proposed_luna_R3_A1_off__teacherall.json", "step3__proposed_luna_R3_A3_off__teacherall.json",
                "check__proposed_haiku_R3_A2_off__teacherall.json")
FINAL_DECISION = ("Because the silver answers could not separate the settings and the teacher set showed a significant "
                  "drop for the final system, the researcher decided on 2 Nov 2026 that marking keeps the earlier R3. "
                  "The study's choices stay where they were measured: Tanya Bulan's lower gate with the decline rule.")
SETTINGS = {"earlier": (4, 3, 0.0), "study": (6, 5, 0.35), "sections": (6, 5, 0.0), "minimum": (4, 3, 0.35)}
CFG = MarkConfig("proposed", "luna", "R3", "A2", False)
OUT = ROOT / "eval" / "results" / "r3_marking_dev.json"
REPS, SEED = 2000, 7


def mark_all(items: list[dict], qs: dict, setting: tuple[int, int, float]) -> list[dict]:
    rag.R3_CHUNKS, rag.R3_SECTIONS, rag.R3_MIN_SIM = setting   # read by kb.rag at every retrieval
    with ThreadPoolExecutor(max_workers=4) as ex:
        outs = list(ex.map(lambda it: E._one(it, qs[it["question_id"]], CFG, None), items))
    return outs


def bands(items: list[dict], outs: list[dict], qs: dict) -> tuple[list[int], list[int]]:
    gold, pred = [], []
    for it, o in zip(items, outs):
        q = qs[it["question_id"]]
        g = sum(award(float(r["marks"]), c["met"]) for r, c in zip(q["rubric"], it["criteria"]))
        gold.append(band(g, float(q["max_marks"])))
        pred.append(band(float(o["score"]), float(q["max_marks"])))
    return gold, pred


def teacher_comparison() -> list[dict]:
    """Paired bootstrap on the 50 teacher answers: earlier R3 (eval/results/experiments) vs the study's R3 (archived)."""
    import final_stats as FS
    from teacher_compare import _meta, _scored, label_sets

    qs, meta, sets = load_questions(), _meta(), label_sets()
    order = sorted(sets["final"])
    idx = FS._boot_idx(len(order))

    def boot(path: Path):
        r = json.loads(path.read_text(encoding="utf-8"))
        preds = {x["answer_id"]: [c["met"] for c in x["criteria"]] for x in r["items"] if x["rep"] == 0}
        items = {i["answer_id"]: i for i in _scored(preds, sets["final"], qs, meta)}
        gold, pred = FS._bands([items[a] for a in order])
        return r["config"], qwk(gold, pred), np.array([FS._qwk_of(i, gold, pred) for i in idx])

    rows = []
    for name in TEACHER_RUNS:
        if not (STUDY_RUNS / name).exists():
            continue
        cfg, q0, b0 = boot(ROOT / "eval" / "results" / "experiments" / name)
        _, q1, b1 = boot(STUDY_RUNS / name)
        d = b1 - b0
        rows.append({"config": cfg, "earlier": round(q0, 3), "study": round(q1, 3), "diff": round(q1 - q0, 3),
                     "ci": [round(float(np.percentile(d, q)), 3) for q in (2.5, 97.5)],
                     "significant": bool(np.percentile(d, 97.5) < 0 or np.percentile(d, 2.5) > 0)})
    return rows


def main() -> None:
    qs = load_questions()
    items = [it for it in E.load_items("silver", None, "final") if it.get("kind") in KINDS and it["question_id"] in qs]
    idx = np.random.default_rng(SEED).integers(0, len(items), size=(REPS, len(items)))
    before = spent_usd()
    res = {"date": datetime.now(timezone.utc).isoformat(timespec="seconds"), "answers": len(items),
           "kinds": {k: sum(it["kind"] == k for it in items) for k in KINDS}, "settings": {}}
    boot = {}
    for name, setting in SETTINGS.items():
        t0 = spent_usd()
        outs = mark_all(items, qs, setting)
        gold, pred = bands(items, outs, qs)
        g, p = np.array(gold), np.array(pred)
        boot[name] = np.array([qwk(list(g[i]), list(p[i])) for i in idx])
        crit = [(c["met"], o_c["met"]) for it, o in zip(items, outs) for c, o_c in zip(it["criteria"], o["criteria"])]
        res["settings"][name] = {
            "chunks": setting[0], "sections": setting[1], "min_sim": setting[2],
            "qwk": round(qwk(gold, pred), 3), "ci": [round(float(np.percentile(boot[name], q)), 3) for q in (2.5, 97.5)],
            "criterion_accuracy": round(sum(a == b for a, b in crit) / len(crit), 3),
            "valid": round(sum(o["ok"] for o in outs) / len(outs), 3), "cost": round(spent_usd() - t0, 4)}
        print(f"{name:9} QWK {res['settings'][name]['qwk']}  criteria {res['settings'][name]['criterion_accuracy']}  "
              f"${res['settings'][name]['cost']:.4f}", flush=True)
    rag.R3_CHUNKS, rag.R3_SECTIONS, rag.R3_MIN_SIM = SETTINGS["study"]   # back to the module's values
    for name in SETTINGS:
        if name != "earlier":
            d = boot[name] - boot["earlier"]
            res["settings"][name]["vs_earlier"] = {"diff": round(res["settings"][name]["qwk"] - res["settings"]["earlier"]["qwk"], 3),
                                                   "ci": [round(float(np.percentile(d, q)), 3) for q in (2.5, 97.5)],
                                                   "significant": bool(np.percentile(d, 97.5) < 0 or np.percentile(d, 2.5) > 0)}
    best_new = max((n for n in SETTINGS if n != "earlier"), key=lambda n: res["settings"][n]["qwk"])
    keep = res["settings"][best_new]["qwk"] >= res["settings"]["earlier"]["qwk"]
    res["decision"] = best_new if keep else "earlier"
    res["teacher"] = teacher_comparison()
    res["final_decision"] = "earlier"
    res["cost"] = round(spent_usd() - before, 4)
    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
    OUT.with_suffix(".md").write_text(markdown(res), encoding="utf-8")
    print(markdown(res))


def markdown(res: dict) -> str:
    md = ["# R3 settings for marking: check on the silver development answers", "",
          f"GPT-6 Luna, proposed system (R3, A2, memory off), {res['answers']} silver answers "
          f"({', '.join(f'{k} {n}' for k, n in res['kinds'].items())}). QWK of the score bands against the silver labels, "
          "95% bootstrap interval; the change is paired against the earlier setting (**bold** = significant).", "",
          "| R3 setting | Chunks | Sections | Minimum similarity | QWK [95% CI] | Change from earlier | Criterion accuracy | Valid |",
          "|---|---|---|---|---|---|---|---|"]
    for name, s in res["settings"].items():
        vs = s.get("vs_earlier")
        change = "–" if not vs else (f"**{vs['diff']:+.3f} [{vs['ci'][0]:+.2f}, {vs['ci'][1]:+.2f}]**" if vs["significant"]
                                     else f"{vs['diff']:+.3f} [{vs['ci'][0]:+.2f}, {vs['ci'][1]:+.2f}]")
        md.append(f"| {name} | {s['chunks']} | {s['sections']} | {s['min_sim'] or 'none'} | {s['qwk']:.3f} [{s['ci'][0]:.2f}, {s['ci'][1]:.2f}] "
                  f"| {change} | {s['criterion_accuracy']:.0%} | {s['valid']:.0%} |")
    md += ["", f"**Rule outcome** (fixed before the run: keep the earlier R3 for marking unless a study setting scores at "
               f"least as high): **{res['decision']}**, but only by a difference far inside the noise: the silver answers are "
               "too easy to separate the settings, and the minimum similarity removed nothing (the same marks as without it).", ""]
    if res.get("teacher"):
        md += ["## The same settings on the 50 teacher answers", "",
               "Runs on the final teacher marks with the earlier R3 and with the study's R3 (archived in "
               "`eval/results/archive/r3_study_settings_2nov/`); paired bootstrap, 2,000 resamples.", "",
               "| Configuration | Earlier R3 | Study's R3 | Change [95% CI] |", "|---|---|---|---|"]
        for t in res["teacher"]:
            ch = f"{t['diff']:+.3f} [{t['ci'][0]:+.3f}, {t['ci'][1]:+.3f}]"
            md.append(f"| {t['config']} | {t['earlier']:.3f} | {t['study']:.3f} | {'**' + ch + '**' if t['significant'] else ch} |")
        md += ["", f"**Final decision:** {FINAL_DECISION} Marking uses **{res['final_decision']}** "
                   f"({SETTINGS[res['final_decision']][0]} chunks, {SETTINGS[res['final_decision']][1]} sections, no minimum).", ""]
    # the first run on 2 Nov 2026 cost $0.063; every later run reads the same answers from the LLM cache
    md += ["API cost of the silver check: $0.063 (first run; the answers are cached, so a rerun is free).", ""]
    return "\n".join(md)


if __name__ == "__main__":
    main()
