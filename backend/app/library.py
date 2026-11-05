"""Books & syllabus: the textbooks and exercise books the system teaches from (Admin → Books & syllabus).

A book's files in data/ ARE the syllabus:
  textbook       topic notes          data/knowledge/<subject>/<topic_id>.md   (RAG searches them, pupils read them)
                 practice questions   data/questions/<subject>/<topic_id>.json
  exercise book  questions            data/questions/<subject>/<book_id>.json  (each linked to a topic)

BUILT-IN books are the three Year 5 textbooks the notes were first made from. UPLOADED books come from a PDF
(a scan or phone photos of the pages are fine):
  PDF → page images → the vision model transcribes each page (Jawi as printed + Rumi, Arabic exactly,
  [TIDAK JELAS] when unclear; rules of data/knowledge/_format.md) → DRAFT notes / questions with
  rubrics → a teacher checks and edits them → Publish copies them into data/ and re-indexes (kb/update.py).
Remove moves a book's files to storage/books/<id>/removed/ (pupils' progress is kept); Restore brings them back.
Working files per book in storage/books/<id>/ (git-ignored): book.json, source.pdf, pages/, draft/, removed/.
"""
from __future__ import annotations

import base64
import json
import re
import secrets
import shutil
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import yaml

from . import runtime
from .config import get_settings
from .kb.chunking import parse_note
from .llm_api import complete

SUBJECTS = ("fiqh", "jawi", "tajwid")
SUBJECT_TEXT = {"fiqh": "Ibadah (Fiqh)", "jawi": "Jawi", "tajwid": "Tajwid"}
KINDS = ("textbook", "exercise")
TRANSCRIBER, WRITER = "haiku", "luna"      # both read images; different providers
MAX_BYTES, MAX_PAGES = 150 * 1024 * 1024, 400
IMAGE_EDGE = 1568                          # long edge in pixels sent to the vision model
# rough API cost, for the estimate shown before processing
COST_PER_PAGE, COST_PER_TOPIC, COST_PER_QUESTION = 0.001, 0.003, 0.0006
NOTE_KEYS = {"id", "subject", "year", "bab", "topic_rumi", "topic_jawi", "source", "pdf_pages", "verified"}
QUESTION_TYPES = ("short", "structured", "essay")

_lock = threading.RLock()


