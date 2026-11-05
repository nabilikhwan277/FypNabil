"""Describe the system's data stores for the report (experiment plan Phase 5): writes docs/database.md.

Read-only: ChromaDB and SQLite are opened without changing them. Pupil records are described by their structure
and row counts only (no names, answers or other personal values). Secrets (.env, storage/admin_secret, the Colab
key in storage/runtime_settings.json) are named, never read out.

Usage (from FypNabil/): .venv\\Scripts\\python scripts\\describe_db.py
"""
from __future__ import annotations

import json
import re
import sqlite3
import statistics
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import chromadb
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.config import get_settings  # noqa: E402
from backend.app.kb.chunking import MAX_CHARS, MIN_CHARS  # noqa: E402
from backend.app.kb.store import NOTES, REFS  # noqa: E402
from backend.app.memory import db as memdb  # noqa: E402

OUT = ROOT / "docs" / "database.md"

COLUMN_NOTES = {
    "students": {
        "id": "Pupil number", "name": "Name typed at sign-in", "kelas": "Class, e.g. 5 Bestari",
        "avatar": "Chosen animal emoji", "script_pref": "Preferred script (rumi / jawi)",
        "created_at": "First sign-in (UTC, ISO 8601)"},
    "attempts": {
        "id": "Attempt number", "student_id": "→ students.id", "question_id": "Question id (data/questions)",
        "topic_id": "Topic id (note file name)", "subject": "fiqh / jawi / tajwid", "level": "Tahap 1–3",
        "answer": "The pupil's answer text", "score": "Marks given", "max_marks": "Marks available",
        "percent": "score / max_marks × 100", "criteria_json": "Per-criterion result (below)",
        "feedback_json": "The feedback shown to the pupil (below)", "react_trace_json": "The ReAct steps (below)",
        "latency_ms": "Marking time", "created_at": "When answered (UTC)"},
    "mistakes": {
        "student_id": "→ students.id", "topic_id": "Topic id", "criterion": "Rubric criterion not met",
        "count": "Times missed", "last_seen": "Last time missed (UTC)"},
    "topic_mastery": {
        "student_id": "→ students.id", "topic_id": "Topic id", "subject": "fiqh / jawi / tajwid",
        "mastery": "0–1, moving average of the scores", "attempts": "Answers in this topic",
        "level_unlocked": "Highest open Tahap (1–3)", "updated_at": "Last change (UTC)"},
    "progress": {
        "student_id": "→ students.id", "xp": "Experience points", "streak_days": "Days in a row with an answer",
        "last_active_date": "Last day with an answer (local date)", "badges_json": "Badge ids earned (list)"},
}


def size(p: Path) -> int:
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) if p.is_dir() else p.stat().st_size


