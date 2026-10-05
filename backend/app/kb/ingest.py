"""Build the vector knowledge base from scratch.

    notes  -> chunks -> bge-m3 embeddings -> ChromaDB `kafa_notes`
    questions' reference answers           -> ChromaDB `kafa_refs`

Run from FypNabil/:
    .venv\\Scripts\\python -m backend.app.kb.ingest
Rebuilds both collections every time (idempotent). Writes a manifest to
storage/kb_manifest.json.
"""
from __future__ import annotations

import json
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from ..config import get_settings
from ..embeddings import embed
from ..questions import load_questions
from .chunking import chunk_note, load_note
from .store import NOTES, REFS, reset_collection

BATCH = 64


def _add(collection, ids, docs, metas) -> None:
    for i in range(0, len(ids), BATCH):
        sl = slice(i, i + BATCH)
        collection.add(ids=ids[sl], documents=docs[sl], metadatas=metas[sl], embeddings=embed(docs[sl]))


def build_notes() -> dict:
    s = get_settings()
    chunks = [c for f in sorted(Path(s.knowledge_dir).glob("*/*.md")) for c in chunk_note(load_note(f))]
    col = reset_collection(NOTES)
    _add(col, [c.id for c in chunks], [c.text for c in chunks], [c.metadata for c in chunks])
    return {
        "chunks": len(chunks),
        "topics": len({c.metadata["topic_id"] for c in chunks}),
        "per_subject": dict(Counter(c.metadata["subject"] for c in chunks)),
        "verified_chunks": sum(c.metadata["verified"] for c in chunks),
    }


def ref_document(q: dict) -> str:
    """Reference answer text used for similarity scoring (Rumi + Jawi)."""
    parts = [q.get("reference_answer_rumi", ""), q.get("reference_answer_jawi", "")]
    return "\n".join(p for p in parts if p).strip()


def build_refs() -> dict:
    qs = load_questions()
    ids, docs, metas = [], [], []
    for qid, q in qs.items():
        doc = ref_document(q)
        if not doc:
            continue
        ids.append(qid)
        docs.append(doc)
        metas.append({"question_id": qid, "topic_id": q["topic_id"], "subject": q["subject"],
                      "level": q["level"], "max_marks": q["max_marks"]})
    col = reset_collection(REFS)
    _add(col, ids, docs, metas)
    return {"reference_answers": len(ids)}


def main() -> None:
    t0 = time.perf_counter()
    manifest = {"built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "embed_model": get_settings().embed_model_id}
    manifest["notes"] = build_notes()
    print(f"notes: {manifest['notes']}")
    manifest["refs"] = build_refs()
    print(f"refs:  {manifest['refs']}")
    manifest["seconds"] = round(time.perf_counter() - t0, 1)
    out = get_settings().chroma_dir.parent / "kb_manifest.json"
    out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"done in {manifest['seconds']}s -> {out}")


if __name__ == "__main__":
    main()
