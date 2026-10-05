"""Deterministic answer matching used by rubric Layer A."""
from __future__ import annotations

import re

from .jawi_text import is_arabic_script, normalize

_TOKEN = re.compile(r"\w+", re.UNICODE)

# Number words -> digits, so "dua harakat" == "2 harakat". Rumi and Jawi.
_NUMBERS = {
    "satu": "1", "dua": "2", "tiga": "3", "empat": "4", "lima": "5", "enam": "6",
    "tujuh": "7", "lapan": "8", "sembilan": "9", "sepuluh": "10",
}
_JAWI_NUMBERS = {
    "ساتو": "1", "دوا": "2", "تيݢ": "3", "امڤت": "4", "ليم": "5", "انم": "6",
    "توجوه": "7", "لاڤن": "8", "سمبيلن": "9", "سڤولوه": "10",
}
for _w, _d in _JAWI_NUMBERS.items():
    _NUMBERS[normalize(_w)] = _d
    _NUMBERS[normalize(_w, strict=True)] = _d

_TRUE_FALSE = {"betul", "salah", "بتول", "ساله"}


def toks(text: str, strict: bool = False) -> list[str]:
    return [_NUMBERS.get(t, t) for t in _TOKEN.findall(normalize(text, strict=strict))]


def numbers_in(text: str) -> set[str]:
    return {t for t in toks(text) if t.isdigit()}


def phrase_in(keyword: str, answer: str, strict: bool | None = None) -> bool:
    """True if the keyword's tokens appear contiguously in the answer.

    Spacing differences are tolerated by comparing joined token windows, so the
    textbook's spaced form "تيك س" matches "تيكس" and vice versa.
    strict=None -> strict normalisation for Arabic-script keywords.
    """
    if strict is None:
        strict = is_arabic_script(keyword)
    kt = toks(keyword, strict)
    if not kt:
        return False
    at = toks(answer, strict)
    target = "".join(kt)
    for i in range(len(at)):
        joined = ""
        for j in range(i, len(at)):
            joined += at[j]
            if joined == target:
                return True
            if len(joined) >= len(target):
                break
    return False


def first_match(keywords: list[str], answer: str, strict: bool | None = None) -> str | None:
    for kw in keywords:
        if kw and phrase_in(kw, answer, strict):
            return kw
    return None


def number_conflict(reference: str, answer: str) -> bool:
    """Reference states numbers, the answer states numbers, and none of the
    reference numbers appear in the answer (e.g. "enam harakat" vs "dua")."""
    ref_n, ans_n = numbers_in(reference), numbers_in(answer)
    return bool(ref_n and ans_n and not (ref_n & ans_n))


def is_true_false(keywords: list[str]) -> bool:
    return bool(keywords) and all(normalize(k) in _TRUE_FALSE for k in keywords)


def true_false_answer(answer: str) -> str | None:
    """'betul' / 'salah' if the answer clearly states exactly one of them."""
    t = set(toks(answer))
    has_b = bool(t & {"betul", normalize("بتول")}) and not ({"tidak", normalize("تيدق")} & t)
    has_s = bool(t & {"salah", normalize("ساله")}) or ("betul" in t and "tidak" in t)
    if has_b and not has_s:
        return "betul"
    if has_s and not has_b:
        return "salah"
    return None


# Words that carry no content when measuring overlap with a criterion.
_OVERLAP_STOP = {
    "yang", "dan", "atau", "di", "ke", "dari", "daripada", "untuk", "bagi", "pada", "ini", "itu",
    "dengan", "adalah", "ialah", "menyatakan", "menyebut", "betul", "cth", "contoh", "kerana", "sebab",
    "mana", "mana2", "dua", "tiga", "pertama", "kedua", "ketiga", "lain", "dalam", "akan",
}


def _stem_eq(a: str, b: str) -> bool:
    """Loose Malay match: equal, or share the first 5 letters (dosa/dosanya,
    diampun/diampunkan). Short words must match exactly."""
    if a == b:
        return True
    return len(a) >= 5 and len(b) >= 5 and a[:5] == b[:5]


def content_overlap(target: str, answer: str) -> float:
    """Share of the target's content words (0..1) that appear in the answer,
    tolerating affixes. Used as a paraphrase-robust complement to keywords."""
    tt = [t for t in toks(target) if t not in _OVERLAP_STOP and len(t) > 1]
    if not tt:
        return 0.0
    at = toks(answer)
    hit = sum(any(_stem_eq(t, a) for a in at) for t in tt)
    return hit / len(tt)


def keyword_overlap(keywords: list[str], answer: str) -> float:
    """Best content overlap over the rubric keywords (0..1)."""
    return max((content_overlap(k, answer) for k in keywords if k), default=0.0)
