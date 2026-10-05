"""Phase 3 retrieval evaluation.

For each question in a split, query the note index WITHOUT the topic filter
and check whether a chunk from the question's own topic is retrieved.
(At run time the pipeline knows the topic and filters on it; this measures
how well retrieval finds relevant material on its own.)

Metrics (topic-level): Recall@1, Recall@4, MRR@10.
Retrievers: dense (bge-m3), keyword (BM25), hybrid (RRF fusion).
Query variants:
  rumi_subject  - Rumi question, filtered to its subject   (main setting)
  jawi_subject  - Jawi question, filtered to its subject
  rumi_all      - Rumi question, no filter

Usage (from FypNabil/):
  .venv\\Scripts\\python eval\\retrieval_eval.py            # train split
  .venv\\Scripts\\python eval\\retrieval_eval.py test       # final report only
Writes eval/results/retrieval_<split>.json and .md
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.app.embeddings import embed  # noqa: E402
from backend.app.kb.retriever import dense_search, hybrid_search, keyword_search  # noqa: E402
from backend.app.questions import load_questions, load_split  # noqa: E402

K = 10
VARIANTS = {
    "rumi_subject": ("question_rumi", True),
    "jawi_subject": ("question_jawi", True),
    "rumi_all": ("question_rumi", False),
}
RETRIEVERS = {
    "dense": lambda q, vec, subj: dense_search(vec, K, subj),
    "keyword": lambda q, vec, subj: keyword_search(q, K, subj),
    "hybrid": lambda q, vec, subj: hybrid_search(q, K, subj, vec=vec),
}


def rank_of_topic(hits, topic_id: str) -> int | None:
    for i, h in enumerate(hits, start=1):
        if h.topic_id == topic_id:
            return i
    return None


def summarise(ranks: list[int | None]) -> dict:
    n = len(ranks)
    return {
        "n": n,
        "recall@1": round(sum(r is not None and r <= 1 for r in ranks) / n, 3),
        "recall@4": round(sum(r is not None and r <= 4 for r in ranks) / n, 3),
        "mrr@10": round(sum(1 / r for r in ranks if r) / n, 3),
    }


def main(split: str) -> None:
    qs = load_questions()
    ids = [i for i in load_split(split) if i in qs]
    results: dict = {"split": split, "k": K, "runs": {}}
    misses: dict[str, list] = defaultdict(list)

    for vname, (field, use_subject) in VARIANTS.items():
        items = [qs[i] for i in ids if (qs[i].get(field) or "").strip()]
        vecs = embed([q[field] for q in items])
        for rname, fn in RETRIEVERS.items():
            ranks_all, by_subject = [], defaultdict(list)
            for q, vec in zip(items, vecs):
                hits = fn(q[field], vec, q["subject"] if use_subject else None)
                r = rank_of_topic(hits, q["topic_id"])
                ranks_all.append(r)
                by_subject[q["subject"]].append(r)
                if vname == "rumi_subject" and rname == "hybrid" and (r is None or r > 4):
                    misses[q["subject"]].append({"id": q["id"], "rank": r, "q": q[field][:90],
                                                 "got": hits[0].topic_id if hits else None})
            key = f"{vname}/{rname}"
            results["runs"][key] = {"overall": summarise(ranks_all),
                                    "by_subject": {s: summarise(v) for s, v in sorted(by_subject.items())}}
            o = results["runs"][key]["overall"]
            print(f"{key:<22} n={o['n']:<4} R@1={o['recall@1']:.3f}  R@4={o['recall@4']:.3f}  MRR={o['mrr@10']:.3f}")

    results["misses_rumi_subject_hybrid"] = misses
    out = ROOT / "eval" / "results"
    out.mkdir(parents=True, exist_ok=True)
    (out / f"retrieval_{split}.json").write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [f"# Retrieval evaluation ({split} split)", "",
             "Topic-level: does a chunk from the question's own topic appear in the top-k? "
             "No topic filter is applied (the live pipeline does filter by topic).", "",
             "| Query | Retriever | Subject | n | Recall@1 | Recall@4 | MRR@10 |",
             "|---|---|---|---|---|---|---|"]
    for key, v in results["runs"].items():
        vname, rname = key.split("/")
        for s, m in [("all", v["overall"]), *v["by_subject"].items()]:
            lines.append(f"| {vname} | {rname} | {s} | {m['n']} | {m['recall@1']:.3f} | "
                         f"{m['recall@4']:.3f} | {m['mrr@10']:.3f} |")
    n_miss = sum(len(v) for v in misses.values())
    lines += ["", f"Misses at k=4 (rumi_subject, hybrid): {n_miss}", ""]
    for s, ms in misses.items():
        for m in ms[:15]:
            lines.append(f"- `{m['id']}` rank={m['rank']} top1=`{m['got']}`: {m['q']}")
    (out / f"retrieval_{split}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"saved eval/results/retrieval_{split}.json/.md")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "train")
