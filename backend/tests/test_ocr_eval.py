"""OCR comparison scoring (eval/ocr_eval.py): which text is scored and how errors are counted, offline."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "eval"))

import ocr_eval  # noqa: E402

NOTE = """## Pengertian | ڤڠرتين
- **Rumi:** Puasa ialah menahan diri. | **Jawi:** ڤواس اياله مناهن ديري.
بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ ﴿١﴾
"""


def test_only_arabic_script_is_kept_and_quran_is_split_out():
    lines = ocr_eval.arabic_lines(NOTE)
    assert lines["jawi"] == ["ڤڠرتين", "ڤواس اياله مناهن ديري"]
    assert len(lines["arabic"]) == 1 and "١" not in lines["arabic"][0]     # verse numbers dropped


def test_perfect_reading_scores_zero_and_missing_text_scores_one():
    same = ocr_eval.compare(NOTE, NOTE)
    assert same["jawi"]["cer"] == 0 and same["jawi"]["f1"] == 1 and same["arabic"]["cer"] == 0
    empty = ocr_eval.compare(NOTE, "")
    assert empty["jawi"]["cer"] == 1 and empty["jawi"]["f1"] == 0


def test_word_f1_ignores_order_but_cer_does_not():
    swapped = ocr_eval.compare("ڤواس اياله\nمناهن ديري", "مناهن ديري\nڤواس اياله")
    assert swapped["jawi"]["f1"] == 1 and swapped["jawi"]["cer"] > 0


def test_only_the_jawi_field_of_a_pair_is_scored():
    # a reader that copies the Quran verse into the Rumi field too must not have it counted twice
    line = "- **Rumi:** بِهِ رَيْبَ (Surah al-Tur) | **Jawi:** بِهِ رَيْبَ (سورة الطور)"
    got = ocr_eval.arabic_lines(line)
    assert " ".join(got["arabic"] + got["jawi"]).split().count("رَيْبَ") == 1


def test_unclear_marks_are_not_scored_as_text():
    got = ocr_eval.compare("ڤواس اياله", "ڤواس [TIDAK JELAS]")
    assert got["jawi"]["recall"] == 0.5 and got["jawi"]["precision"] == 1
