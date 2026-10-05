"""Split topic notes (markdown + YAML front-matter) into retrieval chunks.

Pure functions, no model or DB access, so they are easy to unit-test.

Strategy
- One chunk per `##` section; `###` sub-sections stay with their parent.
- Sections longer than MAX_CHARS are split on paragraph boundaries,
  carrying the last paragraph over as overlap.
- Each chunk text is prefixed with the topic and section title (Rumi + Jawi),
  so a chunk still makes sense on its own after retrieval.
- Rumi and Jawi lines of the same section stay together.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

MAX_CHARS = 1500      # ~400-500 tokens of mixed Rumi/Jawi text
MIN_CHARS = 40        # drop near-empty sections (e.g. a lone heading)

_FRONT_MATTER = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.S)
_H2 = re.compile(r"^##\s+(?!#)(.+?)\s*$", re.M)


@dataclass
class Note:
    meta: dict
    body: str
    path: Path | None = None

    @property
    def topic_id(self) -> str:
        return self.meta["id"]


@dataclass
class Chunk:
    id: str
    text: str
    metadata: dict = field(default_factory=dict)


def parse_note(text: str, path: Path | None = None) -> Note:
    m = _FRONT_MATTER.match(text)
    if not m:
        raise ValueError(f"note has no front-matter: {path}")
    meta = yaml.safe_load(m.group(1)) or {}
    return Note(meta=meta, body=text[m.end():], path=path)


def load_note(path: Path) -> Note:
    return parse_note(path.read_text(encoding="utf-8"), path)


def _sections(body: str) -> list[tuple[str, str]]:
    """Return [(title, content)] split on `##` headings. Text before the first
    `##` (usually the `#` title and short notes) becomes an 'Ringkasan' section."""
    matches = list(_H2.finditer(body))
    out: list[tuple[str, str]] = []
    head = body[: matches[0].start()] if matches else body
    head = re.sub(r"^#\s+.*$", "", head, flags=re.M).strip()  # drop the H1 title
    if head:
        out.append(("Ringkasan", head))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        out.append((m.group(1).strip(), body[m.end():end].strip()))
    return out


def _split_long(content: str, max_chars: int) -> list[str]:
    """Split on blank-line paragraphs; overlap = last paragraph of previous piece.
    A single paragraph longer than max_chars is split on line breaks."""
    if len(content) <= max_chars:
        return [content]
    paras: list[str] = []
    for p in re.split(r"\n\s*\n", content):
        p = p.strip()
        if not p:
            continue
        if len(p) <= max_chars:
            paras.append(p)
        else:  # long table or list: split by lines
            buf = ""
            for line in p.splitlines():
                if buf and len(buf) + len(line) + 1 > max_chars:
                    paras.append(buf)
                    buf = ""
                buf = f"{buf}\n{line}" if buf else line
            if buf:
                paras.append(buf)

    pieces: list[str] = []
    cur: list[str] = []
    for p in paras:
        if cur and sum(len(x) + 2 for x in cur) + len(p) > max_chars:
            pieces.append("\n\n".join(cur))
            cur = [cur[-1]] if len(cur[-1]) < max_chars // 2 else []  # overlap
        cur.append(p)
    if cur:
        pieces.append("\n\n".join(cur))
    return pieces


def _as_str_list(v) -> str:
    if isinstance(v, (list, tuple)):
        return ",".join(str(x) for x in v)
    return "" if v is None else str(v)


def chunk_note(note: Note, max_chars: int = MAX_CHARS) -> list[Chunk]:
    m = note.meta
    header = f"Topik: {m.get('topic_rumi', '')} | {m.get('topic_jawi', '')}"
    base_meta = {
        "topic_id": note.topic_id,
        "subject": m.get("subject", ""),
        "bab": int(m.get("bab") or 0),
        "topic_rumi": m.get("topic_rumi", ""),
        "topic_jawi": m.get("topic_jawi", ""),
        "source": m.get("source", ""),
        "pdf_pages": _as_str_list(m.get("pdf_pages")),
        "verified": bool(m.get("verified", False)),
    }
    chunks: list[Chunk] = []
    for s_idx, (title, content) in enumerate(_sections(note.body)):
        if len(content) < MIN_CHARS:
            continue
        for p_idx, piece in enumerate(_split_long(content, max_chars)):
            cid = f"{note.topic_id}::s{s_idx:02d}p{p_idx}"
            text = f"{header}\nBahagian: {title}\n\n{piece}"
            chunks.append(Chunk(cid, text, {**base_meta, "section": title, "part": p_idx}))
    return chunks
