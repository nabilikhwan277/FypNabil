"""Integration tests: need the built KB (python -m backend.app.kb.ingest) and
the bge-m3 model. Skipped automatically when the KB is missing."""
import pytest

from backend.app.config import get_settings

pytestmark = pytest.mark.skipif(
    not (get_settings().chroma_dir.parent / "kb_manifest.json").exists(),
    reason="knowledge base not built",
)


def test_where_builder():
    from backend.app.kb.retriever import _where

    assert _where(None, None, False) is None
    assert _where("jawi", None, False) == {"subject": "jawi"}
    assert _where("jawi", "t1", True) == {"$and": [{"subject": "jawi"}, {"topic_id": "t1"}, {"verified": True}]}


def test_search_finds_right_topic_without_filter():
    from backend.app.kb.retriever import search_notes

    hits = search_notes("Berapakah kadar harakat Mad Badal?", subject="tajwid", k=4)
    assert len(hits) == 4
    assert "tajwid_b3_mad_badal" in [h.topic_id for h in hits]
    assert hits == sorted(hits, key=lambda h: -h.score)


def test_topic_filter_restricts_results():
    from backend.app.kb.retriever import search_notes

    hits = search_notes("niat solat", subject="fiqh", topic_id="fiqh_b1_solat_dhuha", k=3)
    assert hits and all(h.topic_id == "fiqh_b1_solat_dhuha" for h in hits)


def test_reference_similarity_orders_right_above_wrong():
    from backend.app.kb.retriever import reference_similarity

    qid = "tajwid_b3_mad_badal_q1"  # reference answer: "Dua harakat"
    right = reference_similarity("2 harakat", qid)
    wrong = reference_similarity("solat dhuha pada waktu pagi", qid)
    assert right > wrong
    assert reference_similarity("apa-apa", "no_such_question") == 0.0
