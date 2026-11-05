"""Embedding models (2.1) and chunking methods (2.2) for R3, per subject (Experiment plan v3, Phase 2).

Each option changes ONE thing in the current R3 setup (bge-m3 + BM25 hybrid, 1,500-character section chunks,
4 chunks matched, 3 sections passed, 3,600 characters read) and is scored on the same 45 questions with the
same gold evidence as the settings study (rag_gold.json: textbook lines per reference statement), so the
retrieval metrics cost nothing and do not depend on how the text is cut:
  hit rate, evidence recall, precision (AP), MRR   mean [95% bootstrap CI], overall and per subject
  change from the current option                   paired bootstrap, "clear" = the interval leaves out 0
Chunking methods only change which sections are found: R3 still passes the same whole sections.

2.1 embedding  bge-m3* | multilingual-e5-large | multilingual-e5-base | paraphrase-multilingual-MiniLM-L12-v2
               each with the hybrid search (as live), dense only, and the questions typed in Jawi; plus model
               size, vector size, longest input and time to embed the notes
2.2 chunking   A section + size* (overlap: last short paragraph*, 0, 100, 200) | B fixed window 600 (overlap
               0, 100, 200) | C sub-section (###) | D table rows (3 per chunk) | E bilingual pair (600) | F semantic
               A subject gets its own method only if it is clearly better there on evidence recall and not
               clearly worse on hit rate; the mixed setup is then compared with the best single method.
Answers (faithfulness, factual correctness; rag_eval.py prompts and judge) for the 2 best options of each
study (about $0.02 each; identical texts come from the LLM cache).

Usage: .venv\\Scripts\\python eval\\rag_phase2.py [--no-llm]
  -> eval/results/embedding_models.json/.md, chunking_by_subject.json/.md,
     docs/figures/results/fig_4_13_embeddings.png, fig_4_14_chunking.png
"""
from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, replace
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "eval"))

import rag_settings as RS  # noqa: E402  (in-memory index, retrieval, gold evidence, scoring, answers)

from backend.app.llm_api import spent_usd  # noqa: E402

RES = ROOT / "eval" / "results"
SUBJECTS = {"fiqh": "Ibadah", "jawi": "Jawi", "tajwid": "Tajwid"}
GROUPS = {"all": "All", **SUBJECTS}
METRICS = [("hit_rate", "Hit rate"), ("evidence_recall", "Evidence recall"), ("precision", "Precision"), ("mrr", "MRR")]
REPS, SEED = 2000, 7
D = RS.DEFAULT

EMB_LABEL = {"bge-m3": "bge-m3", "e5-large": "multilingual-e5-large", "e5-base": "multilingual-e5-base",
             "minilm": "MiniLM-L12 (multilingual)"}
CHUNKERS = [
    ("A. Section + size", D),
    ("A. overlap 0", replace(D, overlap=0)),
    ("A. overlap 100", replace(D, overlap=100)),
    ("A. overlap 200", replace(D, overlap=200)),
    ("B. Window 600, overlap 0", replace(D, chunker="window", chunk=600, overlap=0)),
    ("B. Window 600, overlap 100", replace(D, chunker="window", chunk=600, overlap=100)),
    ("B. Window 600, overlap 200", replace(D, chunker="window", chunk=600, overlap=200)),
    ("C. Sub-section", replace(D, chunker="subsection")),
    ("D. Table rows", replace(D, chunker="table_rows")),
    ("E. Bilingual pair", replace(D, chunker="bilingual", chunk=600)),
    ("F. Semantic", replace(D, chunker="semantic")),
]


# ------------------------------------------------------------------ statistics
def boot(x: list[float]) -> list[float]:
    a = np.array(x, dtype=float)
    b = a[np.random.default_rng(SEED).integers(0, len(a), (REPS, len(a)))].mean(axis=1)
    return [round(float(a.mean()), 4), round(float(np.percentile(b, 2.5)), 4), round(float(np.percentile(b, 97.5)), 4)]


def clear(d: list | None) -> int:
    return 0 if not d else 1 if d[1] > 0 else -1 if d[2] < 0 else 0


def ids_of(group: str, qs: list) -> list[str]:
    return [q.key for q in qs if group == "all" or q.subject == group]


