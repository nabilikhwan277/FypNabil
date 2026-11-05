"""RAG settings study: tune the selected RAG type (R3 Parent-Document) one setting at a time.

rag_eval.py compares the RAG types R1, R2 and R3. This study tunes the settings inside the chosen one,
for a thesis table:  Setting | Options tested | Evidence | Selection.
Each run changes ONE setting; every other setting stays at the current value (marked *).

  chunk size          characters per chunk (chunking.MAX_CHARS)          300, 600, 1000, 1500*, whole section
  number of chunks    k best chunks matched; their sections are passed    2, 4*, 6, 10
  context limit       characters the answer model reads (CONTEXT_CHARS)  1800, 3600*, 7200, no limit
  minimum similarity  matched chunks below this bge-m3 cosine are dropped 0* ... 0.85 (Tanya Bulan uses 0.55)
  query variants      2 rewrites of the question by the answer model      none*, fused (RRF), round-robin
  search scope        where to search                                     all notes, subject*, topic first
  matching            how chunks are matched                              bge-m3 only, BM25 only, hybrid RRF*
  Jawi weight         bge-m3 weight for questions typed in Jawi           0, 0.25*, 0.5, 1

Questions: the 45 answerable and 24 out-of-syllabus questions of rag_eval.py, with the same answer model,
prompts and judge, so the current setting reproduces the R3 column there.

Gold evidence (made once, cached): the judge (Claude Haiku 5.5) splits each reference answer into statements
and marks which numbered textbook lines state each one. It reads the question's own topic note plus every
other section that any setting retrieved for that question (pooling, as in TREC). A passage is relevant when
it contains such a line, so every setting is scored the same way, with no more API calls:
  hit rate         questions where the text the model reads contains at least one supporting line
  evidence recall  reference statements whose supporting line is in that text
  precision        relevant passages among those read, weighted by rank (average precision, as RAGAS)
  MRR              1 / rank of the first relevant passage read
Answer metrics, for the settings that change what the model reads: faithfulness, factual correctness and
declined answers (rag_eval.py prompts and judge).
Differences from the current setting get a 95% paired bootstrap interval; a change counts as clear only
when the interval does not include 0.

Usage:  .venv\\Scripts\\python eval\\rag_settings.py            (retrieval + answers; about $0.3 the first time)
        .venv\\Scripts\\python eval\\rag_settings.py --no-llm   (retrieval metrics only, from the saved gold evidence)
Results: eval/results/rag_settings.json and .md (shown on the 📊 Penilaian page, "RAG Evaluation" tab)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "eval"))

import rag_eval as RE  # noqa: E402  (questions, answer model, prompts and judge)

from backend.app.assess.jawi_text import is_arabic_script  # noqa: E402
from backend.app.config import get_settings  # noqa: E402
from backend.app.embeddings import embed, get_embedder  # noqa: E402
from backend.app.kb.chunking import (MAX_CHARS, chunk_bilingual, chunk_note, chunk_semantic, chunk_subsection,  # noqa: E402
                                     chunk_table_rows, chunk_window, load_note)
from backend.app.llm import resolve_device  # noqa: E402
from backend.app.kb.lexical import BM25Index  # noqa: E402
from backend.app.kb.rag import CONTEXT_CHARS  # noqa: E402
from backend.app.kb.retriever import CANDIDATES, JAWI_DENSE_WEIGHT, RRF_K  # noqa: E402
from backend.app.kb.store import NOTES, get_collection  # noqa: E402
from backend.app.llm_api import MODELS, complete, spent_usd  # noqa: E402

RESULTS = ROOT / "eval" / "results"
OUT = RESULTS / "rag_settings.json"
GOLD = RESULTS / "rag_gold.json"
CACHE = ROOT / "eval" / "cache" / "rag_settings"
WHOLE = 0          # chunk size 0 = one chunk per whole section
NO_LIMIT = 0       # context limit 0 = the model reads every passed section in full


# ------------------------------------------------------------------ settings
@dataclass(frozen=True)
class Cfg:
    chunk: int = MAX_CHARS                   # characters per chunk (0 = whole section)
    k: int = 4                               # chunks matched
    sections: int = 3                        # at most this many sections passed (R3)
    limit: int = CONTEXT_CHARS["R3"]         # characters the model reads (0 = no limit)
    min_sim: float = 0.0                     # drop matched chunks whose bge-m3 cosine is lower
    variants: str = "none"                   # none | rrf | round_robin
    scope: str = "subject"                   # all | subject | topic
    matching: str = "hybrid"                 # dense | bm25 | hybrid
    jawi_weight: float = JAWI_DENSE_WEIGHT   # bge-m3 weight in the fusion for Jawi-script questions
    unit: str = "section"                    # section (R3: pass the whole section) | chunk (pass the chunk itself)
    jawi: bool = False                       # ask the Jawi-script version of the question
    chunker: str = "section"                 # section* | window | subsection | table_rows | bilingual | semantic
    overlap: int = -1                        # characters repeated between chunks (-1 = the method's own default)
    embedding: str = "bge-m3"                # a key of EMBEDDINGS


DEFAULT = Cfg()

# embedding models: Hugging Face id, query prefix, passage prefix (the e5 models are trained with these prefixes)
EMBEDDINGS = {
    "bge-m3": ("BAAI/bge-m3", "", ""),
    "e5-large": ("intfloat/multilingual-e5-large", "query: ", "passage: "),
    "e5-base": ("intfloat/multilingual-e5-base", "query: ", "passage: "),
    "minilm": ("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2", "", ""),
}
_encoders: dict = {}


def encoder(name: str):
    """The sentence-transformers model of an embedding (bge-m3 = the live one)."""
    if name == "bge-m3":
        return get_embedder()
    if name not in _encoders:
        from sentence_transformers import SentenceTransformer
        s = get_settings()
        m = SentenceTransformer(EMBEDDINGS[name][0], device=resolve_device(s.device), cache_folder=str(s.hf_cache_dir))
        if m.device.type == "cuda":
            m.half()                # fp16, as the live bge-m3
        _encoders[name] = m
    return _encoders[name]


def encode(name: str, texts: list[str], query: bool) -> np.ndarray:
    prefix = EMBEDDINGS[name][1 if query else 2]
    return np.asarray(encoder(name).encode([prefix + t for t in texts], normalize_embeddings=True, batch_size=4,
                                           show_progress_bar=False), dtype=np.float32)


def make_chunks(note, cfg: Cfg) -> list:
    size = cfg.chunk or 10**9
    ov = None if cfg.overlap < 0 else cfg.overlap
    if cfg.chunker == "section":
        return chunk_note(note, max_chars=size, overlap=ov)
    if cfg.chunker == "window":
        return chunk_window(note, size=cfg.chunk, overlap=100 if ov is None else ov)
    if cfg.chunker == "subsection":
        return chunk_subsection(note, max_chars=size)
    if cfg.chunker == "table_rows":
        return chunk_table_rows(note, max_chars=size)
    if cfg.chunker == "bilingual":
        return chunk_bilingual(note, size=cfg.chunk)
    if cfg.chunker == "semantic":
        return chunk_semantic(note, lambda ts: encode("bge-m3", ts, query=False), max_chars=size)
    raise ValueError(cfg.chunker)


# ------------------------------------------------------------------ in-memory index (one per chunking + embedding)
class Index:
    """The notes chunked one way, with embedding vectors and a BM25 index, searched exactly like the live
    retriever (kb/retriever.py hybrid_search + kb/rag.py R3), but in memory so the live index is never touched."""

    def __init__(self, cfg: Cfg):
        files = sorted(Path(get_settings().knowledge_dir).glob("*/*.md"))
        chunks = [c for f in files for c in make_chunks(load_note(f), cfg)]
        self.cfg = cfg
        self.chunk = cfg.chunk
        self.ids = [c.id for c in chunks]
        self.texts = [c.text for c in chunks]
        self.metas = [c.metadata for c in chunks]
        self.vecs = self._vectors()
        self.bm25 = BM25Index(self.ids, self.texts, self.metas)
        self._masks: dict = {}
        groups: dict[tuple, list[int]] = {}
        for i, m in enumerate(self.metas):
            groups.setdefault((m["topic_id"], m["section"]), []).append(i)
        self.parent: dict[tuple, str] = {}
        for key, idx in groups.items():     # like rag._parent: all parts of the section, in order
            idx.sort(key=lambda i: self.metas[i].get("part", 0))
            text = self.texts[idx[0]]
            for i in idx[1:]:               # later parts repeat the chunk header; keep only their body
                text += "\n" + self.texts[i].split("\n\n", 1)[-1]
            self.parent[key] = text
        if cfg.chunker != "section":        # other methods only change the matching: R3 passes the same sections
            live = index(DEFAULT).parent
            self.parent = {k: live.get(k, v) for k, v in self.parent.items()}

    def _vectors(self) -> np.ndarray:
        live = (self.cfg.chunk, self.cfg.chunker, self.cfg.overlap, self.cfg.embedding) == (MAX_CHARS, "section", -1, "bge-m3")
        if live:   # the live index: use its stored vectors, so the current setting is exact
            got = get_collection(NOTES).get(ids=self.ids, include=["embeddings"])
            by_id = dict(zip(got["ids"], got["embeddings"]))
            if len(by_id) == len(self.ids):
                return np.array([by_id[i] for i in self.ids], dtype=np.float32)
        key = hashlib.sha256("\x00".join(self.texts).encode()).hexdigest()[:16]
        emb = "" if self.cfg.embedding == "bge-m3" else f"{self.cfg.embedding}_"   # bge-m3 keeps its old cache names
        path = CACHE / f"vectors_{emb}{self.chunk}_{key}.npy"
        if path.exists():
            return np.load(path)
        print(f"   embedding {len(self.texts)} chunks ({self.cfg.chunker}, {self.cfg.embedding}) ...", flush=True)
        vecs = encode(self.cfg.embedding, self.texts, query=False)
        path.parent.mkdir(parents=True, exist_ok=True)
        np.save(path, vecs)
        return vecs

    def _mask(self, subject: str | None, topic: str | None) -> np.ndarray:
        if (subject, topic) not in self._masks:
            self._masks[(subject, topic)] = np.array(
                [(not subject or m["subject"] == subject) and (not topic or m["topic_id"] == topic) for m in self.metas])
        return self._masks[(subject, topic)]

    def cosines(self, vec: np.ndarray) -> np.ndarray:
        return self.vecs @ vec

    def dense(self, vec: np.ndarray, n: int, subject: str | None, topic: str | None) -> list[int]:
        sims = self.cosines(vec)
        idx = np.where(self._mask(subject, topic))[0]
        return idx[np.argsort(-sims[idx], kind="stable")][:n].tolist()

    def keyword(self, query: str, n: int, subject: str | None, topic: str | None) -> list[int]:
        where = {k: v for k, v in (("subject", subject), ("topic_id", topic)) if v}
        return [i for i, _ in self.bm25.search(query, n, where)]

    def match(self, query: str, vec: np.ndarray, n: int, subject: str | None, topic: str | None, cfg: Cfg) -> list[int]:
        if cfg.matching == "dense":
            return self.dense(vec, n, subject, topic)
        if cfg.matching == "bm25":
            return self.keyword(query, n, subject, topic)
        dense, lex = self.dense(vec, CANDIDATES, subject, topic), self.keyword(query, CANDIDATES, subject, topic)
        w = cfg.jawi_weight if is_arabic_script(query) else 1.0
        fused: dict[int, float] = {}
        for weight, ranked in ((w, dense), (1.0, lex)):     # Reciprocal Rank Fusion, as hybrid_search
            for rank, i in enumerate(ranked, start=1):
                fused[i] = fused.get(i, 0.0) + weight / (RRF_K + rank)
        return sorted(fused, key=lambda i: -fused[i])[:n]

    def topic_first(self, query: str, vec: np.ndarray, n: int, subject: str | None, topic: str | None, cfg: Cfg) -> list[int]:
        """As rag._topic_first: search the topic, fill up from the subject if it gives fewer than 2 chunks."""
        if not topic:
            return self.match(query, vec, n, subject, None, cfg)
        hits = self.match(query, vec, n, subject, topic, cfg)
        if len(hits) >= 2:
            return hits
        extra = self.match(query, vec, n + len(hits), subject, None, cfg)
        return hits + [i for i in extra if i not in hits][: n - len(hits)]


_indexes: dict[tuple, Index] = {}


def index(cfg: Cfg) -> Index:
    key = (cfg.chunk, cfg.chunker, cfg.overlap, cfg.embedding)
    if key not in _indexes:
        _indexes[key] = Index(cfg)
    return _indexes[key]


# ------------------------------------------------------------------ one retrieval
@dataclass
class Query:
    key: str                    # question id, or "oos:<n>"
    text: str                   # Rumi question
    jawi: str                   # Jawi question ("" for out-of-syllabus)
    subject: str | None
    topic: str | None
    reference: str = ""
    kind: str = "answerable"    # answerable | general | near
    rewrites: tuple = ()


_vec_cache: dict[tuple, np.ndarray] = {}


def qvec(text: str, emb: str = "bge-m3") -> np.ndarray:
    if (text, emb) not in _vec_cache:
        _vec_cache[(text, emb)] = (np.asarray(embed([text])[0], dtype=np.float32) if emb == "bge-m3"
                                   else encode(emb, [text], query=True)[0])
    return _vec_cache[(text, emb)]


def retrieve(q: Query, cfg: Cfg) -> dict:
    """The passages the answer model would read for one question under one setting."""
    ix = index(cfg)
    vec = lambda t: qvec(t, cfg.embedding)  # noqa: E731
    text = q.jawi if cfg.jawi and q.jawi else q.text
    subject = None if cfg.scope == "all" or q.kind != "answerable" else q.subject
    topic = q.topic if cfg.scope == "topic" and q.kind == "answerable" else None
    queries = [text, *(q.rewrites if cfg.variants != "none" else ())]
    if len(queries) == 1:
        matched = ix.topic_first(text, vec(text), cfg.k, subject, topic, cfg)
    elif cfg.variants == "rrf":                 # fuse the rankings of the question and its rewrites
        fused: dict[int, float] = {}
        for qt in queries:
            for rank, i in enumerate(ix.topic_first(qt, vec(qt), CANDIDATES, subject, topic, cfg), start=1):
                fused[i] = fused.get(i, 0.0) + 1.0 / (RRF_K + rank)
        matched = sorted(fused, key=lambda i: -fused[i])[: cfg.k]
    else:                                       # round-robin: 1st of each query, then 2nd of each, ...
        lists = [ix.topic_first(qt, vec(qt), cfg.k, subject, topic, cfg) for qt in queries]
        matched = []
        for rank in range(cfg.k):
            for lst in lists:
                if rank < len(lst) and lst[rank] not in matched:
                    matched.append(lst[rank])
        matched = matched[: cfg.k]
    sims = ix.cosines(vec(text))
    top_sim = float(max((sims[i] for i in matched), default=0.0))
    kept = [i for i in matched if sims[i] >= cfg.min_sim]
    passages: list[dict] = []
    if cfg.unit == "chunk":
        passages = [{"id": ix.ids[i], "topic": ix.metas[i]["topic_id"], "section": ix.metas[i]["section"],
                     "text": ix.texts[i]} for i in kept]
    else:                                       # R3: the whole section of each matched chunk, best first
        seen = set()
        for i in kept:
            key = (ix.metas[i]["topic_id"], ix.metas[i]["section"])
            if key not in seen:
                seen.add(key)
                passages.append({"id": f"{key[0]}::{key[1]}", "topic": key[0], "section": key[1], "text": ix.parent[key]})
        passages = passages[: cfg.sections]
    given, size = [], 0                         # as Retrieved.given: fill the context limit, best first
    for p in passages:
        if given and cfg.limit and size + len(p["text"]) > cfg.limit:
            break
        given.append({**p, "text": p["text"][: cfg.limit] if cfg.limit else p["text"]})
        size += len(given[-1]["text"]) + 2
    return {"given": given, "context": "\n\n".join(p["text"] for p in given).strip(), "top_sim": round(top_sim, 4),
            "matched": len(matched), "removed": len(matched) - len(kept)}


# ------------------------------------------------------------------ the settings tested
def _sections(n: int) -> Cfg:
    """n sections passed; they come from the best max(4, n + 1) chunks (the current R3: 4 chunks, 3 sections)."""
    return replace(DEFAULT, sections=n, k=max(4, n + 1))


SIM_STEPS = [0.0, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85]
CHAT_GATE = 0.55   # chat.py: Tanya Bulan answers from the notes only if its best bge-m3 match is at least this

SETTINGS = [   # key, label, what it is, [(option label, cfg)], answer metrics?
    ("chunk", "Chunk size", "characters per chunk; chunks are matched, then their whole sections are passed (R3)",
     [("300", replace(DEFAULT, chunk=300)), ("600", replace(DEFAULT, chunk=600)), ("1,000", replace(DEFAULT, chunk=1000)),
      ("1,500", DEFAULT), ("whole section", replace(DEFAULT, chunk=WHOLE))], True),
    ("sections", "Number of sections (k)", "how many different textbook sections the answer model is given",
     [("1", _sections(1)), ("2", _sections(2)), ("3", DEFAULT), ("5", _sections(5)), ("10", _sections(10))], True),
    ("limit", "Context limit", "characters of the passed sections the answer model reads",
     [("1,800", replace(DEFAULT, limit=1800)), ("3,600", DEFAULT), ("7,200", replace(DEFAULT, limit=7200)),
      ("no limit", replace(DEFAULT, limit=NO_LIMIT))], True),
    ("min_sim", "Minimum similarity", "matched chunks with a lower bge-m3 cosine are dropped; no chunk left = decline",
     [(f"{t:.2f}" if t else "0 (none)", replace(DEFAULT, min_sim=t)) for t in SIM_STEPS], False),
    ("variants", "Query variants", "two rewrites of the question (by the answer model) are searched as well",
     [("none", DEFAULT), ("2 rewrites + RRF fusion", replace(DEFAULT, variants="rrf")),
      ("2 rewrites + round-robin", replace(DEFAULT, variants="round_robin"))], False),
    ("scope", "Search scope", "which notes are searched",
     [("all notes", replace(DEFAULT, scope="all")), ("subject", DEFAULT), ("topic first", replace(DEFAULT, scope="topic"))], False),
    ("matching", "Matching method", "how chunks are matched to the question",
     [("bge-m3 only", replace(DEFAULT, matching="dense")), ("BM25 only", replace(DEFAULT, matching="bm25")),
      ("hybrid bge-m3 + BM25", DEFAULT)], False),
    ("jawi_weight", "Jawi-script questions", "bge-m3 weight in the fusion when the question is typed in Jawi",
     [("Rumi (same questions)", DEFAULT)]
     + [(f"weight {w:g}", replace(DEFAULT, jawi=True, jawi_weight=w)) for w in (0.0, 0.25, 0.5, 1.0)], False),
]
CURRENT = {"chunk": "1,500", "sections": "3", "limit": "3,600", "min_sim": "0 (none)", "variants": "none",
           "scope": "subject", "matching": "hybrid bge-m3 + BM25", "jawi_weight": "weight 0.25"}


# ------------------------------------------------------------------ questions
REWRITE_RULES = """A Year 5 pupil asked a question about the KAFA textbook (Ibadah, Jawi or Tajwid).
Write the question again in 2 different ways, in simple Bahasa Melayu (Rumi), with the same meaning.
Do not answer it and do not add facts."""
REWRITE_SCHEMA = {"type": "object", "properties": {"rewrites": {"type": "array", "items": {"type": "string"}}},
                  "required": ["rewrites"], "additionalProperties": False}


def rewrites(question: str) -> tuple:
    c = complete(RE.GENERATOR, [{"role": "system", "content": REWRITE_RULES}, {"role": "user", "content": question}],
                 schema=REWRITE_SCHEMA, max_tokens=300, tag="rag_settings:rewrite")
    return tuple(x.strip() for x in ((c.data or {}).get("rewrites") or []) if x.strip())[:2]


def questions(use_llm: bool) -> tuple[list[Query], list[Query]]:
    qs = RE.pick_questions(45)
    if use_llm:
        with ThreadPoolExecutor(max_workers=6) as ex:
            rw = list(ex.map(rewrites, [q["question_rumi"] for q in qs]))
    else:                               # the rewrites of the last full run
        prev = {x["id"]: tuple(x["rewrites"]) for x in json.loads(OUT.read_text(encoding="utf-8"))["questions"]} \
            if OUT.exists() else {}
        rw = [prev.get(q["id"], ()) for q in qs]
    answerable = [Query(q["id"], q["question_rumi"], q.get("question_jawi", ""), q["subject"], q["topic_id"],
                        q.get("reference_answer_rumi", ""), rewrites=r) for q, r in zip(qs, rw)]
    oos = [Query(f"oos:{i}", text, "", None, None, kind=kind) for i, (text, kind) in enumerate(RE.OUT_OF_SYLLABUS, 1)]
    return answerable, oos


# ------------------------------------------------------------------ gold evidence (pooled, judged once)
GOLD_RULES = """You mark the evidence for a reference answer in a Year 5 KAFA textbook (Malay, written in Rumi and in Jawi script).
1. Split the REFERENCE ANSWER into short statements, one fact each.
2. For each statement list the numbers of ALL textbook lines that state that fact, in Rumi or in Jawi.
   A line counts only if a pupil could give the fact from it; a line that only names the topic does not count.
   If no line states the fact, give an empty list."""
GOLD_SCHEMA = {"type": "object", "properties": {"statements": {"type": "array", "items": {"type": "object", "properties": {
    "statement": {"type": "string"}, "lines": {"type": "array", "items": {"type": "integer"}}},
    "required": ["statement", "lines"], "additionalProperties": False}}},
    "required": ["statements"], "additionalProperties": False}
MIN_LINE = 8       # shorter lines (a lone word, an empty table cell) never count as evidence


def _lines(text: str) -> list[str]:
    body = text.split("\n\n", 1)[-1] if text.startswith("Topik:") else text   # drop the chunk header
    return [s for s in (ln.strip() for ln in body.splitlines()) if len(s) >= 3 and not set(s) <= set("|-: ")]


def gold_one(q: Query, pool: list[tuple]) -> dict:
    """pool: (topic, section) keys: the question's own topic note, then every other retrieved section."""
    whole = index(replace(DEFAULT, chunk=WHOLE))
    titles = {m["topic_id"]: m["topic_rumi"] for m in whole.metas}
    numbered, blocks = [], []
    for key in pool:
        rows = []
        for ln in _lines(whole.parent[key]):
            numbered.append(ln)
            rows.append(f"[{len(numbered)}] {ln}")
        blocks.append(f"=== {titles.get(key[0], key[0])} | {key[1]} ===\n" + "\n".join(rows))
    c = complete(RE.JUDGE, [{"role": "system", "content": GOLD_RULES},
                            {"role": "user", "content": f"QUESTION: {q.text}\n\nREFERENCE ANSWER:\n{q.reference}\n\n"
                                                        "TEXTBOOK LINES:\n" + "\n\n".join(blocks)}],
                 schema=GOLD_SCHEMA, max_tokens=2500, tag="rag_settings:gold")
    statements = []
    for s in (c.data or {}).get("statements") or []:
        lines = sorted({numbered[n - 1] for n in s.get("lines") or [] if 1 <= n <= len(numbered)})
        statements.append({"statement": s.get("statement", ""), "lines": [ln for ln in lines if len(ln) >= MIN_LINE]})
    return {"question": q.text, "reference": q.reference, "statements": statements,
            "pool": [f"{t}::{s}" for t, s in pool], "lines_shown": len(numbered), "cost": c.cost}


