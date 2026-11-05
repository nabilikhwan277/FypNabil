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


def _tail(text: str, n: int) -> str:
    """The last ~n characters of text, starting at a word boundary."""
    if n <= 0:
        return ""
    t = text[-n:]
    i = t.find(" ") if len(text) > n else -1
    return (t[i + 1:] if 0 <= i < n // 2 else t).strip()


def _split_long(content: str, max_chars: int, overlap: int | None = None) -> list[str]:
    """Split on blank-line paragraphs; overlap = last paragraph of previous piece
    (or, if `overlap` is given, its last `overlap` characters; 0 = none).
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
            if overlap is None:
                cur = [cur[-1]] if len(cur[-1]) < max_chars // 2 else []  # overlap
            else:
                cur = [t] if (t := _tail(pieces[-1], overlap)) else []
        cur.append(p)
    if cur:
        pieces.append("\n\n".join(cur))
    return pieces


def _as_str_list(v) -> str:
    if isinstance(v, (list, tuple)):
        return ",".join(str(x) for x in v)
    return "" if v is None else str(v)


def _header_meta(note: Note) -> tuple[str, dict]:
    m = note.meta
    header = f"Topik: {m.get('topic_rumi', '')} | {m.get('topic_jawi', '')}"
    return header, {
        "topic_id": note.topic_id,
        "subject": m.get("subject", ""),
        "bab": int(m.get("bab") or 0),
        "topic_rumi": m.get("topic_rumi", ""),
        "topic_jawi": m.get("topic_jawi", ""),
        "source": m.get("source", ""),
        "pdf_pages": _as_str_list(m.get("pdf_pages")),
        "verified": bool(m.get("verified", False)),
    }


def _make(note: Note, pieces: list[tuple[int, str, str]]) -> list[Chunk]:
    """(section index, `##` title, text) in note order -> chunks with the topic header and metadata.
    `section` is always the `##` title, so R3 can pass the whole section whatever the chunking method."""
    header, base_meta = _header_meta(note)
    parts: dict[int, int] = {}
    chunks: list[Chunk] = []
    for s_idx, title, piece in pieces:
        p_idx = parts[s_idx] = parts.get(s_idx, -1) + 1
        chunks.append(Chunk(f"{note.topic_id}::s{s_idx:02d}p{p_idx}", f"{header}\nBahagian: {title}\n\n{piece}",
                            {**base_meta, "section": title, "part": p_idx}))
    return chunks


def chunk_note(note: Note, max_chars: int = MAX_CHARS, overlap: int | None = None) -> list[Chunk]:
    """A. Section + size (the live method): one chunk per `##` section, long sections split at max_chars."""
    return _make(note, [(s, title, piece) for s, (title, content) in enumerate(_sections(note.body))
                        if len(content) >= MIN_CHARS for piece in _split_long(content, max_chars, overlap)])


# ---------------------------------------------------------------- other chunking methods (experiment plan v3, 2.2)
_TABLE = re.compile(r"^\s*\|")
_RUMI = re.compile(r"Rumi\b|\(Rumi\)")
_JAWI = re.compile(r"Jawi\b|\(Jawi\)")


def _major(spans: list[tuple[int, int, int, str]], start: int, end: int) -> tuple[int, str]:
    """The (section index, title) that owns most of the characters start..end."""
    best = max(spans, key=lambda s: min(end, s[1]) - max(start, s[0]))
    return best[2], best[3]


def _stream(note: Note) -> tuple[str, list[tuple[int, int, int, str]]]:
    """The note body as one text (headings kept as text) and each section's span in it."""
    text, spans = "", []
    for s, (title, content) in enumerate(_sections(note.body)):
        part = f"## {title}\n{content}"
        start = len(text) + (2 if text else 0)
        text = f"{text}\n\n{part}" if text else part
        spans.append((start, len(text), s, title))
    return text, spans


def chunk_window(note: Note, size: int = 600, overlap: int = 100) -> list[Chunk]:
    """B. Fixed window: every `size` characters (cut at a space), `overlap` characters repeated, headings ignored."""
    text, spans = _stream(note)
    pieces, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            cut = max(text.rfind(" ", start + size // 2, end), text.rfind("\n", start + size // 2, end))
            end = cut if cut > 0 else end
        piece = text[start:end].strip()
        if len(piece) >= MIN_CHARS:
            pieces.append((*_major(spans, start, end), piece))
        if end >= len(text):
            break
        nxt = max(end - overlap, start + 1)
        while 0 < nxt < end and not text[nxt - 1].isspace():   # start the next window on a word
            nxt += 1
        start = nxt
    return _make(note, pieces)


def chunk_subsection(note: Note, max_chars: int = MAX_CHARS) -> list[Chunk]:
    """C. Sub-section: each `###` sub-section is its own chunk (text before the first `###` too)."""
    pieces = []
    for s, (title, content) in enumerate(_sections(note.body)):
        for sub in re.split(r"\n(?=###\s)", content):
            if len(sub.strip()) >= MIN_CHARS:
                pieces += [(s, title, p) for p in _split_long(sub.strip(), max_chars)]
    return _make(note, pieces)


def _blocks(content: str) -> list[tuple[str, list[str]]]:
    """Split a section into ("text", lines) and ("table", lines) blocks, in order."""
    out: list[tuple[str, list[str]]] = []
    for line in content.splitlines():
        kind = "table" if _TABLE.match(line) else "text"
        if out and out[-1][0] == kind:
            out[-1][1].append(line)
        else:
            out.append((kind, [line]))
    return out


def chunk_table_rows(note: Note, rows: int = 3, max_chars: int = MAX_CHARS) -> list[Chunk]:
    """D. Table rows: every `rows` table rows are a chunk, with the caption line and column names repeated;
    the text around the tables is chunked as in A."""
    pieces = []
    for s, (title, content) in enumerate(_sections(note.body)):
        if len(content) < MIN_CHARS:
            continue
        caption = ""
        for kind, lines in _blocks(content):
            if kind == "text":
                txt = "\n".join(lines).strip()
                caption = next((ln for ln in reversed(lines) if ln.strip()), caption)
                if len(txt) >= MIN_CHARS:
                    pieces += [(s, title, p) for p in _split_long(txt, max_chars)]
                continue
            head = lines[:2] if len(lines) > 1 and set(lines[1].strip()) <= set("|-: ") else lines[:1]
            body = lines[len(head):] or head
            for i in range(0, len(body), rows):
                pieces.append((s, title, "\n".join(([caption] if caption else []) + head + body[i:i + rows])))
    return _make(note, pieces)


def _units(content: str) -> list[str]:
    """Smallest units of meaning: a Rumi line with its Jawi line, a list item with its sub-lines,
    a table row with the column names, or a paragraph line."""
    units: list[str] = []
    open_ = False                 # the last unit may still take continuation lines
    for kind, lines in _blocks(content):
        if kind == "table":
            head = lines[:2] if len(lines) > 1 and set(lines[1].strip()) <= set("|-: ") else []
            units += ["\n".join(head + [row]) for row in lines[len(head):]]
            open_ = False
            continue
        for line in lines:
            if not line.strip():
                open_ = False
                continue
            last = units[-1] if units and open_ else ""
            if last and (line[:1].isspace() or (_JAWI.search(line) and _RUMI.search(last) and not _JAWI.search(last))):
                units[-1] = f"{last}\n{line}"
            else:
                units.append(line)
                open_ = True
    return [u.strip() for u in units if u.strip()]


def _pack(units: list[str], size: int) -> list[str]:
    """Join neighbouring units up to `size` characters, never cutting a unit."""
    out: list[str] = []
    for u in units:
        if out and len(out[-1]) + len(u) + 1 <= size:
            out[-1] += "\n" + u
        else:
            out.append(u)
    return out


def chunk_bilingual(note: Note, size: int = 600) -> list[Chunk]:
    """E. Bilingual pair: units that keep each Rumi line with its Jawi line (and each table row whole),
    packed up to `size` characters within a section."""
    return _make(note, [(s, title, p) for s, (title, content) in enumerate(_sections(note.body))
                        if len(content) >= MIN_CHARS for p in _pack(_units(content), size)
                        if len(p) >= MIN_CHARS])


def chunk_semantic(note: Note, embed_fn, max_chars: int = MAX_CHARS, min_chars: int = 200,
                   percentile: float = 25.0) -> list[Chunk]:
    """F. Semantic: the note as a stream of units (headings ignored); cut where the cosine between
    neighbouring units falls into the lowest `percentile` of the note, keeping chunks min_chars..max_chars.
    embed_fn(list[str]) -> normalised vectors (numpy array)."""
    import numpy as np

    units = [(s, title, u) for s, (title, content) in enumerate(_sections(note.body)) for u in _units(content)]
    if not units:
        return []
    vecs = np.asarray(embed_fn([u for _, _, u in units]))
    sims = (vecs[:-1] * vecs[1:]).sum(axis=1)
    cut_at = float(np.percentile(sims, percentile)) if len(sims) else 1.0
    groups: list[list[tuple[int, str, str]]] = [[units[0]]]
    for i, unit in enumerate(units[1:]):
        size = sum(len(u) + 1 for _, _, u in groups[-1])
        if size + len(unit[2]) > max_chars or (sims[i] <= cut_at and size >= min_chars):
            groups.append([unit])
        else:
            groups[-1].append(unit)
    pieces = []
    for g in groups:
        owner: dict[tuple[int, str], int] = {}
        for s, title, u in g:
            owner[(s, title)] = owner.get((s, title), 0) + len(u)
        s, title = max(owner, key=owner.get)
        text = "\n".join(u for _, _, u in g)
        if len(text) >= MIN_CHARS:
            pieces.append((s, title, text))
    pieces.sort(key=lambda p: p[0])     # _make numbers parts per section in note order
    return _make(note, pieces)