def summarise(per: dict, cur: dict | None, qs: list) -> dict:
    """Mean [CI] per metric and group, and the paired change from the current option."""
    out = {}
    for g in GROUPS:
        ids = [k for k in ids_of(g, qs) if k in per]
        row = {m: boot([per[k][m] for k in ids]) for m, _ in METRICS}
        if cur is not None:
            row["diff"] = {m: boot([per[k][m] - cur[k][m] for k in ids]) for m, _ in METRICS}
        row["n"] = len(ids)
        out[g] = row
    return out


# ------------------------------------------------------------------ one option
def evaluate(cfg: RS.Cfg, qs: list, gold: dict) -> dict:
    per, unjudged, read = {}, 0, 0
    runs = {q.key: RS.retrieve(q, cfg) for q in qs}
    for q in qs:
        s = RS.score(runs[q.key], gold[q.key])
        if s is None:
            continue
        per[q.key] = s
        pool = set(gold[q.key]["pool"])
        read += len(runs[q.key]["given"])
        unjudged += sum(f"{p['topic']}::{p['section']}" not in pool for p in runs[q.key]["given"])
    ix = RS.index(cfg)
    return {"config": asdict(cfg), "per_question": per, "runs": runs, "chunks": len(ix.ids),
            "chunk_chars_mean": int(np.mean([len(t) for t in ix.texts])),
            "unjudged_share": round(unjudged / read, 4) if read else 0.0}


def answers(opts: list[dict], qs: list, workers: int = 6) -> None:
    """Faithfulness and factual correctness for the chosen options (adds 'answers' to each)."""
    jobs = {}
    for o in opts:
        for q in qs:
            r = o["runs"][q.key]
            jobs.setdefault((q.key, r["context"]), (q, r))
    print(f"   answering {len(jobs)} different (question, text) pairs ...", flush=True)
    with ThreadPoolExecutor(max_workers=workers) as ex:
        got = dict(zip(jobs, ex.map(lambda j: RS.answer(*j), jobs.values())))
    for o in opts:
        o["answer_items"] = {q.key: {k: got[(q.key, o["runs"][q.key]["context"])][k]
                                     for k in ("declined", "faithfulness", "factual_correctness")} for q in qs}


def answer_summary(o: dict, cur: dict, qs: list) -> dict:
    out = {}
    for g in GROUPS:
        ids = ids_of(g, qs)
        a, c = o["answer_items"], cur["answer_items"]
        fc = [a[k]["factual_correctness"] for k in ids]
        fa = [(a[k]["faithfulness"], c[k]["faithfulness"]) for k in ids
              if a[k]["faithfulness"] is not None and c[k]["faithfulness"] is not None]
        out[g] = {"factual_correctness": boot(fc), "faithfulness": boot([x for x, _ in fa]) if fa else None,
                  "declined": sum(a[k]["declined"] for k in ids),
                  "diff_factual_correctness": boot([a[k]["factual_correctness"] - c[k]["factual_correctness"] for k in ids]),
                  "diff_faithfulness": boot([x - y for x, y in fa]) if fa else None}
    return out


def select(opts: list[dict], group: str) -> dict:
    """The current option unless another is clearly better on evidence recall and not clearly worse on hit rate."""
    cur = next(o for o in opts if o["current"])
    better = [o for o in opts if not o["current"] and clear(o["groups"][group]["diff"]["evidence_recall"]) > 0
              and clear(o["groups"][group]["diff"]["hit_rate"]) >= 0]
    return max(better, key=lambda o: o["groups"][group]["evidence_recall"][0]) if better else cur


def best_two(opts: list[dict], key: str = "evidence_recall") -> list[dict]:
    """The 2 best non-current options overall or in any subject (for the answer run)."""
    picked = []
    for g in GROUPS:
        ranked = sorted((o for o in opts if not o["current"]), key=lambda o: -o["groups"][g][key][0])
        for o in ranked[:2]:
            if o not in picked:
                picked.append(o)
    return picked


# ------------------------------------------------------------------ studies
def model_info(name: str) -> dict:
    """Size, and seconds to embed all the notes' chunks (model loaded and warmed up first, same GPU and batch)."""
    import time
    m = RS.encoder(name)
    texts = RS.index(D).texts
    RS.encode(name, texts[:8], query=False)
    t0 = time.perf_counter()
    RS.encode(name, texts, query=False)
    return {"hf_id": RS.EMBEDDINGS[name][0], "parameters_m": round(sum(p.numel() for p in m.parameters()) / 1e6),
            "dimensions": m.get_sentence_embedding_dimension(), "max_tokens": m.max_seq_length,
            "embed_seconds": round(time.perf_counter() - t0, 1)}