def make_gold(answerable: list[Query], pooled: dict[str, set], use_llm: bool) -> dict:
    old = json.loads(GOLD.read_text(encoding="utf-8")) if GOLD.exists() else {}
    whole = index(replace(DEFAULT, chunk=WHOLE))
    jobs = []
    for q in answerable:
        own = [key for key in whole.parent if key[0] == q.topic]
        pool = own + sorted(k for k in pooled.get(q.key, set()) if k[0] != q.topic)
        if q.key in old and set(old[q.key]["pool"]) >= {f"{t}::{s}" for t, s in pool}:
            continue            # already judged with at least this pool
        jobs.append((q, pool))
    if jobs and not use_llm:
        raise SystemExit(f"{len(jobs)} questions have no gold evidence yet: run without --no-llm")
    with ThreadPoolExecutor(max_workers=6) as ex:
        for (q, _), g in zip(jobs, ex.map(lambda j: gold_one(*j), jobs)):
            old[q.key] = g
    GOLD.write_text(json.dumps(old, indent=1, ensure_ascii=False), encoding="utf-8")
    return old


# ------------------------------------------------------------------ metrics
def score(r: dict, gold: dict) -> dict | None:
    """Gold-evidence retrieval metrics of what the model reads. None if the textbook has no evidence at all."""
    stmts = [s for s in gold["statements"] if s["lines"]]
    if not stmts:
        return None
    lines = {ln for s in stmts for ln in s["lines"]}
    rel = [any(ln in p["text"] for ln in lines) for p in r["given"]]
    covered = [any(ln in r["context"] for ln in s["lines"]) for s in stmts]
    return {"hit_rate": float(any(rel)), "evidence_recall": sum(covered) / len(covered),
            "precision": RE.average_precision(rel), "mrr": next((1 / i for i, f in enumerate(rel, 1) if f), 0.0),
            "passages": len(r["given"]), "chars": len(r["context"])}


