"""One interface for every language model in the experiments.

API models go through OpenRouter (key in .env as KAFA_OPENROUTER_API_KEY); the
local model (M5) is the 4-bit Qwen loaded by llm.py. Every call:
  - uses fixed settings for repeatable marking (temperature 0, a seed where the
    provider supports it),
  - can ask for JSON that follows a schema, and is parsed here,
  - is cached on disk, so the same prompt and model are never paid for twice,
  - is logged (model, tokens, cost, time, success) to storage/llm_calls.jsonl,
  - stops before the API budget (KAFA_LLM_BUDGET_USD) would be exceeded.
Only question, rubric, textbook text and answer text are ever sent: no names,
classes or student IDs.
"""
from __future__ import annotations

import hashlib
import json
import re
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

import httpx

from .config import get_settings


@dataclass(frozen=True)
class ModelSpec:
    key: str
    id: str            # OpenRouter model name, or the Hugging Face id for the local model
    label: str
    provider: str      # anthropic | openai | meta | local (used to pick a judge from another provider)
    local: bool = False


MODELS: dict[str, ModelSpec] = {
    "haiku": ModelSpec("haiku", "anthropic/claude-haiku-5.5", "Claude Haiku 5.5", "anthropic"),
    "luna": ModelSpec("luna", "openai/gpt-6-luna", "GPT-6 Luna", "openai"),
    "llama": ModelSpec("llama", "meta-llama/llama-3.1-8b-instruct", "Llama 3.1 8B", "meta"),
    # open-weight model: runs on Google Colab (ngrok link) or on this laptop; never a paid API
    "qwen": ModelSpec("qwen", "local", "Qwen3-4B (open-weight)", "local", local=True),
    # Phase 3 open-weight models: only on Google Colab (notebooks/open_models_colab_server.ipynb)
    "fanar": ModelSpec("fanar", "QCRI/Fanar-1-9B-Instruct", "Fanar 9B (open-weight)", "qcri", local=True),
    "sealion": ModelSpec("sealion", "aisingapore/Gemma-SEA-LION-v3-9B-IT", "SEA-LION v3 9B (open-weight)", "aisingapore",
                         local=True),
    # Phase 4: Qwen3-4B fine-tuned with LoRA on Colab (notebooks/finetune_marker.ipynb), one entry per adapter of the grid
    **{f"qwen_ft_r{r}e{e}": ModelSpec(f"qwen_ft_r{r}e{e}", f"kafa/qwen3-4b-marker-r{r}e{e}",
                                      f"Qwen3-4B fine-tuned (LoRA r{r}, {e} epoch{'s' if e > 1 else ''})", "local", local=True)
       for r in (8, 16) for e in (1, 2)},
}


def open_model_problem(spec: ModelSpec) -> str:
    """Why this open-weight model cannot answer now ("" = it can). The Colab link must serve this very model,
    so another model's answers are never cached or saved under its name."""
    from . import remote_llm

    if remote_llm.endpoint() is None:
        if spec.id == "local" and get_settings().local_llm:
            return ""
        return f"Start the Colab notebook for {spec.label} and paste its link (Qwen on Colab tab)"
    served = remote_llm.served_model()
    if not served:
        return "The saved Colab link does not answer: start the notebook again and paste the new link"
    # the base Qwen: any Qwen build except a fine-tuned one, which has its own entry
    if spec.id == "local" and "qwen" in served.lower() and served not in {m.id for m in MODELS.values()}:
        return ""
    if served == spec.id:
        return ""
    return f"Colab is running {served}, not {spec.label}"


class LLMError(RuntimeError):
    pass


class BudgetExceeded(LLMError):
    pass


@dataclass
class Completion:
    text: str
    data: dict | None          # parsed JSON when a schema was requested (None if parsing failed)
    model: str
    tokens_in: int = 0
    tokens_out: int = 0
    cost: float = 0.0
    ms: int = 0
    cached: bool = False
    raw: dict = field(default_factory=dict, repr=False)

    def usage(self) -> dict:
        # "cost" = money paid now (a cache hit is free); "list_cost" = what the call costs at list price, which is
        # what a cost table must report (a cached rerun of the same system must not look free)
        return {"calls": 1, "tokens_in": self.tokens_in, "tokens_out": self.tokens_out,
                "cost": self.cost if not self.cached else 0.0, "list_cost": self.cost, "ms": self.ms,
                "cached": int(self.cached)}


