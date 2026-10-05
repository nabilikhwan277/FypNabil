"""Test doubles: a bag-of-words embedder and a scripted LLM."""
from __future__ import annotations

import hashlib
import math

from backend.app.assess.matching import toks

DIM = 256


def fake_embed(texts: list[str]) -> list[list[float]]:
    """Normalised hashed bag-of-words. Shared words -> higher cosine."""
    out = []
    for t in texts:
        v = [0.0] * DIM
        for tok in toks(t):
            v[int(hashlib.md5(tok.encode()).hexdigest(), 16) % DIM] += 1.0
        n = math.sqrt(sum(x * x for x in v)) or 1.0
        out.append([x / n for x in v])
    return out


class ScriptedLLM:
    """Returns queued replies in order; records every prompt."""

    def __init__(self, *replies: str, default: str = '{"met": "tidak", "reason": "-"}') -> None:
        self.replies = list(replies)
        self.default = default
        self.prompts: list[str] = []

    def __call__(self, messages: list[dict], max_new_tokens: int) -> str:
        self.prompts.append(messages[-1]["content"])
        return self.replies.pop(0) if self.replies else self.default


class FakeHit:
    def __init__(self, id: str, text: str, topic_id: str, section: str = "Pengertian", score: float = 0.9):
        self.id, self.text, self.score = id, text, score
        self.metadata = {"topic_id": topic_id, "section": section}

    @property
    def topic_id(self) -> str:
        return self.metadata["topic_id"]
