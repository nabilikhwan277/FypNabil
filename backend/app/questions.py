"""Load the question bank (data/questions/<subject>/<topic_id>.json)."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from .config import get_settings


def _effective_topic(q: dict, file_topic: str) -> str:
    # Latihan (textbook exercise) files span many topics; each question says which.
    return q.get("related_topic_id") or file_topic


@lru_cache
def load_questions() -> dict[str, dict]:
    """Return {question_id: question} with 'topic_id', 'subject' and
    'source_file' added to every question."""
    out: dict[str, dict] = {}
    root = Path(get_settings().questions_dir)
    for path in sorted(root.glob("*/*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for q in data["questions"]:
            out[q["id"]] = {
                **q,
                "topic_id": _effective_topic(q, data["topic_id"]),
                "subject": data["subject"],
                "source_file": data["topic_id"],
            }
    return out


def load_split(name: str) -> list[str]:
    path = get_settings().knowledge_dir.parent / "splits" / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8"))["ids"]