def embedding_study(qs: list, gold: dict, use_llm: bool) -> dict:
    opts = []
    for name in RS.EMBEDDINGS:
        print(f"   embedding model {name}", flush=True)
        base = replace(D, embedding=name)
        o = evaluate(base, qs, gold) | {"option": EMB_LABEL[name], "key": name, "current": name == "bge-m3",
                                        "model": model_info(name)}
        o["dense"] = evaluate(replace(base, matching="dense"), qs, gold)
        o["jawi"] = evaluate(replace(base, jawi=True), qs, gold)
        opts.append(o)
        if RS._encoders.pop(name, None) is not None:     # free the GPU for the next model
            import torch
            torch.cuda.empty_cache()
    cur = next(o for o in opts if o["current"])
    for o in opts:
        o["groups"] = summarise(o["per_question"], None if o["current"] else cur["per_question"], qs)
        for v in ("dense", "jawi"):
            o[v]["groups"] = summarise(o[v]["per_question"], cur[v]["per_question"] if not o["current"] else None, qs)
    if use_llm:
        two = best_two(opts)[:2]
        answers([cur] + two, qs)
        for o in two:
            o["answers"] = answer_summary(o, cur, qs)
        cur["answers"] = answer_summary(cur, cur, qs)
    return {"options": opts, "selected": {g: select(opts, g)["option"] for g in GROUPS}}


def chunking_study(qs: list, gold: dict, use_llm: bool) -> dict:
    opts = []
    for label, cfg in CHUNKERS:
        print(f"   chunking {label}", flush=True)
        opts.append(evaluate(cfg, qs, gold) | {"option": label, "current": cfg == D})
    cur = next(o for o in opts if o["current"])
    for o in opts:
        o["groups"] = summarise(o["per_question"], None if o["current"] else cur["per_question"], qs)
    selected = {g: select(opts, g) for g in GROUPS}

    # the mixed setup: each subject with its own selected method, against the best single method
    single = max(opts, key=lambda o: o["groups"]["all"]["evidence_recall"][0])
    mixed_per = {k: selected[q.subject]["per_question"][k] for q in qs if (k := q.key) in cur["per_question"]}
    mixed = {"methods": {g: selected[g]["option"] for g in SUBJECTS},
             "groups": summarise(mixed_per, single["per_question"], qs), "vs": single["option"]}
    if use_llm:
        picked = best_two(opts)
        answers([cur] + picked, qs)
        for o in [cur] + picked:
            o["answers"] = answer_summary(o, cur, qs)
    return {"options": opts, "selected": {g: o["option"] for g, o in selected.items()}, "mixed": mixed,
            "best_single": single["option"]}


# ------------------------------------------------------------------ report
def cell(v: list | None) -> str:
    return "–" if not v else f"{v[0]:.3f} [{v[1]:.2f}, {v[2]:.2f}]"


def change(d: list | None) -> str:
    if not d:
        return "–"
    s = f"{d[0]:+.3f} [{d[1]:+.2f}, {d[2]:+.2f}]"
    return f"**{s}**" if clear(d) else s


def per_subject_table(opts: list[dict], metric: str, src=lambda o: o) -> list[str]:
    md = ["| Option | " + " | ".join(f"{GROUPS[g]} (n={src(opts[0])['groups'][g]['n']})" for g in GROUPS) + " |",
          "|---|" + "---|" * len(GROUPS)]
    for o in opts:
        gr = src(o)["groups"]
        md.append(f"| {o['option']}{' (current)' if o['current'] else ''} | " + " | ".join(
            f"{gr[g][metric][0]:.3f}" + ("" if o["current"] else f" ({change(gr[g]['diff'][metric])})") for g in GROUPS) + " |")
    return md


def answers_table(opts: list[dict]) -> list[str]:
    rows = [o for o in opts if o.get("answers")]
    if not rows:
        return ["(answers not run: use without --no-llm)"]
    md = ["| Option | Group | Factual correctness | Change | Faithfulness | Change | Declined |", "|---|---|---|---|---|---|---|"]
    for o in rows:
        for g in GROUPS:
            a = o["answers"][g]
            md.append(f"| {o['option']} | {GROUPS[g]} | {cell(a['factual_correctness'])} | "
                      f"{'–' if o['current'] else change(a['diff_factual_correctness'])} | {cell(a['faithfulness'])} | "
                      f"{'–' if o['current'] else change(a['diff_faithfulness'])} | {a['declined']} |")
    return md


