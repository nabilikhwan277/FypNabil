"""RAG evaluation: compare the three RAG types of the blueprint (R1, R2, R3) with RAGAS-style metrics.

Each test question is asked like a pupil asking Tanya Bulan: the RAG type retrieves textbook text
(by question and subject only, not the topic), one FIXED model writes the answer from that text, and
a judge from ANOTHER provider scores it. Only the RAG type changes, so differences come from retrieval.

Questions: 45 from the question bank (15 Ibadah, 15 Jawi, 15 Tajwid, all levels) with their
textbook reference answers, plus 24 out-of-syllabus questions that the system should DECLINE:
12 general (cooking, sport, science...) and 12 near the syllabus (Islamic, Tajwid and Jawi topics that the
Year 5 notes do not teach, e.g. qalqalah, solat Jumaat, awalan ber-), which look like textbook questions.
Jawi spelling, Betul/Salah and reading-passage questions are left out (they are not standalone questions).

The judge sees exactly the text the answer model read: the passages that fit in the context limit
(CONTEXT_CHARS), not every passage the retriever returned.

Metrics (answerable questions; RAGAS definitions)
  context precision    passages given to the model that are relevant to the question, weighted by rank (average precision)
  context recall       statements of the reference answer that the given text contains
  faithfulness         claims in the answer supported by the given text (answered questions only)
  answer relevancy     mean cosine (bge-m3) between the question and 3 questions the judge infers from the answer
  factual correctness  F1 of claims: answer vs reference answer
  declined             answerable questions where the system said "Data ini tiada dalam pangkalan data saya"
Out-of-syllabus: correctly declined (of 24, general and near-syllabus). Also: passages read, retrieval time, cost.

Usage: .venv\\Scripts\\python eval\\rag_eval.py [--n 45] [--rag R1 R2 R3]
Results: eval/results/rag_eval.json and .md (shown on the 📊 Penilaian page, "RAG Evaluation" tab)
"""
from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.app.embeddings import embed  # noqa: E402
from backend.app.kb.rag import retrieve  # noqa: E402
from backend.app.llm_api import MODELS, complete, spent_usd  # noqa: E402
from backend.app.questions import load_questions  # noqa: E402

OUT = ROOT / "eval" / "results" / "rag_eval.json"
GENERATOR, JUDGE = "luna", "haiku"     # fixed answer writer; judge from another provider
SEED = 21
DECLINE = "Data ini tiada dalam pangkalan data saya."
SKIP_WORDS = ("tersebut", "petikan", "syair", "berdasarkan", "bergaris", "situasi", "latihan")

OUT_OF_SYLLABUS_GENERAL = [  # the system should decline these (not in the Year 5 KAFA textbooks)
    "Bagaimanakah cara membuat kek coklat?",
    "Siapakah Perdana Menteri pertama Malaysia?",
    "Apakah ibu negara Jepun?",
    "Berapakah jarak bumi ke bulan?",
    "Bagaimanakah cara bermain bola sepak?",
    "Apakah formula kimia air?",
    "Apakah planet yang paling besar dalam sistem suria?",
    "Berapakah hasil darab 7 dengan 8?",
    "Bagaimanakah cara menanam pokok cili?",
    "Apakah nama sungai yang paling panjang di Malaysia?",
    "Siapakah yang mencipta mentol lampu?",
    "Bagaimanakah cara membuat layang-layang?",
]
OUT_OF_SYLLABUS_NEAR = [  # Islamic / Tajwid / Jawi topics that the Year 5 notes do not teach (checked with grep)
    "Apakah rukun haji?",
    "Berapakah kadar zakat fitrah yang perlu dibayar?",
    "Bagaimanakah cara menunaikan solat jenazah?",
    "Apakah syarat wajib solat Jumaat?",
    "Apakah hukum Izhar Halqi?",
    "Apakah huruf-huruf qalqalah?",
    "Bilakah berlakunya hukum Ikhfa' Hakiki?",
    "Apakah hukum mim mati apabila bertemu dengan huruf ba?",
    "Bagaimanakah ejaan Jawi bagi awalan ber-?",
    "Bagaimanakah ejaan Jawi bagi kata majmuk?",
    "Siapakah isteri pertama Nabi Muhammad SAW?",
    "Siapakah malaikat yang menyampaikan wahyu kepada para nabi?",
]
OUT_OF_SYLLABUS = [(t, "general") for t in OUT_OF_SYLLABUS_GENERAL] + [(t, "near") for t in OUT_OF_SYLLABUS_NEAR]

