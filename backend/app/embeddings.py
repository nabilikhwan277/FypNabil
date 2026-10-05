"""Loads the multilingual sentence-embedding model (bge-m3) once."""
from __future__ import annotations

import threading

from sentence_transformers import SentenceTransformer

from .config import get_settings
from .llm import resolve_device

_model: SentenceTransformer | None = None
_lock = threading.Lock()


def get_embedder() -> SentenceTransformer:
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                s = get_settings()
                device = resolve_device(s.device)
                m = SentenceTransformer(s.embed_model_id, device=device, cache_folder=str(s.hf_cache_dir))
                if device == "cuda":
                    m.half()  # fp16 to save VRAM (~1.1 GB)
                _model = m
    return _model


def embed(texts: list[str]) -> list[list[float]]:
    """Normalised embeddings, so dot product == cosine similarity."""
    vecs = get_embedder().encode(texts, normalize_embeddings=True, batch_size=16, show_progress_bar=False)
    return vecs.tolist()


def embedder_loaded() -> bool:
    return _model is not None
