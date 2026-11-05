"""Jawi reading test (eval/jawi_reading.py): fixed items and fair answer matching, offline."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "eval"))

import jawi_reading as J  # noqa: E402


def test_items_are_fixed_and_balanced():
    a, b = J.items(), J.items()
    assert a == b and len(a) == 2 * J.N
    assert sum(i["task"] == "spell" for i in a) == J.N
    assert len({i["ask"] for i in a}) == len(a)


def test_matching_ignores_labels_harakat_and_letter_variants():
    assert J.norm("Jawi: ڬَمبير.", "spell") == J.norm("ݢمبير", "spell")
    assert J.norm("Sekolah\nIni ejaan Rumi.", "read") == "sekolah"
    assert J.norm("سكوله", "spell") != J.norm("سكولاه", "spell")      # a real spelling difference still counts
