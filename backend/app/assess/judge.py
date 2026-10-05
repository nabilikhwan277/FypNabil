"""Layer B: LLM judge for one rubric criterion, with an output guard.

The 1B model does not always return valid JSON, so the parser accepts JSON or
a leading verdict word, and one stricter retry is made before giving up.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Callable

from .. import prompts

Generate = Callable[[list[dict], int], str]  # (messages, max_new_tokens) -> text

VERDICTS = ("ya", "separa", "tidak")
_ALIASES = {"ya": "ya", "yes": "ya", "betul": "ya", "memenuhi": "ya",
            "separa": "separa", "sebahagian": "separa", "partial": "separa",
            "tidak": "tidak", "no": "tidak", "salah": "tidak", "bukan": "tidak"}
_JSON_OBJ = re.compile(r"\{.*?\}", re.S)
_MET_FIELD = re.compile(r'"?met"?\s*:\s*"?\s*(ya|separa|tidak)', re.I)
_FIRST_WORD = re.compile(r"[A-Za-z]+")


@dataclass
class Judgement:
    met: str | None          # ya | separa | tidak | None (unparseable)
    reason: str
    raw: str
    attempts: int


def parse_verdict(text: str) -> tuple[str | None, str]:
    """Return (verdict, reason) from model output, or (None, '') if unusable."""
    t = text.strip()
    for block in _JSON_OBJ.findall(t):
        try:
            obj = json.loads(block)
            met = str(obj.get("met", "")).strip().lower()
            if met in VERDICTS:
                return met, str(obj.get("reason", "")).strip()
        except (json.JSONDecodeError, AttributeError):
            pass
    m = _MET_FIELD.search(t)
    if m:
        return m.group(1).lower(), ""
    w = _FIRST_WORD.search(t)
    if w and w.group(0).lower() in _ALIASES:
        return _ALIASES[w.group(0).lower()], t[w.end():].strip(" ,.:-")
    return None, ""


def judge_criterion(
    generate: Generate,
    *,
    criterion: str,
    question: str,
    reference: str,
    answer: str,
    context: str,
    max_new_tokens: int = 80,
) -> Judgement:
    prompt = prompts.render("judge_criterion", criterion=criterion, question=question,
                            reference=reference, answer=answer, context=context or "-")
    raw = generate([{"role": "user", "content": prompt}], max_new_tokens)
    met, reason = parse_verdict(raw)
    if met:
        return Judgement(met, reason, raw, 1)
    retry = prompts.render("judge_retry", criterion=criterion, reference=reference, answer=answer)
    raw2 = generate([{"role": "user", "content": retry}], 8)
    met, reason = parse_verdict(raw2)
    return Judgement(met, reason, f"{raw}\n---retry---\n{raw2}", 2)


# ---------------------------------------------------------------------------
# Probability judge (Phase 5): read the first-token probabilities of
# YA / SEPARA / TIDAK instead of parsing generated text.
# ---------------------------------------------------------------------------
LabelProbs = Callable[[list[dict], dict[str, list[str]]], dict[str, float]]

LABELS = {
    "ya": ["YA", "Ya", "ya", " YA", " Ya"],
    "separa": ["SEPARA", "Separa", "separa", " SEPARA", " Separa"],
    "tidak": ["TIDAK", "Tidak", "tidak", " TIDAK", " Tidak"],
}


def format_examples(examples: list[dict] | None) -> str:
    """Few-shot block. Each example: criterion, answer, met."""
    if not examples:
        return ""
    lines = ["", "Contoh penilaian:"]
    for e in examples:
        lines.append(f'- Kriteria: {e["criterion"]} | Jawapan murid: "{e["answer"]}" -> {e["met"].upper()}')
    return "\n".join(lines) + "\n"


def judge_prob(
    label_probs: LabelProbs,
    *,
    criterion: str,
    question: str,
    reference: str,
    answer: str,
    context: str,
    examples: list[dict] | None = None,
) -> dict[str, float]:
    """Return {'ya': p, 'separa': p, 'tidak': p} (sums to 1)."""
    prompt = prompts.render("judge_prob", criterion=criterion, question=question, reference=reference,
                            answer=answer, context=context or "-", examples=format_examples(examples))
    return label_probs([{"role": "user", "content": prompt}], LABELS)


def expected_credit(p: dict[str, float]) -> float:
    """0..1 credit implied by the judge: P(ya) + 0.5 * P(separa)."""
    return p.get("ya", 0.0) + 0.5 * p.get("separa", 0.0)
