"""The three RAG types compared in the experiments (blueprint §6.2).

R1  naive dense:      bge-m3 cosine in ChromaDB only
R2  hybrid + rerank:  BM25 + dense (RRF, the live retriever) then a cross-encoder
                      reranker (bge-reranker-v2-m3) re-orders the candidates
R3  parent-document:  match the small chunks (hybrid), then pass the WHOLE note
                      section each chunk comes from, so rubric points are not cut

All three search the question's own topic first and fill up from the subject,
like search_notes.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass

from ..config import get_settings
from ..embeddings import embed
from .retriever import Hit, dense_search, hybrid_search
from .store import NOTES, get_collection

RAG_TYPES = ("R1", "R2", "R3")
CONTEXT_CHARS = {"R1": 1800, "R2": 1800, "R3": 3600}   # R3 passes whole sections, so it gets more room
# R3 for marking: 4 chunks matched, at most 3 whole sections passed, no minimum similarity.
# The RAG settings study's choices (6 chunks, 5 sections, minimum 0.35) raised the factual correctness of ANSWERS,
# but in marking they lowered agreement with the teachers (QWK 0.755 -> 0.695, significant; the minimum removed
# nothing), so marking keeps these values (eval/results/r3_marking_dev.md, decided on 2 Nov 2026).
# eval/r3_marking_dev.py changes them to compare the settings.
R3_CHUNKS = 4        # chunks matched; their whole sections are passed
R3_SECTIONS = 3      # at most this many sections
R3_MIN_SIM = 0.0     # matched chunks with a lower bge-m3 cosine are dropped (0 = keep all)


@dataclass
class Retrieved:
    rag: str
    hits: list[Hit]

    def given(self) -> list[Hit]:
        """The passages the model reads: best first until CONTEXT_CHARS is full
        (a first passage longer than the limit is cut to it). Lower-ranked hits are left out."""
        limit = CONTEXT_CHARS[self.rag]
        used, size = [], 0
        for h in self.hits:
            if used and size + len(h.text) > limit:
                break
            used.append(Hit(h.id, h.text[:limit], h.score, h.metadata))
            size += len(used[-1].text) + 2
        return used

    @property
    def context(self) -> str:
        return "\n\n".join(h.text for h in self.given()).strip()

    def chunks(self) -> list[dict]:
        """What was given to the model (only what it read), for the trace and the grounding evaluation."""
        return [{"id": h.id, "section": h.metadata.get("section", ""), "score": h.score, "text": h.text}
                for h in self.given()]


def _topic_first(search, query: str, subject: str | None, topic_id: str | None, k: int) -> list[Hit]:
    if not topic_id:
        return search(query, k, subject, None)
    hits = search(query, k, subject, topic_id)
    if len(hits) >= 2:
        return hits
    seen = {h.id for h in hits}
    extra = search(query, k + len(hits), subject, None)
    return hits + [h for h in extra if h.id not in seen][: k - len(hits)]


_reranker = None
_rerank_lock = threading.Lock()


def get_reranker():
    global _reranker
    if _reranker is None:
        with _rerank_lock:
            if _reranker is None:
                from sentence_transformers import CrossEncoder

                s = get_settings()
                _reranker = CrossEncoder(s.reranker_model_id, device=s.reranker_device, max_length=512,
                                         cache_dir=str(s.hf_cache_dir))
    return _reranker


def _parent(hit: Hit) -> Hit:
    """The whole section a chunk belongs to (all its parts, in order)."""
    m = hit.metadata
    got = get_collection(NOTES).get(
        where={"$and": [{"topic_id": m.get("topic_id", "")}, {"section": m.get("section", "")}]},
        include=["documents", "metadatas"])
    parts = sorted(zip(got["metadatas"], got["documents"]), key=lambda x: x[0].get("part", 0))
    if not parts:
        return hit
    text = parts[0][1]
    for _, doc in parts[1:]:   # later parts repeat the chunk header; keep only their body
        text += "\n" + doc.split("\n\n", 1)[-1]
    return Hit(id=f"{m.get('topic_id')}::{m.get('section')}", text=text, score=hit.score, metadata=m)


_retrieve_lock = threading.Lock()


def retrieve(query: str, *, rag: str = "R2", subject: str | None = None, topic_id: str | None = None,
             k: int = 4) -> Retrieved:
    """Thread-safe: experiment workers share one GPU embedder and one reranker."""
    if rag not in RAG_TYPES:
        raise ValueError(f"unknown RAG type {rag}")
    with _retrieve_lock:
        return _retrieve(query, rag, subject, topic_id, k)


def _retrieve(query: str, rag: str, subject: str | None, topic_id: str | None, k: int) -> Retrieved:
    vec = embed([query])[0]
    if rag == "R1":
        hits = _topic_first(lambda q, n, s, t: dense_search(vec, n, s, t), query, subject, topic_id, k)
        return Retrieved(rag, hits)
    hybrid = lambda q, n, s, t: hybrid_search(q, n, s, t, vec=vec)  # noqa: E731
    if rag == "R2":
        cands = _topic_first(hybrid, query, subject, topic_id, max(12, k * 3))
        if not cands:
            return Retrieved(rag, [])
        scores = get_reranker().predict([(query, h.text) for h in cands])
        order = sorted(range(len(cands)), key=lambda i: -float(scores[i]))[:k]
        return Retrieved(rag, [Hit(cands[i].id, cands[i].text, round(float(scores[i]), 4), cands[i].metadata)
                               for i in order])
    matched = _topic_first(hybrid, query, subject, topic_id, max(k, R3_CHUNKS))
    sims = _cosines(vec, [h.id for h in matched]) if R3_MIN_SIM > 0 else {}
    seen, parents = set(), []
    for h in matched:
        if R3_MIN_SIM > 0 and sims.get(h.id, 0.0) < R3_MIN_SIM:
            continue
        p = _parent(h)
        if p.id not in seen:
            seen.add(p.id)
            parents.append(p)
    return Retrieved(rag, parents[:R3_SECTIONS])


def _cosines(vec: list[float], ids: list[str]) -> dict[str, float]:
    """bge-m3 cosine of the query with each chunk (both vectors are normalised, so the dot product)."""
    if not ids:
        return {}
    got = get_collection(NOTES).get(ids=ids, include=["embeddings"])
    return {i: float(sum(a * b for a, b in zip(vec, e))) for i, e in zip(got["ids"], got["embeddings"])}
