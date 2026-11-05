"""Qwen served from Google Colab (notebooks/qwen_colab_server.ipynb) through an ngrok link.

The researcher pastes the link and key on the 📊 Penilaian page; they are saved in
storage/runtime_settings.json (git-ignored storage/), so they survive a restart and can be
changed without editing files. When a link is set, every local-model call (experiment model
"qwen" and the Tanya Bulan chat) goes to Colab and the laptop does not load Qwen at all.
The Colab server speaks the OpenAI chat-completions format.
"""
from __future__ import annotations

import time

import httpx

from . import runtime


class RemoteUnavailable(RuntimeError):
    pass


def endpoint() -> tuple[str, str] | None:
    """(base URL, key) of the Colab server, or None when Qwen should run locally."""
    d = runtime.load()
    url = (d.get("qwen_endpoint") or "").strip().rstrip("/")
    return (url, d.get("qwen_key", "")) if url else None


def normalize(url: str) -> str:
    """Base URL from whatever was pasted (a full /v1/chat/completions or /health path is fine too)."""
    url = url.strip().rstrip("/")
    for suffix in ("/v1/chat/completions", "/v1", "/health"):
        if url.endswith(suffix):
            url = url[: -len(suffix)]
    return url


def set_endpoint(url: str, key: str) -> None:
    runtime.update(qwen_endpoint=normalize(url), qwen_key=key.strip())


def clear_endpoint() -> None:
    runtime.update(qwen_endpoint=None, qwen_key=None)


def _headers(key: str) -> dict:
    # ngrok shows a browser warning page unless this header is present
    h = {"Content-Type": "application/json", "ngrok-skip-browser-warning": "true"}
    if key:
        h["Authorization"] = f"Bearer {key}"
    return h


def check(url: str | None = None, key: str | None = None) -> dict:
    """Ask the Colab server who it is. Returns {"ok": bool, "model": ..., "error": ...}."""
    if url is None:
        ep = endpoint()
        if ep is None:
            return {"ok": False, "error": "No Colab link saved"}
        url, key = ep
    try:
        r = httpx.get(f"{url.rstrip('/')}/health", headers=_headers(key or ""), timeout=20)
        if r.status_code == 401:
            return {"ok": False, "error": "Wrong key (401)"}
        r.raise_for_status()
        d = r.json()
        return {"ok": True, "model": d.get("model", ""), "gpu": d.get("gpu", ""),
                **{k: d[k] for k in ("precision", "gpu_memory_gb") if k in d}}
    except (httpx.HTTPError, ValueError) as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"[:200]}


_served: dict[str, dict] = {}


def served() -> dict:
    """What the saved Colab server runs: {"model", "gpu", "precision", ...} ({} if none or unreachable);
    asked once per link, because a new Colab session (or another model or GPU) always gives a new link."""
    ep = endpoint()
    if ep is None:
        return {}
    if ep[0] not in _served:
        status = check(*ep)
        if not status["ok"]:
            return {}
        _served[ep[0]] = status
    return _served[ep[0]]


def served_model() -> str:
    """The Hugging Face id the saved Colab server runs ("" if none or unreachable)."""
    return served().get("model", "")


def chat(messages: list[dict], max_tokens: int = 900, temperature: float = 0.0) -> dict:
    """One chat completion on the Colab server: {"text", "tokens_in", "tokens_out", "ms", "model"}."""
    ep = endpoint()
    if ep is None:
        raise RemoteUnavailable("No Colab link saved")
    url, key = ep
    t0 = time.perf_counter()
    last: Exception | None = None
    for attempt in range(3):
        try:
            r = httpx.post(f"{url}/v1/chat/completions", headers=_headers(key), timeout=300,
                           json={"model": "qwen", "messages": messages, "max_tokens": max_tokens,
                                 "temperature": temperature})
            if r.status_code == 200:
                d = r.json()
                u = d.get("usage") or {}
                return {"text": d["choices"][0]["message"].get("content") or "", "model": d.get("model", "colab"),
                        "tokens_in": int(u.get("prompt_tokens") or 0), "tokens_out": int(u.get("completion_tokens") or 0),
                        "ms": int((time.perf_counter() - t0) * 1000)}
            if r.status_code in (401, 403, 404):
                raise RemoteUnavailable(f"Colab server answered {r.status_code}: {r.text[:150]}")
            last = RemoteUnavailable(f"HTTP {r.status_code}: {r.text[:150]}")
        except httpx.HTTPError as e:
            last = e
        time.sleep(2 * (attempt + 1))
    raise RemoteUnavailable(f"Colab server not reachable: {last}")