class LibraryError(ValueError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _slug(text: str, sep: str = "_", limit: int = 40) -> str:
    s = re.sub(r"[^a-z0-9]+", sep, (text or "").lower()).strip(sep)
    return s[:limit].strip(sep) or "buku"


def _kn() -> Path:
    return Path(get_settings().knowledge_dir)


def _qn() -> Path:
    return Path(get_settings().questions_dir)


def _books() -> Path:
    return Path(get_settings().books_dir)


def _folder(book_id: str) -> Path:
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{2,80}", book_id or ""):
        raise LibraryError("unknown book")
    return _books() / book_id


def _read(book_id: str) -> dict:
    p = _folder(book_id) / "book.json"
    if not p.exists():
        raise LibraryError("unknown book")
    return json.loads(p.read_text(encoding="utf-8"))


def _write(rec: dict) -> dict:
    rec["updated"] = _now()
    folder = _folder(rec["id"])
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "book.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False), encoding="utf-8")
    return rec


# ------------------------------------------------------------------ the books and what they hold
def _note_meta(path: Path) -> dict:
    try:
        return parse_note(path.read_text(encoding="utf-8"), path).meta
    except (OSError, ValueError, yaml.YAMLError):
        return {}


def _question_file(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _builtin_title(source: str, subject: str) -> str:
    t = re.sub(r"\.pdf$", "", source or "", flags=re.I).replace("e-BOOK ", "").strip()
    return t or f"Buku Teks {SUBJECT_TEXT[subject]} Tahun 5"


def _discover_builtin() -> None:
    """Register the files that belong to no uploaded book as the built-in textbook of their subject."""
    groups: dict[str, dict] = defaultdict(lambda: {"notes": [], "questions": [], "source": ""})
    for p in sorted(_kn().glob("*/*.md")):
        m = _note_meta(p)
        if m.get("book_id") or m.get("subject") not in SUBJECTS:
            continue
        g = groups[m["subject"]]
        g["notes"].append(p.relative_to(_kn()).as_posix())
        g["source"] = g["source"] or m.get("source", "")
    for p in sorted(_qn().glob("*/*.json")):
        d = _question_file(p)
        if d.get("book_id") or d.get("subject") not in SUBJECTS:
            continue
        groups[d["subject"]]["questions"].append(p.relative_to(_qn()).as_posix())
    for subject, g in groups.items():
        bid = f"builtin-{subject}"
        p = _folder(bid) / "book.json"
        rec = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {
            "id": bid, "title": _builtin_title(g["source"], subject), "subject": subject, "kind": "textbook", "year": 5,
            "origin": "builtin", "status": "active", "created": _now(), "pages": 0, "cost": 0.0,
            "files": {"notes": [], "questions": []}}
        if rec["status"] != "active":
            continue
        for kind in ("notes", "questions"):   # files added by hand later join the built-in book
            rec["files"][kind] = sorted(set(rec["files"][kind]) | set(g[kind]))
        _write(rec)


def _counts(rec: dict) -> dict:
    """Topics and questions of a book: in data/ when active, else in its removed/ or draft/ folder."""
    if rec["status"] == "active":
        base, files = {"notes": _kn(), "questions": _qn()}, rec["files"]
    else:
        where = "removed" if rec["status"] == "removed" else "draft"
        base = {k: _folder(rec["id"]) / where / k for k in ("notes", "questions")}
        files = {k: [p.relative_to(base[k]).as_posix() for p in base[k].glob("*/*.*")] for k in base}
    questions = sum(len(_question_file(base["questions"] / f).get("questions", [])) for f in files["questions"])
    return {"topics": len(files["notes"]), "questions": questions}


def list_books() -> list[dict]:
    with _lock:
        _discover_builtin()
        out = []
        for p in sorted(_books().glob("*/book.json")):
            rec = json.loads(p.read_text(encoding="utf-8"))
            out.append(rec | _counts(rec) | {"estimate": estimate(rec)})
        order = {"processing": 0, "uploaded": 1, "draft": 2, "failed": 3, "active": 4, "removed": 5}
        return sorted(out, key=lambda r: (order.get(r["status"], 9), r["subject"], r["title"]))


def get_book(book_id: str) -> dict:
    rec = _read(book_id)
    return rec | _counts(rec) | {"estimate": estimate(rec)}


def estimate(rec: dict) -> float:
    """Rough API cost of processing an uploaded book (transcription + drafting the questions)."""
    if rec.get("origin") != "upload":
        return 0.0
    pages = rec.get("pages", 0)
    extra = (pages / 3) * COST_PER_TOPIC if rec["kind"] == "textbook" else pages * 5 * COST_PER_QUESTION
    return round(pages * COST_PER_PAGE + extra, 3)


# ------------------------------------------------------------------ upload
def add_book(data: bytes, *, filename: str, title: str, subject: str, kind: str, year: int = 5) -> dict:
    import fitz  # PyMuPDF

    title = (title or "").strip()
    if subject not in SUBJECTS or kind not in KINDS or not title:
        raise LibraryError("title, subject (fiqh/jawi/tajwid) and kind (textbook/exercise) are needed")
    if not data.startswith(b"%PDF"):
        raise LibraryError("The file is not a PDF")
    if len(data) > MAX_BYTES:
        raise LibraryError(f"The PDF is larger than {MAX_BYTES // 1024 // 1024} MB")
    try:
        pages = fitz.open(stream=data, filetype="pdf").page_count
    except Exception as e:  # noqa: BLE001 - any broken PDF
        raise LibraryError(f"The PDF cannot be opened: {e}") from e
    if not 0 < pages <= MAX_PAGES:
        raise LibraryError(f"The PDF must have 1 to {MAX_PAGES} pages (it has {pages})")
    bid = f"{subject}-{_slug(title, '-', 36)}-{secrets.token_hex(2)}"
    with _lock:
        folder = _folder(bid)
        folder.mkdir(parents=True)
        (folder / "source.pdf").write_bytes(data)
        rec = _write({"id": bid, "title": title, "subject": subject, "kind": kind, "year": int(year), "origin": "upload",
                      "status": "uploaded", "created": _now(), "source_file": Path(filename or "book.pdf").name,
                      "pages": pages, "cost": 0.0, "files": {"notes": [], "questions": []}, "log": []})
    return get_book(rec["id"])


# ------------------------------------------------------------------ processing (background job)
PAGE_RULES = """You transcribe ONE page of a Malaysian KAFA Year 5 {kind_text} for the subject {subject} for a study app.
The book is written mostly in Jawi (Malay in Arabic script), with Quran verses, hadith and doa in Arabic.
Rules:
1. Transcribe ONLY what the page says. Do not add facts, dalil, explanations or opinions.
2. Copy Arabic (Quran, hadith, doa, lafaz niat) exactly as printed, with harakat if printed.
   If a word is unclear write [TIDAK JELAS]. Never guess religious text.
3. Give every sentence in Jawi as printed AND in Rumi (Latin Malay), as markdown:
   ## <section heading in Rumi> | <heading in Jawi>
   - **Rumi:** <sentence> | **Jawi:** <sentence>
4. Tables become markdown tables. A picture that carries meaning (steps, examples) gets a one-line description.
5. Skip page numbers, decoration, QR codes, headers and footers.
6. printed_page: the page number printed on the page (0 if none). new_topic is true ONLY if a new topic
   (a unit or sub-topic of the book's contents, printed as a big title) starts on this page; then give its
   title in Rumi and Jawi. Section headings inside a topic (Pengertian, Hukum, Fadilat, Lafaz Niat, Contoh,
   Baca dan Fahami...) are NOT new topics. Give the chapter (bab) number and title if printed (0 and "" if not)."""
PAGE_SCHEMA = {"type": "object", "properties": {
    "printed_page": {"type": "integer"}, "new_topic": {"type": "boolean"},
    "bab": {"type": "integer"}, "bab_rumi": {"type": "string"}, "bab_jawi": {"type": "string"},
    "topic_rumi": {"type": "string"}, "topic_jawi": {"type": "string"}, "markdown": {"type": "string"}},
    "required": ["printed_page", "new_topic", "bab", "bab_rumi", "bab_jawi", "topic_rumi", "topic_jawi", "markdown"],
    "additionalProperties": False}

EXERCISE_RULES = """You transcribe ONE page of a Malaysian KAFA Year 5 exercise book for the subject {subject}.
The book is written mostly in Jawi (Malay in Arabic script); Arabic text must be copied exactly as printed.
Return every question on the page. Make each question complete on its own: include its instruction, word
list or options. Give it in Rumi (Latin Malay) and in Jawi as printed. If the page prints the answer (an answer
key or a filled example), give it in answer_rumi, else "". kind: short (one word or phrase), structured
(a list or 2-3 points), essay (explain or apply). If a word is unclear write [TIDAK JELAS]; never guess
religious text. printed_page: the page number printed on the page (0 if none)."""
EXERCISE_SCHEMA = {"type": "object", "properties": {
    "printed_page": {"type": "integer"},
    "questions": {"type": "array", "items": {"type": "object", "properties": {
        "number": {"type": "string"}, "question_rumi": {"type": "string"}, "question_jawi": {"type": "string"},
        "answer_rumi": {"type": "string"}, "kind": {"type": "string", "enum": list(QUESTION_TYPES)}},
        "required": ["number", "question_rumi", "question_jawi", "answer_rumi", "kind"], "additionalProperties": False}}},
    "required": ["printed_page", "questions"], "additionalProperties": False}

RUBRIC_ITEM = {"type": "object", "properties": {
    "criterion": {"type": "string"}, "marks": {"type": "integer"}, "keywords": {"type": "array", "items": {"type": "string"}}},
    "required": ["criterion", "marks", "keywords"], "additionalProperties": False}
QUESTION_ITEM = {"type": "object", "properties": {
    "level": {"type": "integer"}, "type": {"type": "string", "enum": list(QUESTION_TYPES)},
    "question_rumi": {"type": "string"}, "question_jawi": {"type": "string"},
    "reference_answer_rumi": {"type": "string"}, "reference_answer_jawi": {"type": "string"},
    "rubric": {"type": "array", "items": RUBRIC_ITEM}},
    "required": ["level", "type", "question_rumi", "question_jawi", "reference_answer_rumi", "reference_answer_jawi", "rubric"],
    "additionalProperties": False}

TOPIC_QUESTIONS_RULES = """You write practice questions for Year 5 KAFA pupils (age 10-11) from ONE textbook note.
Write 6 questions answerable ONLY from the note: 3 at level 1 (type short: one word or phrase, 1-2 marks),
2 at level 2 (type structured: list or explain 2-3 points, 3-4 marks) and 1 at level 3 (type essay: explain
and give an example, 5-6 marks). Simple Bahasa Melayu; give each question and reference answer in Rumi and in Jawi.
Rubric: one criterion per mark-earning point, marks per criterion, and keywords a correct answer would
contain: each keyword is ONE short spelling, Rumi or Jawi (e.g. ["dua rakaat", "دوا ركعة"]).
Never add facts that are not in the note."""
TOPIC_QUESTIONS_SCHEMA = {"type": "object", "properties": {"questions": {"type": "array", "items": QUESTION_ITEM}},
                          "required": ["questions"], "additionalProperties": False}

EXERCISE_ANSWER_RULES = """You prepare one exercise-book question for a marking system for Year 5 KAFA pupils.
Use ONLY the printed answer (if any) and the TEXTBOOK NOTE. Write the reference answer in Rumi and in Jawi,
the level (1 short, 2 structured, 3 essay) and a rubric: one criterion per mark-earning point, marks per
criterion, keywords a correct answer would contain: each keyword is ONE short spelling, Rumi or Jawi.
If neither the printed answer nor the note gives the answer, set answerable false."""
EXERCISE_ANSWER_SCHEMA = {"type": "object", "properties": {
    "answerable": {"type": "boolean"}, "level": {"type": "integer"}, "type": {"type": "string", "enum": list(QUESTION_TYPES)},
    "reference_answer_rumi": {"type": "string"}, "reference_answer_jawi": {"type": "string"},
    "rubric": {"type": "array", "items": RUBRIC_ITEM}},
    "required": ["answerable", "level", "type", "reference_answer_rumi", "reference_answer_jawi", "rubric"],
    "additionalProperties": False}


def _render_pages(folder: Path, job=None) -> list[Path]:
    """Every page as a JPEG (long edge IMAGE_EDGE px), done once per book."""
    import fitz

    out = folder / "pages"
    out.mkdir(exist_ok=True)
    doc = fitz.open(folder / "source.pdf")
    paths = []
    for i, page in enumerate(doc, 1):
        p = out / f"page_{i:03d}.jpg"
        if not p.exists():
            zoom = min(3.0, IMAGE_EDGE / max(page.rect.width, page.rect.height))
            page.get_pixmap(matrix=fitz.Matrix(zoom, zoom)).save(p, jpg_quality=85)
        paths.append(p)
        if job:
            job.progress(i, len(doc), f"Preparing page {i} of {len(doc)}")
    return paths


def _ask_page(rec: dict, image: Path, number: int, total: int) -> dict:
    subject = SUBJECT_TEXT[rec["subject"]]
    if rec["kind"] == "textbook":
        rules, schema = PAGE_RULES.format(kind_text="textbook", subject=subject), PAGE_SCHEMA
    else:
        rules, schema = EXERCISE_RULES.format(subject=subject), EXERCISE_SCHEMA
    b64 = base64.b64encode(image.read_bytes()).decode()
    c = complete(TRANSCRIBER, [{"role": "system", "content": rules},
                               {"role": "user", "content": [
                                   {"type": "text", "text": f"Page {number} of {total} of \"{rec['title']}\"."},
                                   {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}]}],
                 schema=schema, max_tokens=6000, tag="library:transcribe")
    if c.data is None:
        raise LibraryError(f"page {number}: the model reply was not valid")
    return c.data | {"page": number, "cost": c.cost if not c.cached else 0.0}


def _front_matter(meta: dict) -> str:
    return "---\n" + yaml.safe_dump(meta, allow_unicode=True, sort_keys=False, default_flow_style=None, width=200) + "---\n"


def _unique(base: str, taken: set[str]) -> str:
    name, n = base, 2
    while name in taken:
        name, n = f"{base}_{n}", n + 1
    taken.add(name)
    return name


def _active_topics() -> set[str]:
    return {p.stem for p in _kn().glob("*/*.md")}


def _keywords(raw: list[str]) -> list[str]:
    """One spelling per keyword: 'dua rakaat — دوا ركعة' becomes two keywords."""
    out = []
    for k in raw:
        for part in re.split(r"\s+[—–/|;]\s+|\s+-\s+", k):
            if (part := part.strip(" .,")) and part not in out:
                out.append(part)
    return out


def _question(q: dict, qid: str, origin: str, pages: list[int], **extra) -> dict:
    rubric = [{"criterion": r["criterion"].strip(), "marks": max(1, int(r["marks"])),
               "keywords": _keywords(r.get("keywords", []))} for r in q["rubric"] if r["criterion"].strip()]
    level = min(3, max(1, int(q["level"])))
    return {"id": qid, "level": level, "type": q.get("type") if q.get("type") in QUESTION_TYPES else QUESTION_TYPES[level - 1],
            "origin": origin, **extra, "question_rumi": q["question_rumi"].strip(), "question_jawi": q.get("question_jawi", "").strip(),
            "reference_answer_rumi": q["reference_answer_rumi"].strip(), "reference_answer_jawi": q.get("reference_answer_jawi", "").strip(),
            "rubric": rubric, "max_marks": sum(r["marks"] for r in rubric), "source_pages": pages}


SEGMENT_RULES = """You split a transcribed KAFA Year 5 textbook into its topics (the units / sub-topics of its contents).
For every page you get: its number, the page number printed on it, the title the page reader noted (if any),
the chapter (bab) it saw and the page's headings. A topic usually runs over several pages; headings inside a
topic (Pengertian, Hukum, Fadilat, Lafaz Niat, Contoh, Baca dan Fahami, Latihan...) do NOT start a new topic.
Pages before the first topic (cover, contents, foreword) belong to no topic.
Return the topics in page order: the page where each starts, its title in Rumi and Jawi, and its chapter
(bab) number and title (carry them over from earlier pages; 0 and "" if never shown)."""
SEGMENT_SCHEMA = {"type": "object", "properties": {"topics": {"type": "array", "items": {"type": "object", "properties": {
    "first_page": {"type": "integer"}, "topic_rumi": {"type": "string"}, "topic_jawi": {"type": "string"},
    "bab": {"type": "integer"}, "bab_rumi": {"type": "string"}, "bab_jawi": {"type": "string"}},
    "required": ["first_page", "topic_rumi", "topic_jawi", "bab", "bab_rumi", "bab_jawi"], "additionalProperties": False}}},
    "required": ["topics"], "additionalProperties": False}


def _segment(rec: dict, pages: list[dict]) -> list[dict]:
    """Where the topics start, decided once over all pages (one page alone cannot tell a topic title from a
    section heading). Falls back to the page reader's own new_topic flags if the answer is unusable."""
    lines = []
    for p in pages:
        heads = [ln.lstrip("# ").strip() for ln in p.get("markdown", "").splitlines() if ln.startswith("#")][:8]
        noted = p["topic_rumi"] if p.get("new_topic") else "-"
        lines.append(f"Page {p['page']}: printed {p.get('printed_page') or '-'}; noted title: {noted}; "
                     f"bab: {p.get('bab') or '-'} {p.get('bab_rumi', '')}; headings: {' / '.join(heads) or '-'}")
    c = complete(WRITER, [{"role": "system", "content": SEGMENT_RULES}, {"role": "user", "content": "\n".join(lines)}],
                 schema=SEGMENT_SCHEMA, max_tokens=4000, tag="library:segment")
    rec["cost"] += c.cost if not c.cached else 0.0
    starts = sorted((t for t in (c.data or {}).get("topics", []) if 1 <= t.get("first_page", 0) <= len(pages)
                     and t.get("topic_rumi", "").strip()), key=lambda t: t["first_page"])
    if starts and len({t["first_page"] for t in starts}) == len(starts):
        return starts
    out, bab = [], {"bab": 0, "bab_rumi": "", "bab_jawi": ""}
    for p in pages:
        if p.get("bab"):
            bab = {"bab": p["bab"], "bab_rumi": p.get("bab_rumi", ""), "bab_jawi": p.get("bab_jawi", "")}
        if p.get("new_topic") and p.get("topic_rumi", "").strip():
            out.append({**bab, "first_page": p["page"], "topic_rumi": p["topic_rumi"], "topic_jawi": p.get("topic_jawi", "")})
    return out


def _draft_textbook(rec: dict, pages: list[dict], draft: Path, job=None) -> None:
    taken, topics, last_bab = _active_topics(), [], {"bab": 0, "bab_rumi": "", "bab_jawi": ""}
    starts = _segment(rec, pages)
    for i, t in enumerate(starts):
        if t.get("bab"):
            last_bab = {k: t[k] for k in ("bab", "bab_rumi", "bab_jawi")}
        end = starts[i + 1]["first_page"] if i + 1 < len(starts) else len(pages) + 1
        topics.append({**last_bab, "topic_rumi": t["topic_rumi"].strip(), "topic_jawi": t.get("topic_jawi", "").strip(),
                       "pages": [p for p in pages if t["first_page"] <= p["page"] < end]})
    if not topics:
        raise LibraryError("No topic title was found on any page; check that the PDF pages are readable")
    s = rec["subject"]
    for i, t in enumerate(topics, 1):
        tid = _unique(f"{s}_b{t['bab'] or 0}_{_slug(t['topic_rumi'])}", taken)
        meta = {"id": tid, "subject": s, "year": rec["year"], "bab": t["bab"], "bab_rumi": t["bab_rumi"], "bab_jawi": t["bab_jawi"],
                "topic_rumi": t["topic_rumi"], "topic_jawi": t["topic_jawi"], "source": rec["title"], "book_id": rec["id"],
                "pdf_pages": [p["page"] for p in t["pages"]],
                "book_pages": [p["printed_page"] for p in t["pages"] if p.get("printed_page")], "verified": False}
        body = f"# {t['topic_rumi']} | {t['topic_jawi']}\n\n" + "\n\n".join(p["markdown"].strip() for p in t["pages"] if p["markdown"].strip())
        note = draft / "notes" / s / f"{tid}.md"
        note.parent.mkdir(parents=True, exist_ok=True)
        note.write_text(_front_matter(meta) + "\n" + body + "\n", encoding="utf-8")
        c = complete(WRITER, [{"role": "system", "content": TOPIC_QUESTIONS_RULES},
                              {"role": "user", "content": f"TEXTBOOK NOTE:\n<<<\n{body[:12000]}\n>>>"}],
                     schema=TOPIC_QUESTIONS_SCHEMA, max_tokens=6000, tag="library:questions")
        rec["cost"] += c.cost if not c.cached else 0.0
        qs = [_question(q, f"{tid}_q{n}", "generated", meta["pdf_pages"]) for n, q in enumerate((c.data or {}).get("questions", []), 1)
              if q.get("rubric")]
        qfile = draft / "questions" / s / f"{tid}.json"
        qfile.parent.mkdir(parents=True, exist_ok=True)
        qfile.write_text(json.dumps({"topic_id": tid, "subject": s, "book_id": rec["id"], "questions": qs},
                                    indent=2, ensure_ascii=False), encoding="utf-8")
        if job:
            job.progress(i, len(topics), f"Writing practice questions for topic {i} of {len(topics)}")


def _draft_exercise(rec: dict, pages: list[dict], draft: Path, job=None) -> None:
    from .kb.retriever import search_notes
    from .notes import note_body

    s, file_id = rec["subject"], rec["id"].replace("-", "_")
    items = [(p, q) for p in pages for q in p.get("questions", []) if q["question_rumi"].strip()]
    questions, skipped = [], []

    def one(job_item):
        n, (p, q) = job_item
        hits = search_notes(q["question_rumi"], subject=s, k=3)
        topic = hits[0].topic_id if hits else ""
        note = (note_body(topic) or "")[:8000]
        c = complete(WRITER, [{"role": "system", "content": EXERCISE_ANSWER_RULES},
                              {"role": "user", "content": f"QUESTION: {q['question_rumi']}\n\nPRINTED ANSWER: {q['answer_rumi'] or '(none)'}"
                                                          f"\n\nTEXTBOOK NOTE ({topic}):\n<<<\n{note or '(none)'}\n>>>"}],
                     schema=EXERCISE_ANSWER_SCHEMA, max_tokens=3000, tag="library:exercise")
        return n, p, q, topic, c

    with ThreadPoolExecutor(max_workers=4) as ex:
        for done, (n, p, q, topic, c) in enumerate(ex.map(one, enumerate(items, 1)), 1):
            rec["cost"] += c.cost if not c.cached else 0.0
            d = c.data or {}
            if not d.get("answerable") or not d.get("rubric") or not topic:
                skipped.append({"page": p["page"], "number": q["number"], "question_rumi": q["question_rumi"],
                                "why": "no answer in the book or the notes" if topic else "no matching topic"})
            else:
                questions.append(_question({**d, "question_rumi": q["question_rumi"], "question_jawi": q["question_jawi"]},
                                           f"{file_id}_q{n}", "exercise_book", [p["page"]], related_topic_id=topic))
            if job:
                job.progress(done, len(items), f"Writing the answer and rubric of question {done} of {len(items)}")
    qfile = draft / "questions" / s / f"{file_id}.json"
    qfile.parent.mkdir(parents=True, exist_ok=True)
    qfile.write_text(json.dumps({"topic_id": file_id, "subject": s, "book_id": rec["id"], "questions": questions,
                                 "skipped": skipped}, indent=2, ensure_ascii=False), encoding="utf-8")


def process(book_id: str, job=None) -> dict:
    """Transcribe an uploaded book and write its drafts (run as a background job)."""
    with _lock:
        rec = _read(book_id)
        if rec["origin"] != "upload" or rec["status"] not in ("uploaded", "failed", "draft"):
            raise LibraryError("Only an uploaded book that is not published can be processed")
        rec.update(status="processing", error="", cost=0.0)
        _write(rec)
    folder = _folder(book_id)
    try:
        images = _render_pages(folder, job)
        results: list[dict] = [{} for _ in images]
        with ThreadPoolExecutor(max_workers=4) as ex:
            futures = {ex.submit(_ask_page, rec, img, i, len(images)): i for i, img in enumerate(images, 1)}
            for done, fut in enumerate(as_completed(futures), 1):
                results[futures[fut] - 1] = fut.result()
                if job:
                    job.progress(done, len(images), f"Reading page {done} of {len(images)} with {TRANSCRIBER}")
        (folder / "pages" / "transcripts.json").write_text(json.dumps(results, indent=1, ensure_ascii=False), encoding="utf-8")
        rec["cost"] = round(sum(r.get("cost", 0.0) for r in results), 5)
        draft = folder / "draft"
        shutil.rmtree(draft, ignore_errors=True)
        (_draft_textbook if rec["kind"] == "textbook" else _draft_exercise)(rec, results, draft, job)
        rec.update(status="draft", cost=round(rec["cost"], 5), processed=_now())
    except Exception as e:
        rec.update(status="failed", error=f"{type(e).__name__}: {e}"[:400])
        _write(rec)
        raise
    _write(rec)
    return get_book(book_id)


# ------------------------------------------------------------------ drafts: check and edit
def _draft_path(book_id: str, rel: str) -> Path:
    base = (_folder(book_id) / "draft").resolve()
    p = (base / rel).resolve()
    if base not in p.parents or p.suffix not in (".md", ".json") or len(p.relative_to(base).parts) != 3:
        raise LibraryError("unknown draft file")
    return p


def check_note(text: str, rel: str) -> list[str]:
    try:
        note = parse_note(text)
    except (ValueError, yaml.YAMLError) as e:
        return [f"front-matter: {e}"]
    m, errors = note.meta, []
    subject, stem = Path(rel).parent.name, Path(rel).stem      # rel = notes/<subject>/<topic_id>.md
    if missing := NOTE_KEYS - m.keys():
        errors.append(f"front-matter is missing {sorted(missing)}")
    if m.get("id") != stem:
        errors.append(f"id must be {stem!r}")
    if m.get("subject") != subject:
        errors.append(f"subject must be {subject!r}")
    if "\n## " not in "\n" + note.body:
        errors.append("the note needs at least one '## ' section")
    return errors


def check_questions(text: str, rel: str, topics: set[str]) -> list[str]:
    try:
        d = json.loads(text)
    except json.JSONDecodeError as e:
        return [f"JSON: {e}"]
    errors, seen = [], set()
    if d.get("topic_id") != Path(rel).stem:
        errors.append(f"topic_id must be {Path(rel).stem!r}")
    for q in d.get("questions", []):
        qid = q.get("id", "?")
        if qid in seen:
            errors.append(f"{qid}: id used twice")
        seen.add(qid)
        if q.get("level") not in (1, 2, 3):
            errors.append(f"{qid}: level must be 1, 2 or 3")
        if q.get("type") not in QUESTION_TYPES:
            errors.append(f"{qid}: type must be short, structured or essay")
        if not str(q.get("question_rumi", "")).strip() or not str(q.get("reference_answer_rumi", "")).strip():
            errors.append(f"{qid}: question_rumi and reference_answer_rumi are needed")
        rubric = q.get("rubric") or []
        if not rubric or any(not r.get("criterion") or not isinstance(r.get("marks"), int) or r["marks"] < 1 for r in rubric):
            errors.append(f"{qid}: every rubric criterion needs a text and marks (a whole number, 1 or more)")
        elif q.get("max_marks") != sum(r["marks"] for r in rubric):
            errors.append(f"{qid}: max_marks must be the sum of the rubric marks ({sum(r['marks'] for r in rubric)})")
        topic = q.get("related_topic_id") or d.get("topic_id")
        if topic not in topics:
            errors.append(f"{qid}: topic {topic!r} is not in the syllabus or in this book")
    if not d.get("questions"):
        errors.append("there are no questions")
    return errors


_ARABIC = re.compile(r"[؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿]")
_LATIN = re.compile(r"[A-Za-z]")


def warnings_for(text: str) -> list[str]:
    """What a teacher should look at first: unclear words and Jawi words broken by Latin letters."""
    out = []
    if n := text.count("TIDAK JELAS"):
        out.append(f"{n} unclear word(s) marked [TIDAK JELAS]: compare with the page")
    mixed = sorted({w for w in re.split(r"[\s,.;:!?؟،()\[\]\"'|*]+", text) if _ARABIC.search(w) and _LATIN.search(w)})
    if mixed:
        out.append(f"{len(mixed)} Jawi word(s) contain Latin letters: {', '.join(mixed[:6])}")
    return out


def _book_topics(book_id: str) -> set[str]:
    return _active_topics() | {p.stem for p in (_folder(book_id) / "draft" / "notes").glob("*/*.md")}


def drafts(book_id: str) -> list[dict]:
    rec = _read(book_id)
    base, topics, out = _folder(book_id) / "draft", _book_topics(book_id), []
    for p in sorted(base.glob("notes/*/*.md")):
        rel, text = p.relative_to(base).as_posix(), p.read_text(encoding="utf-8")
        m = _note_meta(p)
        out.append({"path": rel, "kind": "note", "title": m.get("topic_rumi", p.stem), "pages": m.get("pdf_pages") or [],
                    "verified": bool(m.get("verified")), "content": text, "warnings": warnings_for(text),
                    "errors": check_note(text, rel)})
    for p in sorted(base.glob("questions/*/*.json")):
        rel, text = p.relative_to(base).as_posix(), p.read_text(encoding="utf-8")
        d = _question_file(p)
        out.append({"path": rel, "kind": "questions", "title": d.get("topic_id", p.stem), "count": len(d.get("questions", [])),
                    "skipped": d.get("skipped", []), "content": text, "warnings": warnings_for(text),
                    "errors": check_questions(text, rel, topics)})
    return [x | {"book_status": rec["status"]} for x in out]


def save_draft(book_id: str, rel: str, content: str) -> dict:
    with _lock:
        rec = _read(book_id)
        if rec["status"] != "draft":
            raise LibraryError("Only a book in draft can be edited (remove it first if it is published)")
        p = _draft_path(book_id, rel)
        if not p.exists():
            raise LibraryError("unknown draft file")
        p.write_text(content, encoding="utf-8")
    errors = check_note(content, rel) if p.suffix == ".md" else check_questions(content, rel, _book_topics(book_id))
    return {"path": rel, "errors": errors}


def delete_draft(book_id: str, rel: str) -> None:
    with _lock:
        if _read(book_id)["status"] != "draft":
            raise LibraryError("Only a book in draft can be edited")
        p = _draft_path(book_id, rel)
        p.unlink(missing_ok=True)
        if p.suffix == ".md":     # a topic's practice questions go with it
            _draft_path(book_id, f"questions/{p.parent.name}/{p.stem}.json").unlink(missing_ok=True)


# ------------------------------------------------------------------ publish / remove / restore / delete
def _file_questions(base: Path, rels: list[str]) -> set[str]:
    return {q["id"] for r in rels for q in _question_file(base / r).get("questions", [])}


def _file_topics(rels: list[str]) -> set[str]:
    return {Path(r).stem for r in rels}


def _move_in(rec: dict, src_base: Path, copy: bool) -> dict:
    """Put a book's files into data/ (from its drafts or its removed folder) and re-index them."""
    from .kb.update import sync
    from .questions import load_questions

    notes = sorted(p.relative_to(src_base / "notes").as_posix() for p in (src_base / "notes").glob("*/*.md"))
    qfiles = sorted(p.relative_to(src_base / "questions").as_posix() for p in (src_base / "questions").glob("*/*.json"))
    if not notes and not qfiles:
        raise LibraryError("This book has no notes or questions to add")
    clash = [n for n in notes if (_kn() / n).exists()] + [q for q in qfiles if (_qn() / q).exists()]
    if clash:
        raise LibraryError(f"Already in the syllabus: {', '.join(clash[:5])}. Remove the book that has them first.")
    existing = set(load_questions())
    dup = _file_questions(src_base / "questions", qfiles) & existing
    if dup:
        raise LibraryError(f"Question ids already used: {', '.join(sorted(dup)[:5])}")
    for kind, rels, root in (("notes", notes, _kn()), ("questions", qfiles, _qn())):
        for r in rels:
            dst = root / r
            dst.parent.mkdir(parents=True, exist_ok=True)
            (shutil.copy2 if copy else shutil.move)(src_base / kind / r, dst)
    rec.update(status="active", files={"notes": notes, "questions": qfiles})
    _write(rec)
    index = sync(_file_topics(notes), _file_questions(_qn(), qfiles))
    runtime.update(syllabus_changed_at=_now())
    return index


def publish(book_id: str) -> dict:
    with _lock:
        rec = _read(book_id)
        if rec["status"] != "draft":
            raise LibraryError("Only a book in draft can be published")
        problems = [f"{d['path']}: {e}" for d in drafts(book_id) for e in d["errors"]]
        if problems:
            raise LibraryError("Fix these first: " + "; ".join(problems[:6]))
        index = _move_in(rec, _folder(book_id) / "draft", copy=True)
        rec["published"] = _now()
        _write(rec)
    return get_book(book_id) | {"index": index}


def remove(book_id: str) -> dict:
    from .kb.update import sync

    with _lock:
        rec = _read(book_id)
        if rec["status"] != "active":
            raise LibraryError("Only a book in the syllabus can be removed")
        out = _folder(book_id) / "removed"
        qids = _file_questions(_qn(), rec["files"]["questions"])
        for kind, root in (("notes", _kn()), ("questions", _qn())):
            for r in rec["files"][kind]:
                src = root / r
                if src.exists():
                    (out / kind / r).parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(src, out / kind / r)
        rec.update(status="removed", removed=_now())
        _write(rec)
        index = sync(_file_topics(rec["files"]["notes"]), qids)
        runtime.update(syllabus_changed_at=_now())
    return get_book(book_id) | {"index": index}


def restore(book_id: str) -> dict:
    with _lock:
        rec = _read(book_id)
        if rec["status"] != "removed":
            raise LibraryError("Only a removed book can be restored")
        src = _folder(book_id) / "removed"
        index = _move_in(rec, src, copy=False)
        shutil.rmtree(src, ignore_errors=True)
        rec["restored"] = _now()
        _write(rec)
    return get_book(book_id) | {"index": index}


def delete(book_id: str) -> None:
    """Delete an uploaded book that is not in the syllabus (its working files go too)."""
    with _lock:
        rec = _read(book_id)
        if rec["origin"] != "upload" or rec["status"] in ("active", "processing"):
            raise LibraryError("Only an uploaded book that is not in the syllabus can be deleted")
        shutil.rmtree(_folder(book_id))


def page_image(book_id: str, page: int) -> Path:
    p = _folder(book_id) / "pages" / f"page_{int(page):03d}.jpg"
    if not p.exists():
        raise LibraryError("no such page")
    return p