ANSWER_RULES = f"""You are Bulan, a friendly study helper for Year 5 KAFA pupils in Malaysia.
Answer the pupil's question using ONLY the TEXTBOOK TEXT given. Reply in simple Bahasa Melayu (Rumi), 1-3 short sentences.
If the textbook text does not contain the answer, reply exactly: "{DECLINE}" and nothing else."""

CONTEXT_RULES = """You judge the textbook passages that a retrieval system found for one question.
A. Split the REFERENCE ANSWER into short statements and decide for each whether the PASSAGES contain that information ("attributed").
B. For each passage (by its number) decide whether it is relevant, i.e. useful for answering this question."""
CONTEXT_SCHEMA = {"type": "object", "properties": {
    "statements": {"type": "array", "items": {"type": "object", "properties": {
        "statement": {"type": "string"}, "attributed": {"type": "boolean"}},
        "required": ["statement", "attributed"], "additionalProperties": False}},
    "passages": {"type": "array", "items": {"type": "object", "properties": {
        "index": {"type": "integer"}, "relevant": {"type": "boolean"}},
        "required": ["index", "relevant"], "additionalProperties": False}}},
    "required": ["statements", "passages"], "additionalProperties": False}

FAITH_RULES = """Split the ANSWER into short factual claims and decide for each whether the TEXTBOOK TEXT supports it."""
FAITH_SCHEMA = {"type": "object", "properties": {"claims": {"type": "array", "items": {"type": "object", "properties": {
    "claim": {"type": "string"}, "supported": {"type": "boolean"}},
    "required": ["claim", "supported"], "additionalProperties": False}}},
    "required": ["claims"], "additionalProperties": False}

RELEVANCY_RULES = """Read the ANSWER and write 3 different questions (in Bahasa Melayu) that this answer would be a good answer to.
Write only what the answer itself supports."""
RELEVANCY_SCHEMA = {"type": "object", "properties": {"questions": {"type": "array", "items": {"type": "string"}}},
                    "required": ["questions"], "additionalProperties": False}

CORRECT_RULES = """Compare a system ANSWER with the REFERENCE ANSWER from the textbook.
1. Split the ANSWER into short factual claims; for each decide whether the REFERENCE supports it.
2. Split the REFERENCE into short factual claims; for each decide whether the ANSWER states it (same meaning is enough)."""
CORRECT_SCHEMA = {"type": "object", "properties": {
    "answer_claims": {"type": "array", "items": {"type": "object", "properties": {
        "claim": {"type": "string"}, "in_reference": {"type": "boolean"}},
        "required": ["claim", "in_reference"], "additionalProperties": False}},
    "reference_claims": {"type": "array", "items": {"type": "object", "properties": {
        "claim": {"type": "string"}, "in_answer": {"type": "boolean"}},
        "required": ["claim", "in_answer"], "additionalProperties": False}}},
    "required": ["answer_claims", "reference_claims"], "additionalProperties": False}


FROZEN = ROOT / "eval" / "rag_questions.json"   # the thesis question set, kept fixed when books are added


def pick_questions(n: int) -> list[dict]:
    """The frozen RAG test questions (eval/rag_questions.json), so adding a textbook or exercise book to the
    question bank does not change which questions are asked and old and new results stay comparable.
    Without that file: n new questions, equal per subject, spread over levels (fixed seed)."""
    if FROZEN.exists():
        qs = load_questions()
        ids = json.loads(FROZEN.read_text(encoding="utf-8"))["ids"]
        missing = [i for i in ids if i not in qs]
        if missing:   # their book was removed from the syllabus
            print(f"  note: {len(missing)} frozen questions are no longer in the syllabus and are skipped: {missing[:5]}")
        return [qs[i] for i in ids if i in qs][:n]
    return _pick_new(n)