RETRIEVAL_METRICS = ("hit_rate", "evidence_recall", "precision", "mrr")
ANSWER_METRICS = ("faithfulness", "factual_correctness")


def paired_ci(a: list, b: list, reps: int = 10000, seed: int = 7) -> list | None:
    """Mean of (option - current) over the same questions, with a 95% bootstrap interval."""
    d = np.array([x - y for x, y in zip(a, b) if x is not None and y is not None], dtype=float)
    if not len(d):
        return None
    boots = d[np.random.default_rng(seed).integers(0, len(d), (reps, len(d)))].mean(axis=1)
    return [round(float(d.mean()), 4), round(float(np.percentile(boots, 2.5)), 4), round(float(np.percentile(boots, 97.5)), 4)]


def _mean(xs) -> float | None:
    xs = [x for x in xs if x is not None]
    return round(statistics.mean(xs), 4) if xs else None


# ------------------------------------------------------------------ answers (settings that change what the model reads)
def answer(q: Query, r: dict) -> dict:
    passages = [p["text"] for p in r["given"]]
    out = {"declined": True, "faithfulness": None, "factual_correctness": None, "answer": "", "answer_cost": 0.0,
           "tokens_in": 0}
    if not passages:                    # nothing passed the similarity threshold: the system declines, no model call
        out.update(answer=RE.DECLINE, factual_correctness=0.0 if q.kind == "answerable" else None)
        return out
    c = RE.ask(q.text, r["context"], "rag_settings:answer")
    out.update(answer=c.text.strip(), declined=RE.is_declined(c.text), answer_cost=c.cost, tokens_in=c.tokens_in)
    if q.kind == "answerable":
        if out["declined"]:
            out["factual_correctness"] = 0.0
        else:
            out["faithfulness"], _, _ = RE.judge_faithfulness("\n\n".join(passages), out["answer"])
            out["factual_correctness"], _ = RE.judge_correctness(q.text, q.reference, out["answer"])
    return out