_log_lock = threading.Lock()


def _log(rec: dict) -> None:
    path = get_settings().llm_log_path
    path.parent.mkdir(parents=True, exist_ok=True)
    with _log_lock, path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def spent_usd() -> float:
    """API money spent so far (cache hits cost nothing)."""
    path = get_settings().llm_log_path
    if not path.exists():
        return 0.0
    total = 0.0
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not r.get("cached"):
            total += float(r.get("cost") or 0.0)
    return round(total, 6)


def parse_json(text: str) -> dict | None:
    """First JSON object in a model reply (tolerates ```json fences and text around it)."""
    if not text:
        return None
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.S)
    try:
        v = json.loads(t)
        return v if isinstance(v, dict) else None
    except json.JSONDecodeError:
        pass
    start = t.find("{")
    while start != -1:
        depth, in_str, esc = 0, False, False
        for i in range(start, len(t)):
            ch = t[i]
            if in_str:
                esc = (ch == "\\") and not esc
                if ch == '"' and not esc:
                    in_str = False
                continue
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        v = json.loads(t[start:i + 1])
                        return v if isinstance(v, dict) else None
                    except json.JSONDecodeError:
                        break
        start = t.find("{", start + 1)
    return None


def _cache_path(payload: dict):
    key = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return get_settings().llm_cache_dir / key[:2] / f"{key}.json"


def _schema_instruction(schema: dict) -> str:
    return ("\n\nBalas dengan SATU objek JSON sahaja (tiada teks lain) yang mengikut skema ini:\n"
            + json.dumps(schema, ensure_ascii=False))