def _pick_new(n: int) -> list[dict]:
    qs = load_questions()
    ok = []
    for q in qs.values():
        ref = (q.get("reference_answer_rumi") or "").strip()
        text = q["question_rumi"].lower()
        if ref.lower() in ("betul", "salah") or len(ref) < 3 or any(w in text for w in SKIP_WORDS):
            continue
        if q["subject"] == "jawi" and ("jawi" in text and ("tulis" in text or "jawikan" in text)):
            continue
        ok.append(q)
    rng = random.Random(SEED)
    per = n // 3
    out = []
    for subject in ("fiqh", "jawi", "tajwid"):
        by_level = defaultdict(list)
        for q in ok:
            if q["subject"] == subject:
                by_level[q["level"]].append(q)
        for v in by_level.values():
            rng.shuffle(v)
        chosen, levels = [], sorted(by_level)
        while len(chosen) < per and any(by_level[l] for l in levels):
            for l in levels:
                if by_level[l] and len(chosen) < per:
                    chosen.append(by_level[l].pop())
        out += chosen
    return out


def _cos(a, b) -> float:
    return float(sum(x * y for x, y in zip(a, b)))


def ask(question: str, ctx: str, tag: str):
    """The fixed answer model, answering from the given textbook text only."""
    return complete(GENERATOR, [{"role": "system", "content": ANSWER_RULES},
                                {"role": "user", "content": f"TEXTBOOK TEXT:\n<<<\n{ctx or '(none)'}\n>>>\n\nQUESTION: {question}"}],
                    max_tokens=400, tag=tag)


def is_declined(answer: str) -> bool:
    return "tiada dalam pangkalan data" in answer.lower()


def average_precision(flags: list[bool]) -> float:
    """RAGAS context precision: mean of precision@k over the ranks k that hold a relevant passage."""
    hits, ap = 0, 0.0
    for k, f in enumerate(flags, 1):
        if f:
            hits += 1
            ap += hits / k
    return ap / hits if hits else 0.0


def judge_context(question: str, reference: str, passages: list[str]) -> tuple[float | None, float, float]:
    """(context recall, context precision, cost) of the passages given to the model."""
    text = "\n\n".join(f"[{i}] {p}" for i, p in enumerate(passages, 1))
    c = complete(JUDGE, [{"role": "system", "content": CONTEXT_RULES},
                         {"role": "user", "content": f"QUESTION: {question}\n\nREFERENCE ANSWER:\n{reference}\n\nPASSAGES:\n{text or '(none)'}"}],
                 schema=CONTEXT_SCHEMA, max_tokens=1500, tag="rag_eval:judge:context")
    d = c.data or {}
    st = d.get("statements") or []
    recall = sum(bool(s.get("attributed")) for s in st) / len(st) if st else None
    rel = {int(p.get("index", 0)): bool(p.get("relevant")) for p in d.get("passages") or []}
    return recall, average_precision([rel.get(i, False) for i in range(1, len(passages) + 1)]), c.cost


def judge_faithfulness(ctx: str, answer: str) -> tuple[float | None, list[str], float]:
    """(share of the answer's claims supported by the text the model read, unsupported claims, cost)."""
    f = complete(JUDGE, [{"role": "system", "content": FAITH_RULES},
                         {"role": "user", "content": f"TEXTBOOK TEXT:\n<<<\n{ctx}\n>>>\n\nANSWER:\n{answer}"}],
                 schema=FAITH_SCHEMA, max_tokens=1200, tag="rag_eval:judge:faithfulness")
    claims = (f.data or {}).get("claims") or []
    share = sum(bool(x.get("supported")) for x in claims) / len(claims) if claims else None
    return share, [x.get("claim", "") for x in claims if not x.get("supported")], f.cost


def judge_relevancy(question: str, answer: str) -> tuple[float | None, float]:
    """RAGAS answer relevancy: questions generated from the answer vs the real question (bge-m3 cosine)."""
    g = complete(JUDGE, [{"role": "system", "content": RELEVANCY_RULES}, {"role": "user", "content": f"ANSWER:\n{answer}"}],
                 schema=RELEVANCY_SCHEMA, max_tokens=600, tag="rag_eval:judge:relevancy")
    gen = [x for x in ((g.data or {}).get("questions") or []) if x.strip()][:3]
    if not gen:
        return None, g.cost
    vecs = embed([question, *gen])
    return round(statistics.mean(_cos(vecs[0], v) for v in vecs[1:]), 4), g.cost