# ------------------------------------------------------------------ the thesis table: evidence and selection
LABEL = {"hit_rate": "hit rate", "evidence_recall": "evidence recall", "precision": "precision", "mrr": "MRR",
         "faithfulness": "faithfulness", "factual_correctness": "factual correctness"}
# per setting: metrics quoted in the evidence, the deciding metric, and metrics that must not clearly drop
RULES = {
    "chunk": (("evidence_recall", "hit_rate", "factual_correctness", "faithfulness"), "factual_correctness", ("faithfulness", "evidence_recall")),
    # more sections always lower precision a little, so only faithfulness guards here
    "sections": (("evidence_recall", "hit_rate", "factual_correctness", "faithfulness", "precision"), "factual_correctness", ("faithfulness",)),
    "limit": (("evidence_recall", "hit_rate", "factual_correctness", "faithfulness"), "factual_correctness", ("faithfulness",)),
    "variants": (("evidence_recall", "hit_rate", "precision"), "evidence_recall", ("hit_rate", "precision")),
    "scope": (("evidence_recall", "hit_rate", "precision"), "evidence_recall", ("hit_rate", "precision")),
    "matching": (("evidence_recall", "hit_rate", "precision"), "evidence_recall", ("hit_rate", "precision")),
    "jawi_weight": (("evidence_recall", "hit_rate", "precision"), "evidence_recall", ("hit_rate", "precision")),
}


