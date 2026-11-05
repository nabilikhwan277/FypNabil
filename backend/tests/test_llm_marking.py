"""LLM marking, the model layer and the agreement maths, without any network or GPU."""
import json
import sys
from pathlib import Path

import pytest

from backend.app import llm_api
from backend.app.assess import llm_marking as lm
from backend.app.assess.llm_marking import MarkConfig, mark

ROOT = Path(__file__).resolve().parents[2]

Q = {
    "id": "t_q1", "topic_id": "tajwid_b3_mad_farq", "subject": "tajwid", "level": 1, "type": "short", "max_marks": 2,
    "question_rumi": "Berapakah bilangan kalimah Mad Farq dan di berapa tempat?",
    "reference_answer_rumi": "Tiga kalimah dalam enam tempat",
    "rubric": [{"criterion": "Tiga kalimah", "marks": 1, "keywords": ["tiga kalimah"]},
               {"criterion": "Enam tempat", "marks": 1, "keywords": ["enam tempat"]}],
}
JAWI_Q = {**Q, "subject": "jawi", "id": "j_q1",
          "rubric": [{"criterion": "Mengeja كسيلاوان", "marks": 2, "keywords": ["كسيلاوان"]}]}


def fake_complete(replies):
    calls = []

    def _complete(model, messages, *, schema=None, **kw):
        calls.append({"model": model, "messages": messages, "schema": schema, **kw})
        text = replies.pop(0) if replies else "{}"
        return llm_api.Completion(text, llm_api.parse_json(text) if schema else None, model, 100, 20, 0.0001, 5)
    return _complete, calls


def test_parse_json_tolerates_fences_and_text():
    assert llm_api.parse_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert llm_api.parse_json('Here it is: {"a": {"b": "x}"}} thanks') == {"a": {"b": "x}"}}
    assert llm_api.parse_json("no json") is None


def test_config_names_round_trip():
    for text in ("b2", "b1:luna", "b3:haiku:R1", "proposed:qwen:R3:A3:on"):
        cfg = MarkConfig.parse(text)
        assert MarkConfig.parse(cfg.name) == cfg
    assert MarkConfig.parse("proposed:luna:R2:A2:on").memory is True
    with pytest.raises(ValueError):
        MarkConfig.parse("proposed:gpt99")


def test_b1_marks_from_json_and_adds_up_in_code(monkeypatch):
    reply = json.dumps({"criteria": [{"no": 1, "verdict": "tidak", "reason": "tertukar"},
                                     {"no": 2, "verdict": "separa", "reason": "x"}], "feedback": "Bilangan tertukar."})
    fake, calls = fake_complete([reply])
    monkeypatch.setattr(lm, "complete", fake)
    r = mark(Q, "Enam kalimah dalam tiga tempat.", MarkConfig.parse("b1:luna"))
    assert r.ok and [c["met"] for c in r.criteria] == ["tidak", "separa"]
    assert r.score == 0.5 and r.max_marks == 2.0 and r.feedback == "Bilangan tertukar."
    assert "JAWAPAN RUJUKAN" not in calls[0]["messages"][1]["content"]   # zero-shot: no reference answer
    assert calls[0]["schema"] == lm.MARK_SCHEMA


def test_incomplete_reply_is_not_ok(monkeypatch):
    fake, _ = fake_complete(['{"criteria": [{"no": 1, "verdict": "ya", "reason": ""}], "feedback": ""}'])
    monkeypatch.setattr(lm, "complete", fake)
    r = mark(Q, "Tiga kalimah", MarkConfig.parse("b1:luna"))
    assert not r.ok and r.criteria[1]["met"] == "tidak"


def test_proposed_keeps_hard_rule_for_jawi_spelling(monkeypatch):
    """The LLM cannot overrule an exact Jawi spelling check."""
    reply = json.dumps({"criteria": [{"no": 1, "verdict": "ya", "reason": "hampir sama"}], "feedback": "Bagus."})
    fake, calls = fake_complete([reply])
    monkeypatch.setattr(lm, "complete", fake)
    monkeypatch.setattr(lm, "_retrieve", lambda *a, **k: type("R", (), {"context": "teks", "chunks": lambda self: []})())
    r = mark(JAWI_Q, "كسيلاون", MarkConfig.parse("proposed:luna:R1:A2:off"))
    assert r.criteria[0]["met"] == "tidak" and r.criteria[0]["layer"] == "rule"
    assert "jangan ubah" in calls[0]["messages"][1]["content"]
    assert r.trace[0]["action"] == "hard_rules"


def test_keyword_hit_is_left_to_the_llm(monkeypatch):
    """A plain keyword match is not accepted by rule (keyword illusion)."""
    assert lm._hard_rules(Q, "Tiga kalimah dalam enam tempat") == {}


def test_memory_only_sent_when_switched_on(monkeypatch):
    reply = json.dumps({"criteria": [{"no": 1, "verdict": "ya", "reason": ""}, {"no": 2, "verdict": "ya", "reason": ""}],
                        "feedback": "Bagus."})
    memory = {"mastery": 0.4, "attempts": 3, "recent_mistakes": ["Enam tempat"], "weak_topics": ["mad farq"]}
    monkeypatch.setattr(lm, "_retrieve", lambda *a, **k: type("R", (), {"context": "teks", "chunks": lambda self: []})())
    for on in (False, True):
        fake, calls = fake_complete([reply])
        monkeypatch.setattr(lm, "complete", fake)
        mark(Q, "Tiga kalimah dalam enam tempat", MarkConfig("proposed", "luna", "R1", "A2", on), memory=memory)
        assert ("SEJARAH MURID" in calls[0]["messages"][1]["content"]) is on


