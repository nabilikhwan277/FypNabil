"""Loads the local LLM once and exposes a simple chat-generate function."""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from .config import get_settings

_DTYPES = {"float16": torch.float16, "bfloat16": torch.bfloat16, "float32": torch.float32}


def resolve_device(pref: str) -> str:
    if pref == "auto":
        return "cuda" if torch.cuda.is_available() else "cpu"
    return pref


@dataclass
class Generation:
    text: str
    latency_ms: int
    prompt_tokens: int
    new_tokens: int


class LLM:
    """Wrapper around the Hugging Face causal LM. One instance per process;
    generate() is serialised with a lock because there is a single GPU model."""

    def __init__(self) -> None:
        s = get_settings()
        self.model_id = s.llm_model_id
        self.device = resolve_device(s.device)
        dtype = _DTYPES[s.llm_dtype] if self.device == "cuda" else torch.float32
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_id, cache_dir=s.hf_cache_dir)
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_id, torch_dtype=dtype, cache_dir=s.hf_cache_dir
        ).to(self.device)
        self.model.eval()
        if self.tokenizer.pad_token_id is None:
            self.tokenizer.pad_token_id = self.tokenizer.eos_token_id
        self._lock = threading.Lock()
        self._label_ids: dict = {}

    @torch.inference_mode()
    def generate(
        self,
        messages: list[dict[str, str]],
        max_new_tokens: int = 200,
        temperature: float = 0.0,
        repetition_penalty: float = 1.0,
        no_repeat_ngram_size: int = 0,
    ) -> Generation:
        """Greedy by default. Repetition controls are OFF by default because HF's
        repetition_penalty also penalises prompt tokens, which corrupts words the
        model must copy (e.g. 'harakat' -> 'haritam'). Enable them only for long
        free-text output (feedback) where the 1B model can loop."""
        inputs = self.tokenizer.apply_chat_template(
            messages, add_generation_prompt=True, return_tensors="pt", return_dict=True
        ).to(self.device)
        kwargs = dict(
            max_new_tokens=max_new_tokens,
            pad_token_id=self.tokenizer.pad_token_id,
            repetition_penalty=repetition_penalty,
        )
        if no_repeat_ngram_size:
            kwargs["no_repeat_ngram_size"] = no_repeat_ngram_size
        if temperature > 0:
            kwargs.update(do_sample=True, temperature=temperature, top_p=0.9)
        else:
            kwargs.update(do_sample=False, temperature=None, top_p=None)
        with self._lock:
            t0 = time.perf_counter()
            out = self.model.generate(**inputs, **kwargs)
            ms = int((time.perf_counter() - t0) * 1000)
        prompt_len = inputs["input_ids"].shape[1]
        new_ids = out[0, prompt_len:]
        text = self.tokenizer.decode(new_ids, skip_special_tokens=True).strip()
        return Generation(text=text, latency_ms=ms, prompt_tokens=prompt_len, new_tokens=len(new_ids))


    @torch.inference_mode()
    def label_probs(self, messages: list[dict[str, str]], labels: dict[str, list[str]]) -> dict[str, float]:
        """Probability of each label as the model's FIRST answer token.

        One forward pass, no sampling: far more stable than parsing generated
        text from a 1B model. `labels` maps a label to surface variants
        (e.g. {"ya": ["Ya", "YA"]}); the first-token logits of the variants are
        pooled (logsumexp) and the labels renormalised to sum to 1. Token ids
        shared by two labels are dropped so the classes stay distinct.
        """
        key = tuple((k, tuple(v)) for k, v in labels.items())
        ids = self._label_ids.get(key)
        if ids is None:
            first: dict[str, set[int]] = {}
            for lab, variants in labels.items():
                first[lab] = {self.tokenizer.encode(v, add_special_tokens=False)[0] for v in variants}
            shared = {i for a in first for b in first if a != b for i in first[a] & first[b]}
            ids = {lab: sorted(s - shared) for lab, s in first.items()}
            self._label_ids[key] = ids
        inputs = self.tokenizer.apply_chat_template(
            messages, add_generation_prompt=True, return_tensors="pt", return_dict=True
        ).to(self.device)
        with self._lock:
            logits = self.model(**inputs).logits[0, -1].float()
        logp = torch.log_softmax(logits, dim=-1)
        raw = torch.stack([torch.logsumexp(logp[i], 0) for i in ids.values()])
        probs = torch.softmax(raw, dim=0).tolist()
        return dict(zip(ids.keys(), probs))


_llm: LLM | None = None
_llm_lock = threading.Lock()


def get_llm() -> LLM:
    global _llm
    if _llm is None:
        with _llm_lock:
            if _llm is None:
                _llm = LLM()
    return _llm


def llm_loaded() -> bool:
    return _llm is not None