def _val(o: dict, m: str):
    return (o.get("answers") or {}).get(m) if m in ANSWER_METRICS else o["metrics"].get(m)


def _change(o: dict, m: str) -> int:
    """+1 clearly higher, -1 clearly lower, 0 no clear change (95% interval of the paired difference vs current)."""
    d = (o.get("diff") or {}).get(m)
    return 0 if not d else 1 if d[1] > 0 else -1 if d[2] < 0 else 0


def _f(v) -> str:
    return "–" if v is None else f"{v:.2f}"


def _and(xs: list[str]) -> str:
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]


def _ratio(o: dict, cur: dict) -> float:
    return o["metrics"]["chars"] / cur["metrics"]["chars"] if cur["metrics"]["chars"] else 1.0


def _evidence(s: dict, keys: tuple, primary: str, sizes: bool) -> str:
    """One clause per option with a clear change, then the options with none (quoting the deciding metric)."""
    cur = next(o for o in s["options"] if o["current"])
    keys = tuple(m for m in keys if _val(cur, m) is not None)
    if primary not in keys:
        primary = "evidence_recall"
    parts, same = [], []
    for o in s["options"]:
        if o["current"] or o["option"].startswith("Rumi"):
            continue
        clear = sorted(((m, c) for m in keys if (c := _change(o, m))), key=lambda mc: mc[0] != primary)
        extra = ""
        if o.get("answers") and cur.get("answers") and o["answers"]["declined"] != cur["answers"]["declined"]:
            extra += f", {o['answers']['declined']} vs {cur['answers']['declined']} declined"
        if sizes and abs(_ratio(o, cur) - 1) >= 0.15:
            extra += f", {_ratio(o, cur):.1f}× the text"
        if clear:
            parts.append(f"{o['option']}: " + ", ".join(f"{'higher' if c > 0 else 'lower'} {LABEL[m]} "
                                                       f"({_f(_val(o, m))} vs {_f(_val(cur, m))})" for m, c in clear) + extra)
        else:
            same.append((o, extra))
    if same:
        vals = _and([_f(_val(o, primary)) for o, _ in same])
        parts.append(f"{_and([o['option'] for o, _ in same])}: no clear difference "
                     f"({LABEL[primary]} {vals} vs {_f(_val(cur, primary))}"
                     + "".join(x for _, x in same if x and len(same) == 1) + ")")
    return "; ".join(parts) + "."


def _per(o: dict, m: str) -> dict:
    rows = o.get("answer_items") if m in ANSWER_METRICS else o.get("per_question")
    return {k: v.get(m) for k, v in (rows or {}).items()}


