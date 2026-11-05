"""Helper script to inspect SQLite and ChromaDB databases.

Usage:
    .venv\\Scripts\\python scripts\\inspect_db.py sqlite
    .venv\\Scripts\\python scripts\\inspect_db.py chroma
    .venv\\Scripts\\python scripts\\inspect_db.py all
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import chromadb

import io

# Force utf-8 stdout on Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SQLITE_PATH = Path("storage/kafa.db")
CHROMA_DIR = Path("storage/chroma")


def inspect_sqlite() -> None:
    print("\n" + "=" * 50)
    print(" [SQLITE DATABASE] storage/kafa.db")
    print("=" * 50)

    if not SQLITE_PATH.exists():
        print("[-] SQLite file not found at", SQLITE_PATH)
        return

    conn = sqlite3.connect(SQLITE_PATH)
    cur = conn.cursor()

    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [r[0] for r in cur.fetchall()]
    print(f"Tables found ({len(tables)}): {', '.join(tables)}\n")

    for tbl in tables:
        cur.execute(f"SELECT COUNT(*) FROM {tbl};")
        cnt = cur.fetchone()[0]
        print(f"--- Table: {tbl} (Total rows: {cnt}) ---")

        # Show first 2 sample rows
        cur.execute(f"SELECT * FROM {tbl} LIMIT 2;")
        rows = cur.fetchall()
        col_names = [desc[0] for desc in cur.description]
        if rows:
            print(f"    Columns: {', '.join(col_names)}")
            for idx, row in enumerate(rows, 1):
                clean_row = [str(val)[:50] + "..." if isinstance(val, str) and len(str(val)) > 50 else val for val in row]
                print(f"    Row {idx}: {clean_row}")
        print()

    conn.close()


def inspect_chroma() -> None:
    print("\n" + "=" * 50)
    print(" [CHROMADB VECTOR STORE] storage/chroma")
    print("=" * 50)

    if not CHROMA_DIR.exists():
        print("[-] ChromaDB directory not found at", CHROMA_DIR)
        return

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    colls = client.list_collections()
    print(f"Collections found ({len(colls)}): {[c.name for c in colls]}\n")

    for col in colls:
        cnt = col.count()
        print(f"--- Collection: '{col.name}' (Total documents: {cnt}) ---")
        if cnt > 0:
            sample = col.peek(limit=2)
            for idx, (doc_id, doc_text, meta) in enumerate(zip(sample["ids"], sample["documents"], sample["metadatas"]), 1):
                title = meta.get("topic_rumi") or meta.get("subject") or "N/A"
                section = meta.get("section") or "N/A"
                pages = meta.get("book_pages") or meta.get("pdf_pages") or "N/A"
                preview = (doc_text.replace("\n", " ")[:80] + "...") if doc_text else ""
                print(f"    Doc {idx} [ID: {doc_id}]:")
                print(f"        Topic: {title} | Section: {section} | Pages: {pages}")
                print(f"        Content: {preview}")
        print()


def main() -> None:
    mode = sys.argv[1].lower() if len(sys.argv) > 1 else "all"
    if mode in ("sqlite", "all"):
        inspect_sqlite()
    if mode in ("chroma", "all"):
        inspect_chroma()


if __name__ == "__main__":
    main()