def judge_correctness(question: str, reference: str, answer: str) -> tuple[float, float]:
    """Factual correctness: claim F1 of the answer against the reference answer."""
    k = complete(JUDGE, [{"role": "system", "content": CORRECT_RULES},
                         {"role": "user", "content": f"QUESTION: {question}\n\nREFERENCE ANSWER:\n{reference}\n\nANSWER:\n{answer}"}],
                 schema=CORRECT_SCHEMA, max_tokens=1500, tag="rag_eval:judge:correctness")
    kd = k.data or {}
    ac, rc = kd.get("answer_claims") or [], kd.get("reference_claims") or []
    prec = sum(bool(x.get("in_reference")) for x in ac) / len(ac) if ac else 0.0
    rec = sum(bool(x.get("in_answer")) for x in rc) / len(rc) if rc else 0.0
    return (round(2 * prec * rec / (prec + rec), 4) if prec + rec else 0.0), k.cost


def answer_one(q: dict | None, question: str, subject: str | None, rag: str, kind: str = "") -> dict:
    t0 = time.perf_counter()
    got = retrieve(question, rag=rag, subject=subject)
    retrieval_ms = int((time.perf_counter() - t0) * 1000)
    c = ask(question, got.context, f"rag_eval:{rag}:answer")
    ans = c.text.strip()
    given = got.chunks()          # only the passages the model read
    return {"question_id": q["id"] if q else None, "subject": subject or "", "level": q["level"] if q else None,
            "kind": kind, "question": question, "reference": (q or {}).get("reference_answer_rumi", ""), "answer": ans,
            "declined": is_declined(ans), "retrieval_ms": retrieval_ms, "retrieved": len(got.hits),
            "passages_given": len(given), "context_chars": len(got.context), "context": given, "cost": c.cost}


def judge_one(r: dict) -> dict:
    passages = [c["text"] for c in r["context"]]
    ctx = "\n\n".join(passages)          # = the context the model read
    r["context_recall"], r["context_precision"], cost = judge_context(r["question"], r["reference"], passages)
    if r["declined"]:
        r.update(faithfulness=None, answer_relevancy=0.0, factual_correctness=0.0)
        r["cost"] += cost
        return r
    r["faithfulness"], r["unsupported"], c1 = judge_faithfulness(ctx, r["answer"])
    r["answer_relevancy"], c2 = judge_relevancy(r["question"], r["answer"])
    r["factual_correctness"], c3 = judge_correctness(r["question"], r["reference"], r["answer"])
    r["cost"] += cost + c1 + c2 + c3
    return r


def _mean(xs) -> float | None:
    xs = [x for x in xs if x is not None]
    return round(statistics.mean(xs), 3) if xs else None


def evaluate(rag: str, questions: list[dict], workers: int = 4) -> dict:
    print(f"== {rag}: answering {len(questions)} + {len(OUT_OF_SYLLABUS)} questions (spent so far ${spent_usd():.4f})", flush=True)
    t0 = time.perf_counter()
    answers = [answer_one(q, q["question_rumi"], q["subject"], rag) for q in questions]   # retrieval is serialised anyway
    oos = [answer_one(None, text, None, rag, kind) for text, kind in OUT_OF_SYLLABUS]
    with ThreadPoolExecutor(max_workers=workers) as ex:
        judged = list(ex.map(judge_one, answers))
    s = {
        "context_precision": _mean(r["context_precision"] for r in judged),
        "context_recall": _mean(r["context_recall"] for r in judged),
        "faithfulness": _mean(r["faithfulness"] for r in judged),
        "answer_relevancy": _mean(r["answer_relevancy"] for r in judged),
        "factual_correctness": _mean(r["factual_correctness"] for r in judged),
        "declined": sum(r["declined"] for r in judged),
        "answerable": len(judged),
        "out_of_syllabus_declined": sum(r["declined"] for r in oos),
        "out_of_syllabus": len(oos),
        "out_of_syllabus_by_kind": {k: {"declined": sum(r["declined"] for r in oos if r["kind"] == k),
                                        "n": sum(r["kind"] == k for r in oos)} for k in ("general", "near")},
        "retrieved_mean": round(statistics.mean(r["retrieved"] for r in judged), 2),
        "passages_given_mean": round(statistics.mean(r["passages_given"] for r in judged), 2),
        "context_chars_mean": int(statistics.mean(r["context_chars"] for r in judged)),
        "retrieval_ms_mean": int(statistics.mean(r["retrieval_ms"] for r in judged)),
        "cost": round(sum(r["cost"] for r in judged + oos), 5),
        "by_subject": {sub: {m: _mean(r[m] for r in judged if r["subject"] == sub)
                             for m in ("context_precision", "context_recall", "faithfulness", "answer_relevancy", "factual_correctness")}
                       for sub in ("fiqh", "jawi", "tajwid")},
    }
    print(f"   precision {s['context_precision']}  recall {s['context_recall']}  faithfulness {s['faithfulness']}  "
          f"relevancy {s['answer_relevancy']}  correctness {s['factual_correctness']}  declined {s['declined']}/{s['answerable']}  "
          f"OOS declined {s['out_of_syllabus_declined']}/{s['out_of_syllabus']}  ${s['cost']:.4f}  ({time.perf_counter() - t0:.0f}s)", flush=True)
    return {"rag": rag, "summary": s, "items": judged, "out_of_syllabus": oos}


