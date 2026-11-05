"""RAG evaluation helpers: what the model reads, gold-evidence scoring and the bootstrap, without network or GPU."""
import sys
from pathlib import Path

from backend.app.kb.rag import CONTEXT_CHARS, Retrieved
from backend.app.kb.retriever import Hit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "eval"))

import rag_eval  # noqa: E402
import rag_settings  # noqa: E402


def _hit(i: int, n: int) -> Hit:
    return Hit(f"t::s{i}", f"Topik: T\nBahagian: S{i}\n\n" + "x" * n, 0.5, {"section": f"S{i}"})


def test_model_reads_only_what_fits_the_context_limit():
    limit = CONTEXT_CHARS["R1"]
    got = Retrieved("R1", [_hit(1, 800), _hit(2, 800), _hit(3, 800), _hit(4, 100)])
    given = got.given()
    assert [h.id for h in given] == ["t::s1", "t::s2"]          # the 3rd passage would pass the limit: stop there
    assert got.context == "\n\n".join(h.text for h in given)
    assert len(got.context) <= limit
    assert [c["id"] for c in got.chunks()] == ["t::s1", "t::s2"]   # the trace and the judges see the same passages


def test_a_first_passage_longer_than_the_limit_is_cut():
    got = Retrieved("R1", [_hit(1, 5000), _hit(2, 100)])
    assert len(got.given()) == 1
    assert len(got.context) == CONTEXT_CHARS["R1"]


def test_average_precision_is_ragas_context_precision():
    assert rag_eval.average_precision([True, False, True]) == (1 / 1 + 2 / 3) / 2
    assert rag_eval.average_precision([False, False]) == 0.0


def test_gold_scoring_counts_supporting_lines():
    gold = {"statements": [{"statement": "a", "lines": ["Solat Aidilfitri pada 1 Syawal"]},
                           {"statement": "b", "lines": ["Dua rakaat dengan takbir"]},
                           {"statement": "c", "lines": []}]}           # not in the textbook: left out
    r = {"given": [{"text": "lain"}, {"text": "Solat Aidilfitri pada 1 Syawal pagi"}],
         "context": "lain\n\nSolat Aidilfitri pada 1 Syawal pagi"}
    s = rag_settings.score(r, gold)
    assert s["hit_rate"] == 1.0 and s["evidence_recall"] == 0.5
    assert s["precision"] == 0.5 and s["mrr"] == 0.5
    assert rag_settings.score(r, {"statements": [{"statement": "x", "lines": []}]}) is None


def test_paired_bootstrap_interval():
    d = rag_settings.paired_ci([1.0] * 20, [0.0] * 20)
    assert d == [1.0, 1.0, 1.0]
    mean, lo, hi = rag_settings.paired_ci([1, 0] * 10, [0, 1] * 10)
    assert mean == 0.0 and lo < 0 < hi