def human(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return ""


def types(values) -> str:
    return " / ".join(sorted({type(v).__name__.replace("str", "string").replace("bool", "boolean") for v in values}))


def describe_collection(client, name: str, what: str, id_rule: str) -> tuple[list[str], dict]:
    col = client.get_collection(name)
    got = col.get(include=["metadatas", "documents"])
    first = col.get(ids=[sorted(got["ids"])[0]], include=["metadatas", "documents", "embeddings"])
    cfg = (col.configuration or {}).get("hnsw") or {}
    metas, docs = got["metadatas"], got["documents"]
    fields = sorted({k for m in metas for k in m})
    lengths = [len(d) for d in docs]
    by_subject = Counter(m["subject"] for m in metas)
    md = [f"### `{name}`", "", what, "",
          "| Property | Value |", "|---|---|",
          f"| Records | {col.count()} |",
          f"| Per subject | {', '.join(f'{s} {n}' for s, n in sorted(by_subject.items()))} |",
          f"| ID | {id_rule} (e.g. `{sorted(got['ids'])[0]}`) |",
          f"| Vector | {len(first['embeddings'][0])} numbers (bge-m3), supplied by the app |",
          f"| Index | HNSW, {cfg.get('space', '?')} distance (ef_construction {cfg.get('ef_construction')}, "
          f"ef_search {cfg.get('ef_search')}, max_neighbors {cfg.get('max_neighbors')}) |",
          f"| Document length | {min(lengths)}–{max(lengths)} characters (median {statistics.median(lengths):.0f}) |",
          "", "Metadata fields:", "", "| Field | Type | Example |", "|---|---|---|"]
    ex_meta = first["metadatas"][0]
    md += [f"| `{k}` | {types(m[k] for m in metas if k in m)} | `{ex_meta.get(k, '')}` |" for k in fields]
    doc = first["documents"][0]
    md += ["", f"Example record `{first['ids'][0]}` (document text, first 400 characters):", "", "```text",
           doc[:400] + ("…" if len(doc) > 400 else ""), "```", ""]
    return md, {"metas": metas, "by_subject": by_subject}


def chroma_section() -> list[str]:
    s = get_settings()
    client = chromadb.PersistentClient(path=str(s.chroma_dir), settings=chromadb.Settings(anonymized_telemetry=False))
    manifest = json.loads((s.chroma_dir.parent / "kb_manifest.json").read_text(encoding="utf-8"))
    notes_md, notes = describe_collection(
        client, NOTES,
        f"Textbook notes for retrieval (RAG). Each topic note in `data/knowledge/` is split into one chunk per `##` "
        f"section; a section longer than {MAX_CHARS} characters is split at paragraph breaks (the last paragraph is "
        f"repeated as overlap) and sections shorter than {MIN_CHARS} characters are dropped. Each chunk starts with "
        f"`Topik: <Rumi> | <Jawi>` and `Bahagian: <section>`, so it still makes sense on its own.",
        "`<topic_id>::s<section, 2 digits>p<part>`")
    refs_md, _ = describe_collection(
        client, REFS,
        "Reference answers (Rumi + Jawi) of the questions, used by the B2 marker to measure how close a pupil's answer "
        "is to the expected answer (cosine similarity).",
        "the question id")
    topics = len({m["topic_id"] for m in notes["metas"]})
    verified = sum(bool(m.get("verified")) for m in notes["metas"])
    return [
        "## 1. ChromaDB: the vector store", "",
        f"- **Where:** `storage/chroma/` ({human(size(s.chroma_dir))}), ChromaDB {chromadb.__version__} `PersistentClient`, "
        "telemetry off.",
        f"- **Embeddings:** `{manifest['embed_model']}`, computed by the app (the collections have no embedding function "
        "of their own), so the same model embeds the stored text and the search query.",
        f"- **Built by:** `python -m backend.app.kb.ingest`, which rebuilds both collections from the files and writes "
        f"`storage/kb_manifest.json` (last build {manifest['built_at']}, {manifest['seconds']} s). New books added on "
        "the admin page are added to the same collections (`backend/app/kb/update.py`).",
        f"- **Coverage:** {topics} topics; {verified} of {len(notes['metas'])} chunks come from notes marked "
        "`verified` (checked by a teacher).", "",
        *notes_md, *refs_md,
    ]


def sqlite_section() -> list[str]:
    path = get_settings().sqlite_path
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY rowid")]
    md = ["## 2. SQLite: the pupil learning memory", "",
          f"- **Where:** `storage/kafa.db` ({human(size(path))}), Python's built-in `sqlite3` (`backend/app/memory/db.py`); "
          "the tables are created on first use.",
          "- **Privacy:** this document shows the structure and the number of rows only, never pupils' names or answers.",
          "- **Rules kept in the memory:**",
          f"  - Mastery per topic is a moving average of the percent score: the first answer sets it, then "
          f"mastery = {memdb.EMA_OLD} × old + {1 - memdb.EMA_OLD:.1f} × new.",
          f"  - The next Tahap opens after at least {memdb.UNLOCK_WINDOW} answers at the current Tahap with an average of "
          f"at least {memdb.UNLOCK_THRESHOLD:.0%} over the last {memdb.UNLOCK_WINDOW} (up to Tahap {memdb.MAX_LEVEL}).",
          f"  - A criterion missed {memdb.REPEAT_MIN} or more times in a topic is a repeated mistake; the feedback "
          "then warns the pupil.",
          "  - XP = 10 per star + 2 for trying; the streak counts days in a row with at least one answer.", "",
          "```mermaid", "erDiagram"]
    info = {t: con.execute(f"PRAGMA table_info({t})").fetchall() for t in tables}
    for t in tables:
        md.append(f"  {t} {{")
        md += [f"    {c[2] or 'TEXT'} {c[1]}{' PK' if c[5] else ''}{' FK' if c[1] == 'student_id' else ''}" for c in info[t]]
        md.append("  }")
    md += ['  students ||--o{ attempts : "answers"', '  students ||--o{ mistakes : "misses"',
           '  students ||--o{ topic_mastery : "learns"', '  students ||--|| progress : "earns"', "```", ""]
    for t in tables:
        rows = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        idx = [r[1] for r in con.execute(f"PRAGMA index_list({t})") if not r[1].startswith("sqlite_autoindex")]
        uniq = [r for r in con.execute(f"PRAGMA index_list({t})") if r[2] and r[1].startswith("sqlite_autoindex")]
        md += [f"### `{t}` ({rows} rows)", "", "| Column | Type | Rule | Meaning |", "|---|---|---|---|"]
        for c in info[t]:
            rule = ", ".join(x for x in ("primary key" if c[5] else "", "not null" if c[3] and not c[5] else "",
                                         f"default {c[4]}" if c[4] is not None else "") if x)
            md.append(f"| `{c[1]}` | {c[2]} | {rule or '–'} | {COLUMN_NOTES.get(t, {}).get(c[1], '')} |")
        extra = []
        if idx:
            extra.append(f"Index: {', '.join(f'`{i}`' for i in idx)}.")
        if t == "students" and uniq:
            extra.append("`(name, kelas)` is unique: signing in again with the same name and class returns the same pupil.")
        md += ["", *extra, ""] if extra else [""]
    row = con.execute("SELECT criteria_json, feedback_json, react_trace_json FROM attempts ORDER BY id DESC LIMIT 1").fetchone()
    if row:
        crit, fb, trace = (json.loads(x) for x in row)
        md += ["### JSON stored in `attempts` (field names only)", "",
               f"- `criteria_json`: a list, one object per rubric criterion: {', '.join(f'`{k}`' for k in (crit[0] if crit else {}))}.",
               f"- `feedback_json`: {', '.join(f'`{k}`' for k in fb)}.",
               f"- `react_trace_json`: a list of ReAct steps: {', '.join(f'`{k}`' for k in (trace[0] if trace else {}))}.", ""]
    con.close()
    return md


def keys_of(files: list[Path], pick) -> str:
    seen: Counter = Counter()
    for f in files:
        for obj in pick(f):
            seen.update(list(obj))  # the field names, in file order
    return ", ".join(f"`{k}`" for k in seen)


def front_matter(f: Path) -> list[dict]:
    m = re.match(r"^---\s*\n(.*?)\n---", f.read_text(encoding="utf-8"), re.S)
    return [yaml.safe_load(m.group(1))] if m else []


def files_section() -> list[str]:
    s = get_settings()
    notes = sorted(Path(s.knowledge_dir).glob("*/*.md"))
    qfiles = sorted(Path(s.questions_dir).rglob("*.json"))
    questions = [q for f in qfiles for q in json.loads(f.read_text(encoding="utf-8"))["questions"]]
    books = sorted(Path(s.books_dir).glob("*/book.json"))
    calls = (s.llm_log_path).read_text(encoding="utf-8").splitlines() if s.llm_log_path.exists() else []
    call_keys = next((list(json.loads(x)) for x in reversed(calls) if x.strip().startswith("{") and x.strip().endswith("}")), [])
    runtime = s.sqlite_path.parent / "runtime_settings.json"
    runtime_keys = list(json.loads(runtime.read_text(encoding="utf-8"))) if runtime.exists() else []
    cache = list(Path(s.llm_cache_dir).rglob("*.json")) if Path(s.llm_cache_dir).exists() else []
    ft = ROOT / "data" / "finetune" / "kafa_marker_sft.jsonl"
    mcq = sum(len(json.loads(f.read_text(encoding="utf-8"))) for f in (ROOT / "data" / "mcq").glob("*.json"))
    splits = {k: len(json.loads((ROOT / "data" / "splits" / f"{k}.json").read_text(encoding="utf-8"))["ids"]) for k in ("train", "test")}
    rows = [
        ("Topic notes", f"`data/knowledge/<subject>/*.md` ({len(notes)})",
         f"Markdown with a YAML header: {keys_of(notes, front_matter)}. The source of `kafa_notes`."),
        ("Questions", f"`data/questions/<subject>/*.json` ({len(qfiles)} files, {len(questions)} questions)",
         f"One file per topic: `topic_id`, `subject`, `questions`. A question has {keys_of(qfiles[:1], lambda f: json.loads(f.read_text(encoding='utf-8'))['questions'][:1])}; "
         f"each rubric criterion has `criterion`, `marks`, `keywords`. The source of `kafa_refs`."),
        ("Multiple-choice versions", f"`data/mcq/<subject>.json` ({mcq} questions)",
         "The A–D version of a question, keyed by question id: `stem_rumi`, `stem_jawi`, `options`, `answer`, "
         "`explanation_rumi`, `spelling`, and who generated and checked it."),
        ("Train / test split", "`data/splits/train.json`, `test.json`",
         f"The question ids in each split ({' / '.join(str(splits[k]) for k in ('train', 'test'))}), with the seed, "
         "test ratio and stratification used."),
        ("Evaluation sets", "`data/silver/`, `data/teacher/`",
         "Silver answers (AI-written paraphrases and programmatic answers) and the 50-answer teacher set with the teachers' marks."),
        ("Fine-tuning data", f"`data/finetune/kafa_marker_sft.jsonl` ({sum(1 for _ in ft.open(encoding='utf-8')) if ft.exists() else 0} lines)",
         "One chat example per line: `id`, `split`, `subject`, `kind`, `messages` (Phase 4)."),
        ("Books & syllabus", f"`storage/books/<book_id>/book.json` ({len(books)})",
         f"Fields {keys_of(books, lambda f: [json.loads(f.read_text(encoding='utf-8'))])}; an uploaded book also keeps its PDF, page images and drafts there."),
        ("Knowledge-base manifest", "`storage/kb_manifest.json`", "When the vector store was last built, with which model, and its counts."),
        ("Runtime settings", "`storage/runtime_settings.json`",
         f"Settings changed on the admin page while the system runs: {', '.join(f'`{k}`' for k in runtime_keys) or '–'} "
         "(the Colab key is a secret and is not shown here)."),
        ("LLM answer cache", f"`storage/llm_cache/` ({len(cache)} files, {human(size(Path(s.llm_cache_dir)))})",
         "One JSON file per (model, prompt): the same request is never paid twice."),
        ("LLM call log", f"`storage/llm_calls.jsonl` ({len(calls)} lines)", f"One line per call: {', '.join(f'`{k}`' for k in call_keys)}."),
        ("Experiment results", "`eval/results/`", "Every run, table and statistic in the report (JSON and Markdown)."),
        ("Secrets", "`.env`, `storage/admin_secret`",
         "The OpenRouter API key, the admin password and the key that signs admin sessions. Git-ignored; never shown or committed."),
    ]
    md = ["## 3. Files", "", "| What | Where | Content |", "|---|---|---|"]
    md += [f"| {a} | {b} | {c} |" for a, b, c in rows]
    md += ["", "`storage/` and `.env` are git-ignored: they hold pupil data, secrets and caches that are rebuilt or "
           "re-created on another machine.", ""]
    return md


def main() -> None:
    md = [
        "# KafAI UPKK: data stores", "",
        f"Generated by `scripts/describe_db.py` on {datetime.now(timezone.utc):%d %B %Y}, from the live stores "
        "(run it again after the data changes). The system keeps its data in three places:", "",
        "| Store | Technology | What it holds |", "|---|---|---|",
        "| Vector store | ChromaDB | Textbook note chunks and reference answers with their bge-m3 vectors (Section 1) |",
        "| Pupil memory | SQLite | Pupils, every answer, repeated mistakes, mastery per topic, XP and badges (Section 2) |",
        "| Files | Markdown, JSON, JSONL | Notes, questions, evaluation sets, books, settings, caches and logs (Section 3) |", "",
        "```mermaid", "flowchart LR",
        '  N["data/knowledge/*.md<br/>topic notes"] -->|"chunks + bge-m3"| C1[("kafa_notes")]',
        '  Q["data/questions/*.json<br/>questions + rubrics"] -->|"reference answers + bge-m3"| C2[("kafa_refs")]',
        '  B["Books page<br/>(admin)"] -->|"new notes and questions"| N & Q',
        '  C1 -->|"RAG: textbook evidence"| M["Marking pipeline<br/>rules, RAG, ReAct, LLM"]',
        '  C2 -->|"similarity (B2)"| M',
        '  M -->|"attempt, mistakes, mastery, XP"| S[("storage/kafa.db")]',
        '  S -->|"history, repeated mistakes"| M', "```", "",
        *chroma_section(), *sqlite_section(), *files_section(),
    ]
    OUT.write_text("\n".join(md), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({len(md)} lines)")


if __name__ == "__main__":
    main()