RAG_LABELS = {"R1": "R1 Naive Dense RAG", "R2": "R2 Hybrid RAG + Reranker", "R3": "R3 Parent-Document RAG"}
METRICS = [("context_precision", "Context precision"), ("context_recall", "Context recall"), ("faithfulness", "Faithfulness"),
           ("answer_relevancy", "Answer relevancy"), ("factual_correctness", "Factual correctness")]


def main(n: int, rags: list[str]) -> None:
    questions = pick_questions(n)
    print(f"{len(questions)} questions: {dict(sorted({s: sum(q['subject'] == s for q in questions) for s in ('fiqh', 'jawi', 'tajwid')}.items()))}")
    results = [evaluate(r, questions) for r in rags]
    res = {"date": datetime.now(timezone.utc).isoformat(timespec="seconds"), "generator": MODELS[GENERATOR].label,
           "judge": MODELS[JUDGE].label, "embedding": "BAAI/bge-m3", "n": len(questions),
           "questions": [{"id": q["id"], "subject": q["subject"], "level": q["level"], "question": q["question_rumi"]} for q in questions],
           "rags": results}
    OUT.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    md = [f"# RAG evaluation (mean over {len(questions)} answerable questions)", "",
          f"Answer model: {res['generator']} (fixed) · judge: {res['judge']} · embedding: bge-m3 · {res['date'][:10]}", "",
          "| Metric | " + " | ".join(RAG_LABELS[r["rag"]] for r in results) + " |", "|---|" + "---|" * len(results)]
    for key, label in METRICS:
        md.append(f"| {label} | " + " | ".join(f"{r['summary'][key]:.3f}" if r["summary"][key] is not None else "-" for r in results) + " |")
    md.append(f"| Declined answers (of {len(questions)}) | " + " | ".join(str(r["summary"]["declined"]) for r in results) + " |")
    md.append(f"| Out-of-syllabus correctly declined (of {len(OUT_OF_SYLLABUS)}) | "
              + " | ".join(str(r["summary"]["out_of_syllabus_declined"]) for r in results) + " |")
    for kind, label in (("general", "general"), ("near", "near the syllabus")):
        md.append(f"| - {label} (of {results[0]['summary']['out_of_syllabus_by_kind'][kind]['n']}) | "
                  + " | ".join(str(r["summary"]["out_of_syllabus_by_kind"][kind]["declined"]) for r in results) + " |")
    md.append("| Passages retrieved → read by the model (mean) | "
              + " | ".join(f"{r['summary']['retrieved_mean']} → {r['summary']['passages_given_mean']}" for r in results) + " |")
    md.append("| Characters read (mean) | " + " | ".join(str(r["summary"]["context_chars_mean"]) for r in results) + " |")
    md.append("| Retrieval time (ms) | " + " | ".join(str(r["summary"]["retrieval_ms_mean"]) for r in results) + " |")
    OUT.with_suffix(".md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))
    print(f"-> {OUT}  (spent so far ${spent_usd():.4f})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=45)
    ap.add_argument("--rag", nargs="+", default=["R1", "R2", "R3"])
    a = ap.parse_args()
    main(a.n, a.rag)
