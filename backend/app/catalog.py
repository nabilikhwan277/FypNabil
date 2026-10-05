"""Subject -> bab -> topic catalogue built from note metadata and the question
bank, merged with one student's mastery."""
from __future__ import annotations

from collections import Counter, defaultdict
from functools import lru_cache

from .notes import SUBJECT_NAMES, note_meta
from .questions import load_questions

SUBJECT_ORDER = ("fiqh", "jawi", "tajwid")


@lru_cache
def _question_counts() -> dict[str, dict[int, int]]:
    counts: dict[str, Counter] = defaultdict(Counter)
    for q in load_questions().values():
        counts[q["topic_id"]][q["level"]] += 1
    return {t: dict(c) for t, c in counts.items()}


@lru_cache
def _topics() -> list[dict]:
    counts = _question_counts()
    out = []
    for tid, m in note_meta().items():
        pdf = m.get("pdf_pages") or [0]
        out.append({
            "id": tid, "subject": m["subject"], "bab": int(m.get("bab") or 0),
            "bab_rumi": m.get("bab_rumi", ""), "bab_jawi": m.get("bab_jawi", ""),
            "title_rumi": m.get("topic_rumi", ""), "title_jawi": m.get("topic_jawi", ""),
            "book_pages": m.get("book_pages") or [], "order": int(pdf[0]),
            "question_counts": {str(k): v for k, v in sorted(counts.get(tid, {}).items())},
            "verified": bool(m.get("verified", False)),
        })
    return sorted(out, key=lambda t: (SUBJECT_ORDER.index(t["subject"]), t["bab"], t["order"]))


def topic(topic_id: str) -> dict | None:
    return next((t for t in _topics() if t["id"] == topic_id), None)


def catalog(mastery: dict[str, dict] | None = None) -> list[dict]:
    mastery = mastery or {}
    subjects = []
    for s in SUBJECT_ORDER:
        babs: dict[int, dict] = {}
        for t in (t for t in _topics() if t["subject"] == s):
            m = mastery.get(t["id"], {})
            entry = {**t, "mastery": round(m.get("mastery", 0.0), 3), "attempts": m.get("attempts", 0),
                     "level_unlocked": m.get("level_unlocked", 1),
                     "has_questions": bool(t["question_counts"])}
            b = babs.setdefault(t["bab"], {"bab": t["bab"], "title_rumi": t["bab_rumi"],
                                           "title_jawi": t["bab_jawi"], "topics": []})
            b["topics"].append(entry)
        topics = [t for b in babs.values() for t in b["topics"] if t["has_questions"]]
        subjects.append({
            "id": s, "name_rumi": SUBJECT_NAMES[s]["rumi"], "name_jawi": SUBJECT_NAMES[s]["jawi"],
            "babs": [babs[k] for k in sorted(babs)],
            "topic_count": len(topics),
            "mastery": round(sum(t["mastery"] for t in topics) / len(topics), 3) if topics else 0.0,
        })
    return subjects