def _beats(a: dict, b: dict, m: str) -> bool:
    """a is clearly better than b on m (paired over the same questions)."""
    pa, pb = _per(a, m), _per(b, m)
    keys = [k for k in pa if k in pb]
    d = paired_ci([pa[k] for k in keys], [pb[k] for k in keys])
    return bool(d and d[1] > 0)


def _choose(s: dict, primary: str, guards: tuple) -> tuple[dict, list[dict]]:
    """The current option, unless others are clearly better on the deciding metric and clearly worse on no guard.
    Of those, the one that reads the least text, unless a bigger one is clearly better than it.
    Returns (selected option, the other clearly better options)."""
    cur = next(o for o in s["options"] if o["current"])
    if _val(cur, primary) is None:
        primary = "evidence_recall"
    cands = sorted((o for o in s["options"] if not o["current"] and not o["option"].startswith("Rumi")
                    and _change(o, primary) > 0 and all(_change(o, g) >= 0 for g in guards)),
                   key=lambda o: o["metrics"]["chars"])
    for c in cands:
        if not any(_beats(o, c, primary) for o in cands if o is not c):
            return c, [o for o in cands if o is not c]
    return cur, []


def explain(s: dict, res: dict) -> dict:
    """Options tested / Evidence / Selection for one setting (the columns of the thesis table)."""
    key, opts = s["key"], s["options"]
    cur = next(o for o in opts if o["current"])
    names = [o["option"] for o in opts]
    oos_n = sum(res["oos"].values())
    if key == "min_sim":
        sim, steps = res["similarity"], res["similarity"]["steps"]
        base = steps[0]
        safe = max((t for t in steps if t["answerable_rejected"] == 0 and t["evidence_recall"] == base["evidence_recall"]),
                   key=lambda t: t["threshold"])
        clean = next((t for t in steps if t["general_rejected"] + t["near_rejected"] == oos_n), None)
        c, gate = sim["top_cosine"], sim.get("chat_gate")
        ev = [f"Best-match cosine: answerable questions {c['answerable']['min']:.2f}–{c['answerable']['max']:.2f}, "
              f"general out-of-syllabus up to {c['general']['max']:.2f}, near-syllabus up to {c['near']['max']:.2f}, "
              "so no threshold separates them",
              f"{safe['threshold']:.2f} is the highest that loses no answerable question or evidence (it rejects "
              f"{safe['general_rejected']}/{res['oos']['general']} general and {safe['near_rejected']}/{res['oos']['near']} near-syllabus ones)"]
        ev.append(f"rejecting every out-of-syllabus question needs {clean['threshold']:.2f}, which also rejects "
                  f"{clean['answerable_rejected']}/{res['n']} answerable ones" if clean else
                  "no threshold up to 0.85 rejects every out-of-syllabus question")
        if gate:
            ev.append(f"Tanya Bulan's gate ({gate['threshold']:.2f} on its best match in the subject) turns away "
                      f"{gate['answerable_rejected']}/{res['n']} answerable questions")
        chunk = next((x for x in res["settings"] if x["key"] == "chunk"), {"options": []})
        declined = next((o["answers"]["oos_declined"] for o in chunk["options"] if o["current"] and o.get("answers")), None)
        sel = f"{safe['threshold']:.2f} as a safeguard that loses no answerable question; "
        sel += (f"out-of-syllabus questions are left to the answer model's decline rule ({sum(declined.values())}/{oos_n} declined)"
                if declined else "not relied on to reject out-of-syllabus questions")
        return {"tested": f"{names[0]} to {names[-1]} ({len(names)} steps)", "evidence": "; ".join(ev) + ".",
                "selection": sel, "selected": f"{safe['threshold']:.2f}"}
    keys, primary, guards = RULES[key]
    if not res["answers_run"] and primary in ANSWER_METRICS:
        primary = "evidence_recall"
    sizes = key in ("chunk", "sections", "limit")
    best, others = _choose(s, primary, guards)
    tested = {"chunk": f"{_and(names[:-1])} characters, and whole sections",
              "sections": f"{_and(names)} sections",
              "limit": f"{_and(names[:-1])} characters, and no limit",
              "jawi_weight": f"bge-m3 weight {_and([n.split()[-1] for n in names[1:]])} for questions typed in Jawi"}.get(key, _and(names))
    ev = _evidence(s, keys, primary, sizes)
    if key == "jawi_weight":
        rumi = opts[0]
        ev = (f"The same questions typed in Jawi reach evidence recall {_f(_val(cur, 'evidence_recall'))} vs "
              f"{_f(_val(rumi, 'evidence_recall'))} in Rumi; " + ev)
    if best is cur:
        sel = f"{cur['option']} (current): no option is clearly better"
    else:
        r = _ratio(best, cur)
        sel = (f"{best['option']}: clearly higher {LABEL[primary]} ({_f(_val(best, primary))} vs {_f(_val(cur, primary))})"
               + (f", with {r:.1f}× the text" if sizes and r >= 1.15 else ""))
        if others:
            sel += f"; {_and([o['option'] for o in others])} add{'s' if len(others) == 1 else ''} no clear gain over it"
    if key == "scope":
        topic = next(o for o in opts if o["option"] == "topic first")
        if best is not topic and _change(topic, "evidence_recall") >= 0:
            sel += "; topic first where the question's topic is known (marking)"
    if key == "matching" and best is cur:
        sel += "; the keyword side is what finds questions typed in Jawi"
    return {"tested": tested, "evidence": ev, "selection": sel, "selected": best["option"]}