def emb_markdown(r: dict) -> str:
    opts = r["options"]
    md = ["# Embedding models for R3 (Phase 2.1)", "",
          "Same 45 questions, gold evidence and R3 setup; only the embedding model changes. Mean [95% bootstrap CI]; "
          "in brackets the change from bge-m3 (**bold** = clear: the interval leaves out 0).", "",
          "## The models", "", "| Model | Parameters | Vector size | Longest input (tokens) | Time to embed the notes (RTX 3050 laptop, fp16) | Chunks |",
          "|---|---|---|---|---|---|"]
    for o in opts:
        m = o["model"]
        md.append(f"| {o['option']} | {m['parameters_m']} M | {m['dimensions']} | {m['max_tokens']:,} | "
                  f"{m['embed_seconds']:.0f} s | {o['chunks']} |")
    md += ["", "## Hybrid search (as live), all metrics", "", "| Model | " + " | ".join(l for _, l in METRICS) + " |",
           "|---|" + "---|" * len(METRICS)]
    for o in opts:
        md.append(f"| {o['option']}{' (current)' if o['current'] else ''} | "
                  + " | ".join(cell(o["groups"]["all"][m]) for m, _ in METRICS) + " |")
    for title, src in (("Hybrid search (as live)", lambda o: o), ("Dense only (the embedding alone)", lambda o: o["dense"]),
                       ("Questions typed in Jawi (hybrid)", lambda o: o["jawi"])):
        md += ["", f"## {title}: evidence recall per subject", ""] + per_subject_table(opts, "evidence_recall", src)
    md += ["", "## Answers (the best two and the current model)", ""] + answers_table(opts)
    md += ["", "## Selection", "", "| Group | Selected |", "|---|---|"]
    md += [f"| {GROUPS[g]} | {s} |" for g, s in r["selected"].items()]
    return "\n".join(md) + "\n"


def chunk_markdown(r: dict) -> str:
    opts = r["options"]
    md = ["# Chunking methods per subject for R3 (Phase 2.2)", "",
          "Same 45 questions (15 per subject), gold evidence and R3 setup; only the way the notes are cut into chunks "
          "changes (R3 still passes the whole matched sections). Mean; in brackets the change from the current method "
          "A with 95% CI (**bold** = clear).", "",
          "| Method | Chunks | Mean chunk size (characters) | Passages outside the judged pool |", "|---|---|---|---|"]
    md += [f"| {o['option']}{' (current)' if o['current'] else ''} | {o['chunks']} | {o['chunk_chars_mean']} | "
           f"{o['unjudged_share']:.1%} |" for o in opts]
    for m, label in METRICS:
        md += ["", f"## {label} per subject", ""] + per_subject_table(opts, m)
    md += ["", "## Answers (the 2 best methods per subject and the current one)", ""] + answers_table(opts)
    mx = r["mixed"]
    md += ["", "## Selection per subject", "", "| Group | Selected method |", "|---|---|"]
    md += [f"| {GROUPS[g]} | {s} |" for g, s in r["selected"].items()]
    md += ["", f"Mixed setup ({', '.join(f'{SUBJECTS[g]}: {m}' for g, m in mx['methods'].items())}) vs the best single "
               f"method ({mx['vs']}), evidence recall: " + "; ".join(
               f"{GROUPS[g]} {mx['groups'][g]['evidence_recall'][0]:.3f} ({change(mx['groups'][g]['diff']['evidence_recall'])})"
               for g in GROUPS) + "."]
    return "\n".join(md) + "\n"