def test_a1_loop_uses_tools_then_submits(monkeypatch):
    steps = [json.dumps({"thought": "lihat rubrik", "action": "get_rubric", "input": {}}),
             json.dumps({"thought": "hantar", "action": "submit_marks",
                         "input": {"criteria": [{"no": 1, "verdict": "ya", "reason": ""},
                                                {"no": 2, "verdict": "tidak", "reason": ""}], "feedback": "Separuh betul."}})]
    fake, calls = fake_complete(steps)
    monkeypatch.setattr(lm, "complete", fake)
    r = mark(Q, "Tiga kalimah", MarkConfig.parse("proposed:luna:R1:A1:off"))
    assert r.ok and r.score == 1.0 and len(calls) == 2
    assert [t["action"] for t in r.trace] == ["hard_rules", "get_rubric", "submit_marks"]


def test_a1_without_submit_fails_cleanly(monkeypatch):
    fake, _ = fake_complete([json.dumps({"thought": "", "action": "get_history", "input": {}})] * 6)
    monkeypatch.setattr(lm, "complete", fake)
    r = mark(Q, "x", MarkConfig.parse("proposed:luna:R1:A1:off"))
    assert not r.ok and "submit_marks" in r.error


def test_budget_stops_api_calls(monkeypatch, tmp_path):
    s = llm_api.get_settings()
    monkeypatch.setattr(s, "llm_log_path", tmp_path / "calls.jsonl")
    monkeypatch.setattr(s, "llm_cache_dir", tmp_path / "cache")
    monkeypatch.setattr(s, "llm_budget_usd", 0.01)
    (tmp_path / "calls.jsonl").write_text(json.dumps({"cost": 0.02, "cached": False}) + "\n", encoding="utf-8")
    with pytest.raises(llm_api.BudgetExceeded):
        llm_api.complete("luna", [{"role": "system", "content": "x"}, {"role": "user", "content": "y"}])


def test_fleiss_kappa_textbook_example():
    sys.path.insert(0, str(ROOT / "scripts"))
    sys.path.insert(0, str(ROOT / "eval"))
    import teacher_sheet

    counts = [[0, 0, 0, 0, 14], [0, 2, 6, 4, 2], [0, 0, 3, 5, 6], [0, 3, 9, 2, 0], [2, 2, 8, 1, 1],
              [7, 7, 0, 0, 0], [3, 2, 6, 3, 0], [2, 5, 3, 2, 2], [6, 5, 2, 1, 0], [0, 2, 2, 3, 7]]
    grid = [[c for c, n in enumerate(row) for _ in range(n)] for row in counts]
    assert round(teacher_sheet._fleiss_kappa(grid, categories=5), 3) == 0.210


def test_a_cached_call_pays_nothing_but_keeps_its_list_price(monkeypatch):
    """Cost tables must show what a system costs, not what a rerun from the cache paid."""
    reply = json.dumps({"criteria": [{"no": 1, "verdict": "ya", "reason": "x"}, {"no": 2, "verdict": "ya", "reason": "y"}],
                        "feedback": "Bagus."})
    monkeypatch.setattr(lm, "complete", lambda model, messages, **kw: llm_api.Completion(
        reply, llm_api.parse_json(reply), model, 100, 20, 0.0003, 5, cached=True))
    r = mark(Q, "Tiga kalimah dalam enam tempat.", MarkConfig.parse("b1:luna"))
    assert r.usage["cost"] == 0.0 and r.usage["cached"] == 1
    assert r.usage["list_cost"] == pytest.approx(0.0003)


@pytest.mark.parametrize("bad", ["proposed:luna:R9:A2:off", "proposed:luna:R3:A7:off", "b3:luna:R0"])
def test_config_with_an_unknown_rag_or_react_name_is_rejected(bad):
    with pytest.raises(ValueError):
        MarkConfig.parse(bad)


def test_a1_survives_a_string_where_the_model_should_send_an_object(monkeypatch):
    steps = [json.dumps({"thought": "", "action": "search_notes", "input": "mad farq"}),
             json.dumps({"thought": "", "action": "submit_marks",
                         "input": {"criteria": [{"no": 1, "verdict": "ya", "reason": ""},
                                                {"no": 2, "verdict": "ya", "reason": ""}], "feedback": "Betul."}})]
    fake, calls = fake_complete(steps)
    monkeypatch.setattr(lm, "complete", fake)
    monkeypatch.setattr(lm, "_retrieve", lambda *a, **k: type("R", (), {"context": "teks", "chunks": lambda self: []})())
    r = mark(Q, "Tiga kalimah dalam enam tempat", MarkConfig.parse("proposed:luna:R1:A1:off"))
    assert r.ok and r.score == 2.0 and len(calls) == 2


def test_a_bad_live_scorer_name_falls_back_to_b2_and_is_logged(monkeypatch, caplog):
    from types import SimpleNamespace

    from backend.app.assess import pipeline, rubric

    mem = SimpleNamespace(history=lambda sid, tid: SimpleNamespace(mastery=0.5, attempts=1, repeated_mistakes=[]),
                          all_mastery=lambda sid: {})
    monkeypatch.setattr(pipeline, "live_scorer", lambda: "proposed:luna:R9:A2:off")     # e.g. a typo in KAFA_SCORER
    monkeypatch.setattr(rubric, "score_answer", lambda *a, **k: "B2-RESULT")
    with caplog.at_level("WARNING"):
        r, details = pipeline._llm_score({"topic_id": "t_x"}, "jawapan", 1, mem, {})
    assert r == "B2-RESULT" and details["scorer"] == "b2 (fallback)" and "R9" in details["fallback_reason"]
    assert "fell back to B2" in caplog.text
