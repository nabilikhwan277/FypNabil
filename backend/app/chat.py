"""AI Chat Assistant — answers free-form pupil questions using RAG.

The LLM is grounded entirely in retrieved textbook chunks, the same KB
used by the assessor.  We limit output to 300 tokens and apply light
repetition penalties to stop the 1B model from looping.

Rate limit: MAX_TURNS per session, tracked in-process (resets on restart).
"""
from __future__ import annotations

import re
import threading
from dataclasses import dataclass, field

from .kb.retriever import search_notes
from .llm import get_llm
from . import prompts

MAX_TURNS = 10          # messages per session (reset on restart or re-login)
MAX_Q_LEN = 500         # characters; trim silently
MAX_HISTORY = 3         # assistant turns kept in the prompt
MAX_NEW_TOKENS = 300
REPETITION_PENALTY = 1.15
NO_REPEAT_NGRAM = 4
CHUNK_SEP = "\n---\n"

_counters: dict[int, int] = {}   # student_id -> turn count
_lock = threading.Lock()


@dataclass
class ChatSource:
    topic_rumi: str
    topic_jawi: str
    pages: list[int]


@dataclass
class ChatReply:
    reply: str
    sources: list[ChatSource]
    turns_left: int


class ChatLimitError(Exception):
    """Raised when the student has used all allowed chat turns."""


def reset_turns(student_id: int) -> None:
    """Reset the turn counter — call after login."""
    with _lock:
        _counters[student_id] = 0


def _increment(student_id: int) -> int:
    """Increment and return the NEW count.  Raises ChatLimitError if over limit."""
    with _lock:
        n = _counters.get(student_id, 0) + 1
        if n > MAX_TURNS:
            raise ChatLimitError(f"Had {MAX_TURNS} turns for this session.")
        _counters[student_id] = n
        return n


def _build_context(hits) -> str:
    """Format retrieved chunks into a readable block for the prompt."""
    parts = []
    for h in hits:
        meta = h.metadata
        pages = meta.get("book_pages") or []
        page_str = f" (ms. {', '.join(str(p) for p in pages)})" if pages else ""
        title = meta.get("section_rumi") or meta.get("topic_rumi") or ""
        parts.append(f"[{title}{page_str}]\n{h.text.strip()}")
    return CHUNK_SEP.join(parts) if parts else "(tiada petikan berkaitan ditemui)"


def _build_history(history: list[dict]) -> str:
    """Format recent turns into a readable block."""
    if not history:
        return "(tiada)"
    lines = []
    for turn in history[-MAX_HISTORY:]:
        role = "Murid" if turn.get("role") == "user" else "Bulan"
        lines.append(f"{role}: {turn.get('content', '').strip()}")
    return "\n".join(lines)


def _clean(text: str) -> str:
    """Strip prompt echo and common artefacts from the LLM output."""
    # Sometimes the model echoes "Jawapan Bulan:" at the start.
    text = re.sub(r"^[Jj]awapan\s+[Bb]ulan\s*:?\s*", "", text).strip()
    # Trim at the first sign of repetition (same 5-word span appearing twice).
    words = text.split()
    seen: set[tuple] = set()
    for i in range(len(words) - 4):
        span = tuple(words[i : i + 5])
        if span in seen:
            text = " ".join(words[:i]).strip()
            break
        seen.add(span)
    return text.strip()


def ask(
    *,
    student_id: int,
    message: str,
    subject: str | None = None,
    history: list[dict] | None = None,
) -> ChatReply:
    """Answer a pupil's question using RAG + the local LLM.

    Parameters
    ----------
    student_id : int   — used for rate limiting only (no DB lookup)
    message    : str   — the pupil's question (Rumi or Jawi)
    subject    : str | None — hint to narrow the KB search
    history    : list[{role, content}] — recent conversation turns
    """
    count = _increment(student_id)
    message = message.strip()[:MAX_Q_LEN]
    history = history or []

    # Retrieve relevant note chunks.
    hits = search_notes(message, subject=subject, k=4)

    context = _build_context(hits)
    hist_text = _build_history(history)

    prompt_text = prompts.render("chat", context=context, history=hist_text, question=message)
    messages = [{"role": "user", "content": prompt_text}]

    gen = get_llm().generate(
        messages,
        max_new_tokens=MAX_NEW_TOKENS,
        temperature=0.3,          # slight warmth for natural chat; still mostly deterministic
        repetition_penalty=REPETITION_PENALTY,
        no_repeat_ngram_size=NO_REPEAT_NGRAM,
    )
    reply = _clean(gen.text)

    # Deduplicate sources by topic.
    seen_topics: set[str] = set()
    sources: list[ChatSource] = []
    for h in hits:
        tid = h.metadata.get("topic_id", "")
        if tid and tid not in seen_topics:
            seen_topics.add(tid)
            pages = h.metadata.get("book_pages") or []
            sources.append(ChatSource(
                topic_rumi=h.metadata.get("topic_rumi", tid),
                topic_jawi=h.metadata.get("topic_jawi", ""),
                pages=pages,
            ))

    return ChatReply(
        reply=reply,
        sources=sources,
        turns_left=MAX_TURNS - count,
    )