def markdown(res: dict) -> str:
    md = [f"# RAG settings study: {res['rag']}", "",
          f"One setting changed at a time, the others at the current value. {res['n']} answerable + "
          f"{sum(res['oos'].values())} out-of-syllabus questions (as rag_eval.py) · answer model {res['generator']} · "
          f"judge {res['judge']} · {res['date'][:10]}", "",
          "| Setting | Options tested | Evidence | Selection |", "|---|---|---|---|"]
    md += [f"| {s['setting']} | {s['tested']} | {s['evidence']} | {s['selection']} |" for s in res["settings"]]
    md += ["", "Evidence uses the gold evidence (textbook lines that state each statement of the reference answer, "
           f"judged once: {res['gold']['statements_in_textbook']} of {res['gold']['statements']} statements are in the notes). "
           "'Clear' = the 95% paired bootstrap interval of the change leaves out 0.", ""]
    for s in res["settings"]:
        if s["key"] == "min_sim":
            md += [f"## {s['setting']}", "", "| Threshold | Chunks removed | Answerable rejected | Hit rate | Evidence recall | General rejected | Near rejected |",
                   "|---|---|---|---|---|---|---|"]
            md += [f"| {t['threshold']:.2f} | {t['chunks_removed']:.0%} | {t['answerable_rejected']}/{res['n']} | {_f(t['hit_rate'])} | "
                   f"{_f(t.get('evidence_recall'))} | "
                   f"{t['general_rejected']}/{res['oos']['general']} | {t['near_rejected']}/{res['oos']['near']} |"
                   for t in res["similarity"]["steps"]]
            gate = res["similarity"].get("chat_gate")
            if gate:
                md += ["", f"Tanya Bulan's gate ({gate['threshold']:.2f} on its best bge-m3 match in the subject): "
                           f"{gate['answerable_rejected']}/{res['n']} answerable, {gate['general_rejected']}/{res['oos']['general']} general "
                           f"and {gate['near_rejected']}/{res['oos']['near']} near-syllabus questions turned away."]
            md.append("")
            continue
        ans = any(o.get("answers") for o in s["options"])
        md += [f"## {s['setting']}", "", s["what"], "",
               "| Option | Hit rate | Evidence recall | Precision | MRR | Sections read | Characters |"
               + (" Faithfulness | Factual correctness | Declined | Out-of-syllabus declined |" if ans else ""),
               "|---|---|---|---|---|---|---|" + ("---|---|---|---|" if ans else "")]
        for o in s["options"]:
            m = o["metrics"]
            row = (f"| {o['option']}{' (current)' if o['current'] else ''} | {_f(m['hit_rate'])} | {_f(m['evidence_recall'])} | "
                   f"{_f(m['precision'])} | {_f(m['mrr'])} | {m['passages']:.2f} | {m['chars']} |")
            if ans:
                a = o.get("answers") or {}
                row += (f" {_f(a.get('faithfulness'))} | {_f(a.get('factual_correctness'))} | {a.get('declined', '–')} | "
                        f"{sum((a.get('oos_declined') or {}).values())} |")
            md.append(row)
        md.append("")
    md += ["## Check: the RAG types on the same gold evidence", "",
           "| RAG type | Hit rate | Evidence recall | Precision | MRR | Judge context recall | Mean abs. difference | Pearson r |",
           "|---|---|---|---|---|---|---|---|"]
    for rag, t in res["rag_types"].items():
        m = t["metrics"]
        md.append(f"| {rag} | {_f(m['hit_rate'])} | {_f(m['evidence_recall'])} | {_f(m['precision'])} | {_f(m['mrr'])} | "
                  f"{_f(t['judge_recall'])} | {_f(t['agreement']['mean_abs_diff'])} | {_f(t['agreement']['pearson'])} |")
    return "\n".join(md) + "\n"


# ------------------------------------------------------------------ run
def _sections_of(passages: list[dict]) -> set:
    """(topic, section) of passages from this study or from rag_eval.json (R1/R2 chunk ids are 'topic::s03p0')."""
    return {(p.get("topic") or p["id"].split("::")[0], p["section"]) for p in passages}


def _rag_eval_items() -> dict:
    path = RESULTS / "rag_eval.json"
    if not path.exists():
        return {}
    d = json.loads(path.read_text(encoding="utf-8"))
    return {r["rag"]: r for r in d["rags"]}


