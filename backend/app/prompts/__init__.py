"""Prompt templates (plain text, str.format placeholders)."""
from functools import lru_cache
from pathlib import Path

_DIR = Path(__file__).resolve().parent


@lru_cache
def load(name: str) -> str:
    return (_DIR / f"{name}.txt").read_text(encoding="utf-8")


def render(name: str, **values) -> str:
    return load(name).format(**values)
