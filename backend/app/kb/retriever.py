"""Hybrid semantic + keyword search over the textbook notes, and similarity
against reference answers.

Dense: bge-m3 cosine in ChromaDB. Keyword: BM25 (kb/lexical.py).
Fusion: Reciprocal Rank Fusion, score = sum_i 1 / (RRF_K + rank_i).
"""
from __future__ import annotations

from dataclasses import dataclass

from ..assess.jawi_text import is_arabic_script
from ..embeddings import embed
from .lexical import get_bm25
from .store import NOTES, REFS, get_collection

RRF_K = 60
CANDIDATES = 20   # per retriever before fusion
JAWI_DENSE_WEIGHT = 0.25  # tuned on the train split


@dataclass
class Hit:
    id: str
    text: str
    score: float          # dense: cosine similarity; hybrid: RRF score
    metadata: dict

    @property
    def topic_id(self) -> str:
        return self.metadata.get("topic_id", "")


def _filters(subject: str | None, topic_id: str | None, only_verified: bool) -> dict:
    f: dict = {}
    if subject:
        f["subject"] = subject
    if topic_id:
        f["topic_id"] = topic_id
    if only_verified:
        f["verified"] = True
    return f


def _where(subject: str | None, topic_id: str | None, only_verified: bool) -> dict | None:
    conds = [{k: v} for k, v in _filters(subject, topic_id, only_verified).items()]
    if not conds:
        return None
    return conds[0] if len(conds) == 1 else {"$and": conds}


def _query(collection: str, vec: list[float], k: int, where: dict | None) -> list[Hit]:
    res = get_collection(collection).query(
        query_embeddings=[vec], n_results=k, where=where,
        include=["documents", "metadatas", "distances"],
    )
    return [
        Hit(id=i, text=d, score=round(1.0 - dist, 4), metadata=m)
        for i, d, m, dist in zip(res["ids"][0], res["documents"][0], res["metadatas"][0], res["distances"][0])
    ]


def dense_search(query_or_vec, k: int, subject=None, topic_id=None, only_verified=False) -> list[Hit]:
    vec = embed([query_or_vec])[0] if isinstance(query_or_vec, str) else query_or_vec
    return _query(NOTES, vec, k, _where(subject, topic_id, only_verified))


def keyword_search(query: str, k: int, subject=None, topic_id=None, only_verified=False) -> list[Hit]:
    idx = get_bm25()
    return [
        Hit(id=idx.ids[i], text=idx.docs[i], score=round(s, 4), metadata=idx.metas[i])
        for i, s in idx.search(query, k, _filters(subject, topic_id, only_verified))
    ]


def hybrid_search(query: str, k: int, subject=None, topic_id=None, only_verified=False,
                  vec: list[float] | None = None) -> list[Hit]:
    dense = dense_search(vec if vec is not None else query, CANDIDATES, subject, topic_id, only_verified)
    lex = keyword_search(query, CANDIDATES, subject, topic_id, only_verified)
    # bge-m3 is weaker on Jawi script than on Rumi (see eval/results/retrieval_train.md),
    # so trust the keyword ranking more for Jawi-script queries.
    w_dense = JAWI_DENSE_WEIGHT if is_arabic_script(query) else 1.0
    fused: dict[str, float] = {}
    hits: dict[str, Hit] = {}
    for weight, ranked in ((w_dense, dense), (1.0, lex)):
        for rank, h in enumerate(ranked, start=1):
            fused[h.id] = fused.get(h.id, 0.0) + weight / (RRF_K + rank)
            hits.setdefault(h.id, h)
    order = sorted(fused, key=lambda i: -fused[i])[:k]
    return [Hit(id=i, text=hits[i].text, score=round(fused[i], 5), metadata=hits[i].metadata) for i in order]


def search_notes(
    query: str,
    subject: str | None = None,
    topic_id: str | None = None,
    k: int = 4,
    only_verified: bool = False,
    min_topic_hits: int = 2,
) -> list[Hit]:
    """Top-k note chunks (hybrid).

    If topic_id is given (the question's own topic), search inside that topic
    first. When the topic yields fewer than `min_topic_hits` chunks, fill the
    remaining slots from the whole subject, so related topics can still help.
    """
    vec = embed([query])[0]
    if not topic_id:
        return hybrid_search(query, k, subject, None, only_verified, vec=vec)

    hits = hybrid_search(query, k, subject, topic_id, only_verified, vec=vec)
    if len(hits) >= min_topic_hits:
        return hits
    seen = {h.id for h in hits}
    extra = hybrid_search(query, k + len(hits), subject, None, only_verified, vec=vec)
    hits += [h for h in extra if h.id not in seen][: k - len(hits)]
    return hits


def reference_similarity(answer: str, question_id: str) -> float:
    """Cosine similarity between a student answer and the stored reference
    answer of one question (0.0 if the question has no reference)."""
    got = get_collection(REFS).get(ids=[question_id], include=["embeddings"])
    if not got["ids"]:
        return 0.0
    ref = got["embeddings"][0]
    ans = embed([answer])[0]
    return round(float(sum(a * b for a, b in zip(ans, ref))), 4)