def figures(emb: dict, chunk: dict) -> None:
    import make_figures as MF     # the thesis figure style and palette
    plt = MF.plt
    MF.OUT.mkdir(parents=True, exist_ok=True)

    def grouped(ax, opts, src, title):
        w = 0.8 / len(opts)
        for i, o in enumerate(opts):
            gr = src(o)["groups"]
            vals = [gr[g]["evidence_recall"] for g in GROUPS]
            x = np.arange(len(GROUPS)) + (i - (len(opts) - 1) / 2) * w
            ax.bar(x, [v[0] for v in vals], w * 0.9, color=MF.C[i % len(MF.C)], label=o["option"], zorder=2,
                   edgecolor="white", linewidth=1)
            ax.errorbar(x, [v[0] for v in vals], yerr=[[v[0] - v[1] for v in vals], [v[2] - v[0] for v in vals]],
                        fmt="none", ecolor=MF.INK2, elinewidth=0.8, capsize=2, zorder=3)
        ax.set_xticks(range(len(GROUPS)), GROUPS.values())
        ax.set_ylim(0, 1.05)
        ax.set_title(title)

    fig, axes = plt.subplots(1, 3, figsize=(13, 4), sharey=True)
    for ax, (t, src) in zip(axes, (("Hybrid (as live)", lambda o: o), ("Dense only", lambda o: o["dense"]),
                                   ("Questions typed in Jawi", lambda o: o["jawi"]))):
        grouped(ax, emb["options"], src, t)
    axes[0].set_ylabel("Evidence recall (95% CI)")
    axes[0].legend(loc="lower left", fontsize=8)
    fig.suptitle("Embedding models in R3: evidence recall per subject", fontweight="bold")
    MF.save(fig, "fig_4_13_embeddings.png")

    opts = chunk["options"]
    mat = np.array([[o["groups"][g]["evidence_recall"][0] for g in GROUPS] for o in opts])
    fig, ax = plt.subplots(figsize=(7, 0.42 * len(opts) + 1.2))
    ax.imshow(mat, cmap="Blues", vmin=max(0.0, mat.min() - 0.1), vmax=1.0, aspect="auto")
    ax.grid(False)
    ax.set_xticks(range(len(GROUPS)), GROUPS.values())
    ax.set_yticks(range(len(opts)), [o["option"] + (" (current)" if o["current"] else "") for o in opts])
    for i, o in enumerate(opts):
        for j, g in enumerate(GROUPS):
            d = None if o["current"] else o["groups"][g]["diff"]["evidence_recall"]
            mark = "" if not d or not clear(d) else (" ▲" if d[0] > 0 else " ▼")
            ax.text(j, i, f"{mat[i, j]:.2f}{mark}", ha="center", va="center", fontsize=9,
                    color="white" if mat[i, j] > 0.8 else MF.INK)
    ax.set_title("Chunking methods: evidence recall per subject (▲▼ = clear change from A)")
    MF.save(fig, "fig_4_14_chunking.png")


def strip(r: dict) -> dict:
    """Drop the retrieval runs (passage texts) from the saved JSON; keep per-question metrics."""
    for o in r["options"]:
        o.pop("runs", None)
        for v in ("dense", "jawi"):
            if v in o:
                o[v].pop("runs", None)
    return r


def main(use_llm: bool) -> None:
    spent0 = spent_usd()
    qs, _ = RS.questions(use_llm=False)          # the frozen 45 questions (saved rewrites are not used here)
    gold = json.loads(RS.GOLD.read_text(encoding="utf-8"))
    qs = [q for q in qs if q.key in gold]
    check = evaluate(D, qs, gold)
    saved = json.loads((RES / "rag_settings.json").read_text(encoding="utf-8"))
    cur = next(o for s in saved["settings"] if s["key"] == "chunk" for o in s["options"] if o["current"])
    same = all(abs(check["per_question"][k]["evidence_recall"] - v["evidence_recall"]) < 1e-9
               for k, v in cur["per_question"].items())
    print(f"check: the current setting reproduces the settings study: {same}", flush=True)
    if not same:
        raise SystemExit("the current setting no longer matches rag_settings.json")

    chunk = chunking_study(qs, gold, use_llm)
    emb = embedding_study(qs, gold, use_llm)
    for name, r, md in (("embedding_models", emb, emb_markdown), ("chunking_by_subject", chunk, chunk_markdown)):
        (RES / f"{name}.md").write_text(md(r), encoding="utf-8")
        (RES / f"{name}.json").write_text(json.dumps(strip(r) | {"spent": round(spent_usd() - spent0, 4)},
                                                     indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    figures(emb, chunk)
    print(chunk_markdown(chunk).split("\n## Precision")[0])
    print(emb_markdown(emb))
    print(f"-> {RES / 'embedding_models.md'}, {RES / 'chunking_by_subject.md'}  (this run ${spent_usd() - spent0:.4f})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-llm", action="store_true", help="retrieval metrics only (no answers)")
    main(not ap.parse_args().no_llm)
