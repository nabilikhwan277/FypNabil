import random

import pytest

from backend.app.assess import pipeline
from backend.app.assess.feedback import guard_encouragement
from backend.app.assess.decision import PHASE4
from backend.app.assess.react import run_react
from backend.app.memory.db import MemoryStore, TopicHistory
from backend.app.questions import load_questions

from .fakes import FakeHit, ScriptedLLM, fake_embed

Q = {
    "id": "f_q2", "subject": "fiqh", "topic_id": "fiqh_b1_solat_dhuha", "level": 2, "type": "structured",
    "question_rumi": "Nyatakan dua fadhilat solat dhuha.",
    "reference_answer_rumi": "Dimurahkan rezeki; diampunkan dosa",
    "reference_answer_jawi": "دموراهكن رزقي؛ دأمڤونكن دوس",
    "rubric": [
        {"criterion": "Dimurahkan rezeki", "marks": 1, "keywords": ["rezeki"]},
        {"criterion": "Diampunkan dosa", "marks": 1, "keywords": ["diampunkan dosa"]},
    ],
    "max_marks": 2, "source_pages": [15],
}


def fake_search(query, subject=None, topic_id=None, k=4):
    return [FakeHit("c1", "Fadhilat: dimurahkan rezeki, diampunkan dosa.", topic_id)]


def fake_source(topic_id, pages):
    return {"rumi": "Buku Teks Ibadah Tahun 5, ms. 10", "jawi": "-", "topic_rumi": "Solat Dhuha", "book_pages": [10]}


def run(answer, llm, history=None):
    return run_react(Q, answer, search=fake_search, embed=fake_embed,
                     history=lambda t: history or TopicHistory(t), source=fake_source, generate=llm,
                     config=PHASE4)


def test_trace_has_five_ordered_steps():
    res = run("dimurahkan rezeki", ScriptedLLM('{"met":"tidak"}', "Teruskan usaha, kamu boleh!"))
    actions = [s.action for s in res.trace]
    assert actions == ["get_question", "search_notes", "score_rubric", "get_history", "generate_feedback"]
    assert all(s.thought for s in res.trace)
    assert res.trace[1].observation["chunks"][0]["id"] == "c1"


def test_feedback_is_grounded_and_uses_textbook_source():
    res = run("dimurahkan rezeki", ScriptedLLM('{"met":"tidak"}', "Teruskan usaha, kamu boleh!"))
    fb = res.feedback
    assert fb["score"] == 1 and fb["max_marks"] == 2 and fb["stars"] == 2
    assert fb["correct_answer"]["rumi"] == Q["reference_answer_rumi"]
    assert fb["source"]["rumi"].endswith("ms. 10")
    assert [m["criterion"] for m in fb["mistakes"]] == ["Diampunkan dosa"]
    assert fb["encouragement"] == {"rumi": "Teruskan usaha, kamu boleh!", "jawi": fb["encouragement"]["jawi"],
                                   "source": "llm"}


def test_hallucinated_encouragement_is_replaced_by_template():
    res = run("dimurahkan rezeki", ScriptedLLM('{"met":"tidak"}', "Solat dhuha ialah 12 rakaat wajib."))
    assert res.feedback["encouragement"]["source"] == "template"


def test_repeated_mistake_is_named():
    h = TopicHistory(Q["topic_id"], mastery=0.5, attempts=2, repeated_mistakes=["Diampunkan dosa"])
    res = run("dimurahkan rezeki", ScriptedLLM('{"met":"tidak"}'), history=h)
    assert "Diampunkan dosa" in res.feedback["repeated"]["rumi"]


def test_guard_encouragement():
    assert guard_encouragement("Bagus, teruskan belajar! Kamu hebat.") == "Bagus, teruskan belajar!"
    assert guard_encouragement("Mad Asli dibaca 2 harakat.") is None
    assert guard_encouragement("شاباس") is None
    assert guard_encouragement("") is None
    assert guard_encouragement("Jangan terlalu cepat, jangan terlalu cepat, jangan terlalu cepat") is None


# ---------- pipeline wiring (real question bank, fake models) ----------
@pytest.fixture
def wired(monkeypatch):
    monkeypatch.setattr(pipeline, "embed", fake_embed)
    monkeypatch.setattr(pipeline, "search_notes", fake_search)
    llm = ScriptedLLM(default='{"met":"tidak"}')
    monkeypatch.setattr(pipeline, "llm_generate", llm)
    monkeypatch.setattr(pipeline, "llm_label_probs", lambda m, labels: {"ya": 0.1, "separa": 0.1, "tidak": 0.8})
    return MemoryStore(":memory:")


def test_assess_saves_attempt_and_validates_input(wired):
    sid = wired.get_or_create_student("Ali", "5A")["id"]
    qid = "tajwid_b3_mad_badal_q1"
    ref = load_questions()[qid]["reference_answer_rumi"]
    res = pipeline.assess(sid, qid, ref, memory=wired)
    assert res.percent == 100 and res.attempt_id and "langkah_pertama" in res.new_badges
    assert len(res.trace) == 5
    assert wired.history(sid, "tajwid_b3_mad_badal").attempts == 1
    for bad in ("", "   ", "x" * 2001):
        with pytest.raises(pipeline.AssessmentError):
            pipeline.assess(sid, qid, bad, memory=wired)
    with pytest.raises(pipeline.AssessmentError):
        pipeline.assess(sid, "no_such_q", "jawapan", memory=wired)
    with pytest.raises(pipeline.AssessmentError):
        pipeline.assess(999, qid, "jawapan", memory=wired)


def test_next_question_is_adaptive(wired):
    sid = wired.get_or_create_student("Siti", "5A")["id"]
    q = pipeline.next_question(sid, subject="tajwid", memory=wired, rng=random.Random(0))
    assert q["subject"] == "tajwid" and q["level"] == 1
    with pytest.raises(pipeline.AssessmentError):
        pipeline.next_question(sid, topic_id=q["topic_id"], level=3, memory=wired)
    pub = pipeline.public_question(q)
    assert "rubric" not in pub and "reference_answer_rumi" not in pub and pub["criteria_count"] >= 1
