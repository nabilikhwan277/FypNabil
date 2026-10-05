from backend.app.assess.jawi_text import is_arabic_script, normalize, tokens
from backend.app.kb.lexical import BM25Index


def test_strips_harakat_and_tatweel():
    assert normalize("أُصَلِّي") == normalize("اصلي")
    assert normalize("كـتـاب") == "كتاب"


def test_font_variants_fold_in_both_modes():
    # textbook prints final kaf as keheh
    for strict in (False, True):
        assert normalize("بڠک", strict=strict) == normalize("بڠك", strict=strict)


def test_strict_mode_keeps_real_spelling_differences():
    # ى (ye) vs ي and hamza seats are meaningful in Jawi spelling
    assert normalize("ميكانيسمى", strict=True) != normalize("ميكانيسمي", strict=True)
    assert normalize("ميكانيسمى") == normalize("ميكانيسمي")  # loose mode for retrieval
    # special Jawi letters are never folded
    assert normalize("ݢورو", strict=True) != normalize("كورو", strict=True)
    assert normalize("ۏيروس") != normalize("ويروس")


def test_rumi_normalisation():
    assert normalize("  Kanak-Kanak  ") == "kanak kanak"
    assert normalize("كانق٢") == "كانق2"
    assert tokens("Dua Harakat!") == ["dua", "harakat"]


def test_is_arabic_script():
    assert is_arabic_script("مد اصلي")
    assert not is_arabic_script("Mad Asli")


def test_bm25_ranks_exact_term_first_and_filters():
    idx = BM25Index(
        ["a", "b", "c"],
        ["mad badal dua harakat", "solat dhuha waktu pagi", "mad lin enam harakat"],
        [{"subject": "tajwid"}, {"subject": "fiqh"}, {"subject": "tajwid"}],
    )
    res = idx.search("mad badal", k=3)
    assert idx.ids[res[0][0]] == "a"
    assert all(idx.metas[i]["subject"] == "fiqh" for i, _ in idx.search("harakat pagi", 3, {"subject": "fiqh"}))
    assert idx.search("tiada perkataan ini", 3) == []