def run(use_llm: bool, workers: int = 6) -> dict:
    spent0 = spent_usd()
    answerable, oos = questions(use_llm)
    every = answerable + oos
    print(f"{len(answerable)} answerable + {len(oos)} out-of-syllabus questions", flush=True)

    # 1. what the model would read, for every option of every setting (no API calls)
    by_cfg: dict[Cfg, dict[str, dict]] = {}
    for key, _, _, options, _ in SETTINGS:
        for name, cfg in options:
            if cfg not in by_cfg:
                by_cfg[cfg] = {q.key: retrieve(q, cfg) for q in every}
        print(f"   retrieved: {key}", flush=True)

    # 2. gold evidence over the pooled sections (each question judged once)
    rag_types = _rag_eval_items()
    pooled: dict[str, set] = {q.key: set() for q in answerable}
    for runs in by_cfg.values():
        for q in answerable:
            pooled[q.key] |= _sections_of(runs[q.key]["given"])
    for r in rag_types.values():
        for it in r["items"]:
            if it["question_id"] in pooled:
                pooled[it["question_id"]] |= _sections_of(it["context"])
    gold = make_gold(answerable, pooled, use_llm)
    print(f"   gold evidence ready (spent so far ${spent_usd():.4f})", flush=True)

    # 3. answers for the settings that change what the model reads
    jobs: dict[tuple, tuple] = {}
    for key, _, _, options, with_answers in SETTINGS:
        if with_answers and use_llm:
            for _, cfg in options:
                for q in every:
                    r = by_cfg[cfg][q.key]
                    jobs.setdefault((q.key, r["context"]), (q, r))
    answers: dict[tuple, dict] = {}
    if jobs:
        print(f"   answering {len(jobs)} different (question, text) pairs ...", flush=True)
        with ThreadPoolExecutor(max_workers=workers) as ex:
            for jk, res in zip(jobs, ex.map(lambda j: answer(*j), jobs.values())):
                answers[jk] = res

    # 4. metrics per option, and differences from the current option
    reachable = [q for q in answerable if score(by_cfg[DEFAULT][q.key], gold[q.key]) is not None]
    settings = []
    for key, label, what, options, with_answers in SETTINGS:
        rows = []
        for name, cfg in options:
            runs = by_cfg[cfg]
            per = [score(runs[q.key], gold[q.key]) for q in reachable]
            row = {"option": name, "current": name == CURRENT[key], "config": asdict(cfg),
                   "metrics": {m: _mean(p[m] for p in per) for m in RETRIEVAL_METRICS}
                   | {"passages": _mean(p["passages"] for p in per), "chars": int(statistics.mean(p["chars"] for p in per))},
                   "per_question": {q.key: p for q, p in zip(reachable, per)},
                   "rejected": sum(not runs[q.key]["given"] for q in answerable),
                   "oos_rejected": {k: sum(not runs[q.key]["given"] for q in oos if q.kind == k) for k in ("general", "near")}}
            if with_answers and answers:
                got = {q.key: answers[(q.key, runs[q.key]["context"])] for q in every}
                ans = [got[q.key] for q in answerable]
                row["answers"] = {
                    "faithfulness": _mean(a["faithfulness"] for a in ans),
                    "factual_correctness": _mean(a["factual_correctness"] for a in ans),
                    "declined": sum(a["declined"] for a in ans),
                    "oos_declined": {k: sum(got[q.key]["declined"] for q in oos if q.kind == k) for k in ("general", "near")},
                    "answer_cost_per_100": round(100 * statistics.mean(got[q.key]["answer_cost"] for q in answerable), 4),
                    "tokens_in_mean": int(statistics.mean(got[q.key]["tokens_in"] for q in answerable)),
                }
                row["answer_items"] = {q.key: {k: got[q.key][k] for k in ("answer", "declined", "faithfulness", "factual_correctness")}
                                       for q in every}
            rows.append(row)
        cur = next(r for r in rows if r["current"])
        for row in rows:
            if row is cur:
                continue
            row["diff"] = {m: paired_ci([row["per_question"][q.key][m] for q in reachable],
                                        [cur["per_question"][q.key][m] for q in reachable]) for m in RETRIEVAL_METRICS}
            if "answer_items" in row:
                for m in ANSWER_METRICS:
                    row["diff"][m] = paired_ci([row["answer_items"][q.key][m] for q in answerable],
                                               [cur["answer_items"][q.key][m] for q in answerable])
        settings.append({"key": key, "setting": label, "what": what, "options": rows})

    # 5. the RAG types of rag_eval.py on the same gold evidence (a check that both tables agree)
    types = {}
    for rag, r in rag_types.items():
        items = {it["question_id"]: it for it in r["items"]}
        per, llm_recall = [], []
        for q in reachable:
            it = items.get(q.key)
            if not it:
                continue
            given = [{"text": c["text"]} for c in it["context"]]
            p = score({"given": given, "context": "\n\n".join(c["text"] for c in it["context"]).strip()}, gold[q.key])
            per.append(p)
            llm_recall.append((p["evidence_recall"], it.get("context_recall")))
        pairs = [(a, b) for a, b in llm_recall if b is not None]
        types[rag] = {"metrics": {m: _mean(p[m] for p in per) for m in RETRIEVAL_METRICS},
                      "n": len(per),
                      "judge_recall": _mean(b for _, b in pairs),
                      "agreement": {"mean_abs_diff": _mean(abs(a - b) for a, b in pairs),
                                    "pearson": round(float(np.corrcoef([a for a, _ in pairs], [b for _, b in pairs])[0, 1]), 3)
                                    if len(pairs) > 2 else None}}

    # 6. minimum similarity: what each threshold removes
    base = by_cfg[DEFAULT]
    sims = {"answerable": sorted(base[q.key]["top_sim"] for q in answerable),
            "general": sorted(base[q.key]["top_sim"] for q in oos if q.kind == "general"),
            "near": sorted(base[q.key]["top_sim"] for q in oos if q.kind == "near")}
    similarity = {"top_cosine": {k: {"min": v[0], "median": round(statistics.median(v), 4), "max": v[-1]} for k, v in sims.items()},
                  "steps": []}
    for t in SIM_STEPS:
        runs = by_cfg[replace(DEFAULT, min_sim=t)]
        matched = sum(runs[q.key]["matched"] for q in answerable)
        similarity["steps"].append({
            "threshold": t,
            "chunks_removed": round(sum(runs[q.key]["removed"] for q in answerable) / matched, 4) if matched else 0.0,
            "answerable_rejected": sum(not runs[q.key]["given"] for q in answerable),
            "hit_rate": _mean(score(runs[q.key], gold[q.key])["hit_rate"] for q in reachable),
            "evidence_recall": _mean(score(runs[q.key], gold[q.key])["evidence_recall"] for q in reachable),
            "general_rejected": sum(not runs[q.key]["given"] for q in oos if q.kind == "general"),
            "near_rejected": sum(not runs[q.key]["given"] for q in oos if q.kind == "near")})

    ix = index(DEFAULT)          # as chat.py: the best bge-m3 match in the subject (all notes for out-of-syllabus)

    def best(q: Query) -> float:
        return float(ix.cosines(qvec(q.text))[ix._mask(q.subject if q.kind == "answerable" else None, None)].max())
    similarity["chat_gate"] = {"threshold": CHAT_GATE, "answerable_rejected": sum(best(q) < CHAT_GATE for q in answerable),
                               **{f"{k}_rejected": sum(best(q) < CHAT_GATE for q in oos if q.kind == k) for k in ("general", "near")}}

    n_stmt = sum(len(gold[q.key]["statements"]) for q in answerable)
    n_found = sum(sum(bool(s["lines"]) for s in gold[q.key]["statements"]) for q in answerable)
    return {
        "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "rag": "R3 Parent-Document RAG", "generator": MODELS[RE.GENERATOR].label, "judge": MODELS[RE.JUDGE].label,
        "embedding": "BAAI/bge-m3", "current": asdict(DEFAULT), "answers_run": bool(answers),
        "n": len(answerable), "n_reachable": len(reachable),
        "oos": {k: sum(q.kind == k for q in oos) for k in ("general", "near")},
        "gold": {"statements": n_stmt, "statements_in_textbook": n_found,
                 "questions_without_evidence": [q.key for q in answerable if q not in reachable],
                 "pool_sections_mean": round(statistics.mean(len(gold[q.key]["pool"]) for q in answerable), 1)},
        "questions": [{"id": q.key, "question": q.text, "rewrites": list(q.rewrites)} for q in answerable],
        "settings": settings, "rag_types": types, "similarity": similarity,
        "spent": round(spent_usd() - spent0, 4),
    }


def main(use_llm: bool) -> None:
    res = run(use_llm)
    for s in res["settings"]:
        s.update(explain(s, res))
    OUT.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    md = markdown(res)
    OUT.with_suffix(".md").write_text(md, encoding="utf-8")
    print(md.split("\n## ")[0])
    print(f"-> {OUT}  (this run ${res['spent']:.4f}; spent so far ${spent_usd():.4f})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-llm", action="store_true", help="retrieval metrics only, from the saved gold evidence")
    a = ap.parse_args()
    main(not a.no_llm)
