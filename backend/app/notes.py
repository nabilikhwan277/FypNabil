"""Topic note metadata (front-matter) lookup."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from .config import get_settings
from .kb.chunking import load_note

SUBJECT_NAMES = {
    "fiqh": {"rumi": "Ibadah", "jawi": "عبادة"},
    "jawi": {"rumi": "Jawi", "jawi": "جاوي"},
    "tajwid": {"rumi": "Tajwid", "jawi": "تجويد"},
}


@lru_cache
def note_meta() -> dict[str, dict]:
    root = Path(get_settings().knowledge_dir)
    return {n.topic_id: n.meta for n in (load_note(p) for p in sorted(root.glob("*/*.md")))}


def note_body(topic_id: str) -> str | None:
    meta = note_meta().get(topic_id)
    if not meta:
        return None
    path = Path(get_settings().knowledge_dir) / meta["subject"] / f"{topic_id}.md"
    return load_note(path).body


def book_pages(topic_id: str, pdf_pages: list[int]) -> list[int]:
    """Convert PDF page numbers to the page numbers printed in the textbook."""
    meta = note_meta().get(topic_id, {})
    pdf, book = meta.get("pdf_pages") or [], meta.get("book_pages") or []
    mapping = dict(zip(pdf, book)) if len(pdf) == len(book) else {}
    return [mapping[p] for p in pdf_pages if p in mapping]


def source_label(topic_id: str, pdf_pages: list[int] | None = None) -> dict:
    meta = note_meta().get(topic_id, {})
    subj = SUBJECT_NAMES.get(meta.get("subject", ""), {"rumi": "", "jawi": ""})
    pages = book_pages(topic_id, pdf_pages or []) or (meta.get("book_pages") or [])[:1]
    pg = ", ".join(str(p) for p in pages)
    return {
        "rumi": f"Buku Teks {subj['rumi']} Tahun 5" + (f", ms. {pg}" if pg else ""),
        "jawi": f"بوكو تيکس {subj['jawi']} تاهون 5" + (f"، مس. {pg}" if pg else ""),
        "topic_rumi": meta.get("topic_rumi", ""),
        "topic_jawi": meta.get("topic_jawi", ""),
        "book_pages": pages,
    }
