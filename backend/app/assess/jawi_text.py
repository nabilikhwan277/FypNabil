"""Normalisation for mixed Rumi / Jawi / Arabic text.

Used by keyword retrieval now and by rubric matching in Phase 4. The goal is
that spellings which a teacher would accept as the same compare equal, while
real spelling differences (e.g. ة vs ت, ۏ vs و, ݢ vs ك) are kept.
"""
from __future__ import annotations

import re
import unicodedata

# Arabic diacritics (harakat, tanwin, sukun, shadda, dagger alif, Quranic marks)
_HARAKAT = re.compile("[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED\u08D3-\u08FF]")
_TATWEEL = "\u0640"

# Letter variants that are the same letter in Jawi usage / different fonts.
_FOLD = str.maketrans({
    "ى": "ي",   # alif maqsura -> ya   (NB: applied only in loose mode, see below)
    "ی": "ي",   # Persian ya
    "ک": "ك",   # keheh -> kaf (textbook font prints final kaf as ک)
    "ٴ": "ء",   # high hamza -> hamza
    "أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا",   # alif forms
    "ؤ": "و",
    "ئ": "ي",
    "٬": ",", "،": ",", "؛": ";", "؟": "?",
    "٢": "2",   # Jawi reduplication sign is written as Arabic-Indic 2
})
_FOLD_STRICT = {k: v for k, v in {
    "ی": "ي", "ک": "ك", "ٴ": "ء", "٬": ",", "،": ",", "؛": ";", "؟": "?", "٢": "2",
}.items()}
_FOLD_STRICT_T = str.maketrans(_FOLD_STRICT)

_ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
_SPACE = re.compile(r"\s+")
_TOKEN = re.compile(r"[\w]+", re.UNICODE)


def normalize(text: str, strict: bool = False) -> str:
    """Canonical form for comparison.

    strict=False (retrieval): fold alif/hamza-seat/ya variants, strip harakat.
    strict=True (Jawi spelling marking): only strip harakat/tatweel and fold
    font-only variants (ک->ك, ی->ي), keeping hamza seats and ى, which are
    real spelling choices in Jawi (e.g. ميكانيسمى).
    """
    if not text:
        return ""
    t = unicodedata.normalize("NFKC", text)
    t = _HARAKAT.sub("", t).replace(_TATWEEL, "")
    t = t.translate(_FOLD_STRICT_T if strict else _FOLD)
    t = t.translate(_ARABIC_DIGITS).lower()
    t = t.replace("-", " ")  # "kanak-kanak" == "kanak kanak"
    return _SPACE.sub(" ", t).strip()


def tokens(text: str) -> list[str]:
    return _TOKEN.findall(normalize(text))


def is_arabic_script(text: str) -> bool:
    return any("\u0600" <= ch <= "\u06FF" or "\u0750" <= ch <= "\u077F" for ch in text)
