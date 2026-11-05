"""Keep the knowledge base in step with the note and question files when the syllabus changes
(a book is published, removed or restored on the admin's Books & syllabus page).

Only the topics and questions that changed are re-indexed, so the live index is never empty:
  notes      chunks of the changed topics are deleted, then the current files are chunked and added
  questions  reference answers of the changed questions are deleted, then the current ones are added
The cached question bank, note metadata, catalogue and BM25 index are cleared afterwards.
`python -m backend.app.kb.ingest` still rebuilds everything from scratch.
"""
from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path

from ..config import get_settings
from .chunking import chunk_note, load_note
from .ingest import _add, ref_document
from .lexical import reset_bm25
from .store import NOTES, REFS, get_collection

_lock = threading.Lock()


def clear_caches() -> None:
    from .. import catalog, notes, questions

    questions.load_questions.cache_clear()
    notes.note_meta.cache_clear()
    catalog._topics.cache_clear()
    catalog._question_counts.cache_clear()
    reset_bm25()


def sync(topic_ids: set[str], question_ids: set[str]) -> dict:
    """Re-index these topics and questions from the files as they are now (missing files = removed)."""
    with _lock:
        clear_caches()
        from ..questions import load_questions

        notes_col, refs_col = get_collection(NOTES), get_collection(REFS)
        if topic_ids:
            notes_col.delete(where={"topic_id": {"$in": sorted(topic_ids)}})
        root = Path(get_settings().knowledge_dir)
        chunks = [c for t in sorted(topic_ids) for p in root.glob(f"*/{t}.md") for c in chunk_note(load_note(p))]
        if chunks:
            _add(notes_col, [c.id for c in chunks], [c.text for c in chunks], [c.metadata for c in chunks])

        qs = load_questions()
        changed = set(question_ids) | {qid for qid, q in qs.items() if q["topic_id"] in topic_ids}
        if changed:
            refs_col.delete(ids=sorted(changed))
        ids, docs, metas = [], [], []
        for qid in sorted(changed):
            q = qs.get(qid)
            if q and (doc := ref_document(q)):
                ids.append(qid)
                docs.append(doc)
                metas.append({"question_id": qid, "topic_id": q["topic_id"], "subject": q["subject"],
                              "level": q["level"], "max_marks": q["max_marks"]})
        if ids:
            _add(refs_col, ids, docs, metas)
        clear_caches()
        out = {"chunks": notes_col.count(), "reference_answers": refs_col.count(),
               "topics_changed": len(topic_ids), "questions_changed": len(changed),
               "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        manifest = get_settings().chroma_dir.parent / "kb_manifest.json"
        try:
            m = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            m = {}
        m["last_update"] = out
        manifest.write_text(json.dumps(m, indent=2, ensure_ascii=False), encoding="utf-8")
        return out