def complete(model: str, messages: list[dict], *, schema: dict | None = None, max_tokens: int = 900,
             temperature: float = 0.0, seed: int = 7, tag: str = "", use_cache: bool = True) -> Completion:
    """Run one chat completion. `model` is a key of MODELS ("haiku", "luna", "llama", "qwen")."""
    spec = MODELS[model]
    s = get_settings()
    msgs = [dict(m) for m in messages]
    if schema is not None:   # the instruction is also sent to API models: a belt-and-braces fallback
        msgs[0] = {**msgs[0], "content": msgs[0]["content"] + _schema_instruction(schema)}
    model_key = spec.id
    if spec.local:   # the same open model in 4-bit and 16-bit gives different answers: never mix them in the cache
        from . import remote_llm
        if problem := open_model_problem(spec):   # checked first: a dead link must not fall back to old cached answers
            raise LLMError(problem)
        if precision := remote_llm.served().get("precision"):
            model_key += f"@{precision}"
    payload = {"model": model_key, "messages": msgs, "schema": schema, "max_tokens": max_tokens,
               "temperature": temperature, "seed": seed}
    cpath = _cache_path(payload)
    if use_cache and cpath.exists():
        c = json.loads(cpath.read_text(encoding="utf-8"))
        comp = Completion(c["text"], parse_json(c["text"]) if schema else None, spec.id, c["tokens_in"],
                          c["tokens_out"], c["cost"], c["ms"], cached=True)
        _log({"ts": _now(), "model": spec.id, "tag": tag, "tokens_in": comp.tokens_in, "tokens_out": comp.tokens_out,
              "cost": comp.cost, "ms": 0, "ok": True, "cached": True})
        return comp

    t0 = time.perf_counter()
    try:
        if spec.local:
            comp = _local(spec, msgs, max_tokens)
        else:
            if spent_usd() >= s.llm_budget_usd:
                raise BudgetExceeded(f"API budget of ${s.llm_budget_usd:.2f} reached (spent ${spent_usd():.4f})")
            comp = _openrouter(spec, msgs, schema, max_tokens, temperature, seed)
    except Exception as e:
        _log({"ts": _now(), "model": spec.id, "tag": tag, "ok": False, "cached": False, "cost": 0.0,
              "ms": int((time.perf_counter() - t0) * 1000), "error": f"{type(e).__name__}: {e}"[:300]})
        raise
    comp.ms = int((time.perf_counter() - t0) * 1000)
    if schema is not None:
        comp.data = parse_json(comp.text)
    _log({"ts": _now(), "model": spec.id, "tag": tag, "tokens_in": comp.tokens_in, "tokens_out": comp.tokens_out,
          "cost": comp.cost, "ms": comp.ms, "ok": schema is None or comp.data is not None, "cached": False})
    if use_cache and (schema is None or comp.data is not None):   # never cache a broken reply
        cpath.parent.mkdir(parents=True, exist_ok=True)
        cpath.write_text(json.dumps({"text": comp.text, "tokens_in": comp.tokens_in, "tokens_out": comp.tokens_out,
                                     "cost": comp.cost, "ms": comp.ms}, ensure_ascii=False), encoding="utf-8")
    return comp


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _openrouter(spec: ModelSpec, msgs: list[dict], schema: dict | None, max_tokens: int,
                temperature: float, seed: int) -> Completion:
    s = get_settings()
    if not s.openrouter_api_key:
        raise LLMError("KAFA_OPENROUTER_API_KEY is not set in .env")
    body: dict = {"model": spec.id, "messages": msgs, "max_tokens": max_tokens, "temperature": temperature,
                  "seed": seed, "usage": {"include": True}}
    if schema is not None:
        body["response_format"] = {"type": "json_schema",
                                   "json_schema": {"name": "result", "strict": True, "schema": schema}}
    headers = {"Authorization": f"Bearer {s.openrouter_api_key}", "Content-Type": "application/json",
               "X-Title": "KAFA UPKK Learning Assistant (FYP)"}
    last: Exception | None = None
    for attempt in range(4):
        try:
            r = httpx.post(f"{s.openrouter_base_url}/chat/completions", json=body, headers=headers,
                           timeout=s.llm_timeout_s)
        except httpx.HTTPError as e:            # network problem or timeout: retry
            last = e
        else:
            if r.status_code == 200:
                d = r.json()
                if "choices" not in d:          # OpenRouter can return an error object with status 200
                    last = LLMError(str(d.get("error"))[:300])
                else:
                    msg = d["choices"][0]["message"]
                    u = d.get("usage") or {}
                    return Completion(msg.get("content") or "", None, d.get("model", spec.id),
                                      int(u.get("prompt_tokens") or 0), int(u.get("completion_tokens") or 0),
                                      float(u.get("cost") or 0.0), raw=d)
            elif r.status_code in (429, 500, 502, 503, 504):
                last = LLMError(f"HTTP {r.status_code}: {r.text[:200]}")
            else:                                # 400/401/402/403: retrying will not help
                raise LLMError(f"HTTP {r.status_code}: {r.text[:300]}")
        time.sleep(2 ** (attempt + 1))
    raise LLMError(f"{spec.id} failed after retries: {last}")


def _local(spec: ModelSpec, msgs: list[dict], max_tokens: int) -> Completion:
    """The open-weight model: on Google Colab when its link is saved, else on this laptop."""
    from . import remote_llm
    from .llm import generate_text

    if problem := open_model_problem(spec):
        raise LLMError(problem)
    on_colab = remote_llm.endpoint() is not None
    g = generate_text(msgs, max_new_tokens=max_tokens)
    served = remote_llm.served_model() if on_colab else get_settings().llm_model_id
    return Completion(g.text, None, f"{'colab' if on_colab else 'local'}:{served}", g.prompt_tokens, g.new_tokens,
                      0.0, g.latency_ms)


def call_log(since: str | None = None) -> list[dict]:
    path = get_settings().llm_log_path
    if not path.exists():
        return []
    out = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [r for r in out if since is None or r.get("ts", "") >= since]


def model_info() -> list[dict]:
    return [asdict(m) for m in MODELS.values()]
