"""Admin part: sign-in, the live marking system and Books & syllabus, without network, GPU or real data."""
import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import library, llm_api, main
from backend.app.config import get_settings
from backend.app.kb import update

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def env(tmp_path, monkeypatch):
    """Temporary data folders with two real notes of the built-in Ibadah textbook."""
    s = get_settings()
    kn, qn = tmp_path / "knowledge", tmp_path / "questions"
    for topic in ("fiqh_b1_solat_dhuha", "fiqh_b1_solat_hajat"):
        (kn / "fiqh").mkdir(parents=True, exist_ok=True)
        (qn / "fiqh").mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / "data" / "knowledge" / "fiqh" / f"{topic}.md", kn / "fiqh")
        shutil.copy(ROOT / "data" / "questions" / "fiqh" / f"{topic}.json", qn / "fiqh")
    monkeypatch.setattr(s, "knowledge_dir", kn)
    monkeypatch.setattr(s, "questions_dir", qn)
    monkeypatch.setattr(s, "books_dir", tmp_path / "books")
    monkeypatch.setattr(s, "sqlite_path", tmp_path / "storage" / "kafa.db")
    monkeypatch.setattr(s, "admin_password", "rahsia-123")
    monkeypatch.setattr(s, "openrouter_api_key", "test-key")
    monkeypatch.setattr(main.settings, "preload_models", False)
    synced = []
    monkeypatch.setattr(update, "sync", lambda topics, qids: synced.append((set(topics), set(qids))) or {"chunks": 0})
    update.clear_caches()
    yield {"kn": kn, "qn": qn, "synced": synced}
    update.clear_caches()


@pytest.fixture
def client(env):
    with TestClient(main.app) as c:
        yield c


