"""BM25 keyword index over the note chunks (pure Python, built in memory from
the ChromaDB collection). Complements dense search for exact-word questions,
e.g. Jawi spelling items that name one word from a textbook table."""
from __future__ import annotations

import math
import threading
from collections import Counter

from ..assess.jawi_text import tokens
from .store import NOTES, get_collection

K1, B = 1.5, 0.75

# Question-instruction words that carry no topic information. Removed from the
# QUERY only (documents keep them), so "Tulis perkataan 'bacaan' dalam tulisan
# Jawi" is matched on "bacaan". Rumi and Jawi forms.
QUERY_STOPWORDS = {
    "tulis", "tuliskan", "perkataan", "dalam", "tulisan", "jawi", "jawikan", "rumi",
    "apakah", "berapakah", "bilakah", "siapakah", "manakah", "mengapakah", "bagaimanakah",
    "nyatakan", "terangkan", "jelaskan", "senaraikan", "berikan", "namakan", "huraikan",
    "yang", "dan", "atau", "di", "ke", "dari", "daripada", "untuk", "bagi", "pada", "ini",
    "itu", "dengan", "adalah", "ialah", "berikut", "tersebut", "satu", "dua", "tiga",
    "contoh", "maksud", "soalan", "jawapan", "betul", "salah", "latihan", "isi", "tempat",
    "kosong",
    "توليس", "توليسكن", "ڤركاتاءن", "ڤركاتاٴن", "دالم", "توليسن", "جاوي", "جاويكن",
    "اڤاكه", "براڤاكه", "ڽاتاكن", "تراڠكن", "سنارايكن", "بريكن", "ناماكن", "يڠ", "دان",
    "اتاو", "د", "ك", "درڤد", "اونتوق", "باݢي", "ڤد", "اين", "ايت", "دڠن", "اياله",
    "برايكوت", "ترسبوت",
}


_STOP = {t for w in QUERY_STOPWORDS for t in tokens(w)}


class BM25Index:
    def __init__(self, ids: list[str], docs: list[str], metas: list[dict]) -> None:
        self.ids, self.docs, self.metas = ids, docs, metas
        self.tfs = [Counter(tokens(d)) for d in docs]
        self.lens = [sum(tf.values()) for tf in self.tfs]
        self.avg_len = sum(self.lens) / max(len(self.lens), 1)
        df = Counter(t for tf in self.tfs for t in tf)
        n = len(docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def search(self, query: str, k: int = 10, where: dict | None = None) -> list[tuple[int, float]]:
        """Return [(doc_index, score)] best first. `where` = simple equality filter."""
        q = [t for t in tokens(query) if t in self.idf and t not in _STOP]
        scores: list[tuple[int, float]] = []
        for i, tf in enumerate(self.tfs):
            if where and any(self.metas[i].get(key) != val for key, val in where.items()):
                continue
            s = 0.0
            for t in q:
                f = tf.get(t)
                if f:
                    s += self.idf[t] * f * (K1 + 1) / (f + K1 * (1 - B + B * self.lens[i] / self.avg_len))
            if s > 0:
                scores.append((i, s))
        scores.sort(key=lambda x: -x[1])
        return scores[:k]


_index: BM25Index | None = None
_lock = threading.Lock()


def get_bm25() -> BM25Index:
    global _index
    if _index is None:
        with _lock:
            if _index is None:
                got = get_collection(NOTES).get(include=["documents", "metadatas"])
                _index = BM25Index(got["ids"], got["documents"], got["metadatas"])
    return _index


def reset_bm25() -> None:
    global _index
    _index = None
