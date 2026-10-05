"""ChromaDB access. Two collections, both cosine distance, embeddings supplied
by us (bge-m3) rather than Chroma's default embedder."""
from __future__ import annotations

import threading

import chromadb

from ..config import get_settings

NOTES = "kafa_notes"   # textbook note chunks
REFS = "kafa_refs"     # reference answers, for similarity scoring

_client: chromadb.ClientAPI | None = None
_lock = threading.Lock()


def get_client() -> chromadb.ClientAPI:
    global _client
    if _client is None:
        with _lock:
            if _client is None:
                path = get_settings().chroma_dir
                path.mkdir(parents=True, exist_ok=True)
                _client = chromadb.PersistentClient(
                    path=str(path), settings=chromadb.Settings(anonymized_telemetry=False)
                )
    return _client


def get_collection(name: str):
    return get_client().get_or_create_collection(
        name=name, embedding_function=None, configuration={"hnsw": {"space": "cosine"}}
    )


def reset_collection(name: str):
    client = get_client()
    try:
        client.delete_collection(name)
    except Exception:  # noqa: BLE001 - collection did not exist
        pass
    return get_collection(name)
