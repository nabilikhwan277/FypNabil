from fastapi.testclient import TestClient

from backend.app.config import get_settings
from backend.app.main import app


def test_health_ok_without_loading_models(monkeypatch):
    monkeypatch.setattr("backend.app.main.settings.preload_models", False)
    with TestClient(app) as client:
        r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["llm_model"] == get_settings().llm_model_id
    assert body["warm_up"] == "idle"


def test_eval_summary_only_for_the_admin(monkeypatch, tmp_path):
    monkeypatch.setattr("backend.app.main.settings.preload_models", False)
    monkeypatch.setattr(get_settings(), "admin_password", "pw-test")
    monkeypatch.setattr(get_settings(), "sqlite_path", tmp_path / "kafa.db")   # the token secret goes here
    with TestClient(app) as client:
        assert client.get("/api/eval/summary").status_code == 401
        tok = client.post("/api/admin/login", json={"password": "pw-test"}).json()["token"]
        r = client.get("/api/eval/summary", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    body = r.json()
    assert {"targets", "runs", "spend", "labels"} <= set(body)
    assert body["targets"]["qwk"]["target"] == 0.70


def test_health_does_not_call_a_dead_colab_link_loaded(monkeypatch):
    from backend.app import remote_llm

    monkeypatch.setattr("backend.app.main.settings.preload_models", False)
    monkeypatch.setattr(remote_llm, "endpoint", lambda: ("https://dead.example", "k"))
    monkeypatch.setattr("backend.app.main.llm_loaded", lambda: False)
    calls = []
    monkeypatch.setattr(remote_llm, "check", lambda *a: calls.append(a) or {"ok": False, "error": "down"})
    remote_llm._served.clear(); remote_llm._dead.clear()
    with TestClient(app) as client:
        assert client.get("/api/health").json()["llm_loaded"] is False
        assert client.get("/api/health").json()["llm_loaded"] is False
    assert len(calls) == 1            # the second health call did not wait for the dead link again
    monkeypatch.setattr(remote_llm, "check", lambda *a: {"ok": True, "model": "qwen"})
    remote_llm._dead.clear()
    with TestClient(app) as client:
        assert client.get("/api/health").json()["llm_loaded"] is True
    remote_llm._served.clear(); remote_llm._dead.clear()