def token(client) -> dict:
    r = client.post("/api/admin/login", json={"password": "rahsia-123"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['token']}"}


def test_admin_sign_in_protects_the_admin_pages(client, monkeypatch):
    assert client.post("/api/admin/login", json={"password": "salah"}).status_code == 401
    assert client.get("/api/admin/config").status_code == 401
    assert client.get("/api/eval/summary").status_code == 401
    assert client.get("/api/admin/config", headers={"Authorization": "Bearer 123.abc"}).status_code == 401
    h = token(client)
    assert client.get("/api/admin/me", headers=h).status_code == 200
    assert client.get("/api/eval/summary", headers=h).status_code == 200
    monkeypatch.setattr(get_settings(), "admin_password", "baharu")   # a new password ends old sessions
    assert client.get("/api/admin/me", headers=h).status_code == 401
    monkeypatch.setattr(get_settings(), "admin_password", "")
    assert client.post("/api/admin/login", json={"password": "x"}).status_code == 503


def test_admin_switches_the_live_marking_system(client):
    h = token(client)
    cfg = client.get("/api/admin/config", headers=h).json()
    assert cfg["live"]["config"] == get_settings().scorer
    assert {m["key"] for m in cfg["options"]["models"]} >= {"haiku", "luna", "qwen"}
    r = client.post("/api/admin/config", json={"config": "proposed:luna:R3:A2:on"}, headers=h)
    assert r.status_code == 200 and r.json()["react_label"].startswith("A2")
    assert client.get("/api/health").json()["live_scorer"] == "proposed:luna:R3:A2:on"
    assert client.post("/api/admin/config", json={"config": "proposed:gpt9"}, headers=h).status_code == 400
    assert client.post("/api/admin/config", json={"config": "proposed:qwen:R3:A2:on"}, headers=h).status_code == 400
    est = client.get("/api/admin/evaluate/estimate", params={"config": "b2", "data": "silver"}, headers=h).json()
    assert est["cost"] == 0.0


def _pdf(pages: int) -> bytes:
    import fitz

    doc = fitz.open()
    for i in range(pages):
        doc.new_page().insert_text((72, 72), f"Halaman {i + 1}")
    return doc.tobytes()


def _fake_model(monkeypatch, replies):
    calls = []

    def fake(model, messages, *, schema=None, tag="", **kw):
        calls.append(tag)
        data = replies(tag, messages)
        return llm_api.Completion(json.dumps(data), data, model, 10, 10, 0.0001, 5)
    monkeypatch.setattr(library, "complete", fake)
    return calls


QUESTION = {"level": 1, "type": "short", "question_rumi": "Berapakah rakaat solat sunat ini?", "question_jawi": "",
            "reference_answer_rumi": "Dua rakaat", "reference_answer_jawi": "",
            "rubric": [{"criterion": "Dua rakaat", "marks": 1, "keywords": ["dua rakaat"]}]}


TOPICS = [{"first_page": 1, "topic_rumi": "Solat Witir Baharu", "topic_jawi": "", "bab": 1, "bab_rumi": "Solat Sunat", "bab_jawi": ""},
          {"first_page": 3, "topic_rumi": "Solat Tasbih", "topic_jawi": "", "bab": 0, "bab_rumi": "", "bab_jawi": ""}]


@pytest.mark.parametrize("segment", [TOPICS, []], ids=["topics-from-the-segment-step", "fallback-to-page-flags"])
def test_textbook_upload_to_syllabus_and_back(env, monkeypatch, segment):
    def replies(tag, messages):
        if tag == "library:segment":
            return {"topics": segment}
        if tag == "library:transcribe":
            page = int(messages[1]["content"][0]["text"].split()[1])
            return {"printed_page": page + 4, "new_topic": page in (1, 3), "bab": 1, "bab_rumi": "Solat Sunat", "bab_jawi": "",
                    "topic_rumi": "Solat Witir Baharu" if page == 1 else "Solat Tasbih", "topic_jawi": "",
                    "markdown": f"## Pengertian | ڤڠرتين\n- **Rumi:** Isi halaman {page}. | **Jawi:** ..."}
        return {"questions": [QUESTION] * 3}
    calls = _fake_model(monkeypatch, replies)

    rec = library.add_book(_pdf(4), filename="buku.pdf", title="Buku Teks Ibadah Edisi Baharu", subject="fiqh", kind="textbook")
    assert rec["status"] == "uploaded" and rec["pages"] == 4 and rec["estimate"] > 0
    library.process(rec["id"])
    assert calls.count("library:transcribe") == 4 and calls.count("library:segment") == 1
    assert calls.count("library:questions") == 2
    d = library.drafts(rec["id"])
    notes = [x for x in d if x["kind"] == "note"]
    assert [n["pages"] for n in notes] in ([[1, 2], [3, 4]], [[3, 4], [1, 2]])
    assert all(not x["errors"] for x in d)

    bad = library.save_draft(rec["id"], notes[0]["path"], notes[0]["content"].replace("subject: fiqh", "subject: jawi"))
    assert bad["errors"]
    with pytest.raises(library.LibraryError):
        library.publish(rec["id"])
    library.save_draft(rec["id"], notes[0]["path"], notes[0]["content"])
    with pytest.raises(library.LibraryError):
        library.save_draft(rec["id"], "../../../evil.md", "x")

    out = library.publish(rec["id"])
    assert out["status"] == "active" and out["topics"] == 2 and out["questions"] == 6
    assert (env["kn"] / "fiqh" / "fiqh_b1_solat_witir_baharu.md").exists()
    assert env["synced"][-1][0] == {"fiqh_b1_solat_witir_baharu", "fiqh_b1_solat_tasbih"}

    books = {b["id"]: b for b in library.list_books()}
    assert books["builtin-fiqh"]["status"] == "active" and books["builtin-fiqh"]["topics"] == 2

    library.remove(rec["id"])
    assert not (env["kn"] / "fiqh" / "fiqh_b1_solat_witir_baharu.md").exists()
    library.restore(rec["id"])
    assert (env["kn"] / "fiqh" / "fiqh_b1_solat_witir_baharu.md").exists()
    with pytest.raises(library.LibraryError):
        library.delete(rec["id"])      # still in the syllabus


def test_removing_a_builtin_textbook_keeps_its_files_for_restore(env):
    library.list_books()
    out = library.remove("builtin-fiqh")
    assert out["status"] == "removed" and out["topics"] == 2
    assert not list(env["kn"].glob("fiqh/*.md")) and not list(env["qn"].glob("fiqh/*.json"))
    assert env["synced"][-1][0] == {"fiqh_b1_solat_dhuha", "fiqh_b1_solat_hajat"}
    with pytest.raises(library.LibraryError):
        library.delete("builtin-fiqh")
    assert library.restore("builtin-fiqh")["status"] == "active"
    assert len(list(env["kn"].glob("fiqh/*.md"))) == 2


def test_exercise_book_questions_are_linked_to_topics(env, monkeypatch):
    from backend.app.kb import retriever

    class Hit:
        topic_id = "fiqh_b1_solat_dhuha"
    monkeypatch.setattr(retriever, "search_notes", lambda q, subject=None, k=3: [Hit()])

    def replies(tag, messages):
        if tag == "library:transcribe":
            return {"printed_page": 1, "questions": [
                {"number": "1", "question_rumi": "Berapakah rakaat solat dhuha?", "question_jawi": "", "answer_rumi": "", "kind": "short"},
                {"number": "2", "question_rumi": "Apakah warna kegemaran kamu?", "question_jawi": "", "answer_rumi": "", "kind": "short"}]}
        answerable = "dhuha" in messages[1]["content"].splitlines()[0]     # the QUESTION line
        return {**{k: QUESTION[k] for k in ("level", "type", "reference_answer_rumi", "reference_answer_jawi", "rubric")},
                "answerable": answerable}
    _fake_model(monkeypatch, replies)
    rec = library.add_book(_pdf(1), filename="latihan.pdf", title="Buku Latihan Ibadah", subject="fiqh", kind="exercise")
    library.process(rec["id"])
    (qfile,) = [x for x in library.drafts(rec["id"]) if x["kind"] == "questions"]
    data = json.loads(qfile["content"])
    assert [q["related_topic_id"] for q in data["questions"]] == ["fiqh_b1_solat_dhuha"]
    assert len(data["skipped"]) == 1 and not qfile["errors"]
    assert library.publish(rec["id"])["questions"] == 1


def test_warnings_point_the_teacher_to_unclear_and_broken_jawi():
    w = library.warnings_for("حكومڽ ادالah سنة [TIDAK JELAS] مؤكد")
    assert any("TIDAK JELAS" in x for x in w) and any("ادالah" in x for x in w)
    assert library.warnings_for("- **Rumi:** Hukumnya sunat. | **Jawi:** حكومڽ سنة.") == []
    assert library._keywords(["dua rakaat — دوا ركعة", "sunat muakkad"]) == ["dua rakaat", "دوا ركعة", "sunat muakkad"]


def test_a_token_with_non_ascii_text_is_just_invalid_not_a_server_error(monkeypatch, tmp_path):
    from backend.app import admin_auth

    monkeypatch.setattr(get_settings(), "admin_password", "pw-test")
    monkeypatch.setattr(get_settings(), "sqlite_path", tmp_path / "kafa.db")
    good = admin_auth.issue()["token"]
    assert admin_auth.valid(good)
    for bad in ("9999999999.é", "²99999999.abc", "٣.abc", good[:-1] + "é"):
        assert admin_auth.valid(bad) is False
