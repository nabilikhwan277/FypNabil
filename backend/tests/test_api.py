"""API tests with an in-memory DB and fake models (no GPU needed)."""
import pytest
from fastapi.testclient import TestClient

from backend.app import main
from backend.app.assess import pipeline
from backend.app.memory.db import MemoryStore
from backend.app.questions import load_questions

from .fakes import FakeHit, ScriptedLLM, fake_embed


@pytest.fixture
def client(monkeypatch):
    mem = MemoryStore(":memory:")
    monkeypatch.setattr(pipeline, "get_memory", lambda: mem)
    monkeypatch.setattr(pipeline, "embed", fake_embed)
    monkeypatch.setattr(pipeline, "search_notes",
                        lambda q, subject=None, topic_id=None, k=4: [FakeHit("c", "nota", topic_id)])
    monkeypatch.setattr(pipeline, "llm_generate", ScriptedLLM())
    monkeypatch.setattr(pipeline, "llm_label_probs", lambda m, labels: {"ya": 0.1, "separa": 0.1, "tidak": 0.8})
    monkeypatch.setattr(main.settings, "preload_models", False)
    with TestClient(main.app) as c:
        yield c


def login(client, name="Aisyah", kelas="5 Bestari"):
    r = client.post("/api/auth/login", json={"name": name, "kelas": kelas, "avatar": "🐼"})
    assert r.status_code == 200
    return r.json()


def test_login_is_idempotent_and_validates(client):
    a, b = login(client), login(client, name="  Aisyah ")
    assert a["id"] == b["id"] and a["avatar"] == "🐼"
    assert client.post("/api/auth/login", json={"name": "   "}).status_code == 422
    assert client.post("/api/auth/login", json={"name": "x" * 41}).status_code == 422
    r = client.post("/api/auth/login", json={"name": "Ali", "avatar": "<script>"})
    assert r.json()["avatar"] == "🐱"   # unknown avatar replaced


def test_subjects_catalog(client):
    subs = client.get("/api/subjects").json()
    assert [s["id"] for s in subs] == ["fiqh", "jawi", "tajwid"]
    topics = [t for s in subs for b in s["babs"] for t in b["topics"]]
    assert len(topics) == 48
    tajwid_topics = [t["id"] for b in subs[2]["babs"] for t in b["topics"]]
    assert tajwid_topics[0] == "tajwid_b1_mad_bahagian" and tajwid_topics[-1] == "tajwid_b6_ibtida"
    assert all(t["level_unlocked"] == 1 for t in topics)
    assert client.get("/api/subjects?student_id=999").status_code == 404


def test_note_endpoint(client):
    r = client.get("/api/topics/tajwid_b3_mad_badal/note").json()
    assert r["topic"]["title_rumi"] == "Mad Badal" and "Pengertian" in r["markdown"]
    assert r["source"]["rumi"].startswith("Buku Teks Tajwid")
    assert client.get("/api/topics/nope/note").status_code == 404


def test_next_question_hides_answers(client):
    sid = login(client)["id"]
    q = client.get(f"/api/questions/next?student_id={sid}&subject=jawi").json()
    assert q["subject"] == "jawi" and q["level"] == 1
    assert "rubric" not in q and "reference_answer_rumi" not in q and "reference_answer_jawi" not in q
    locked = client.get(f"/api/questions/next?student_id={sid}&topic_id={q['topic_id']}&level=2")
    assert locked.status_code == 400
    assert client.get(f"/api/questions/next?student_id={sid}&level=9").status_code == 422


def test_answer_flow_updates_progress(client):
    sid = login(client)["id"]
    qid = "tajwid_b3_mad_badal_q1"
    ref = load_questions()[qid]["reference_answer_rumi"]
    r = client.post("/api/answers", json={"student_id": sid, "question_id": qid, "answer": ref})
    assert r.status_code == 200
    body = r.json()
    assert body["percent"] == 100 and body["feedback"]["stars"] == 3 and len(body["trace"]) == 5
    p = client.get(f"/api/progress/{sid}").json()
    assert p["xp"] == 32 and "langkah_pertama" in p["badges"] and p["recent"][0]["question_id"] == qid
    tajwid = next(s for s in p["subjects"] if s["id"] == "tajwid")
    assert next(t for t in tajwid["topics"] if t["id"] == "tajwid_b3_mad_badal")["attempts"] == 1


def test_answer_validation(client):
    sid = login(client)["id"]
    ok = {"student_id": sid, "question_id": "tajwid_b3_mad_badal_q1", "answer": "dua"}
    assert client.post("/api/answers", json={**ok, "answer": ""}).status_code == 422
    assert client.post("/api/answers", json={**ok, "answer": "  "}).status_code == 400
    assert client.post("/api/answers", json={**ok, "question_id": "nope"}).status_code == 400
    assert client.post("/api/answers", json={**ok, "student_id": 999}).status_code == 404
    assert client.get("/api/progress/999").status_code == 404
