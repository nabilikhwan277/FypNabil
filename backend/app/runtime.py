"""Settings the admin changes while the system runs, kept in storage/runtime_settings.json (git-ignored).

They survive a restart and override the .env defaults: the Qwen link on Google Colab (remote_llm.py),
the live marking system (live_config.py) and when the syllabus last changed (library.py).
"""
from __future__ import annotations

import json
import threading

from .config import get_settings

_lock = threading.Lock()


def _path():
    return get_settings().sqlite_path.parent / "runtime_settings.json"


def load() -> dict:
    try:
        return json.loads(_path().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def update(**values) -> dict:
    """Set the given keys (None removes a key) and return all settings."""
    with _lock:
        d = load()
        for k, v in values.items():
            if v is None:
                d.pop(k, None)
            else:
                d[k] = v
        p = _path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(d, indent=1, ensure_ascii=False), encoding="utf-8")
    return d
