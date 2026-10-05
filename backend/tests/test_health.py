from fastapi.testclient import TestClient

from backend.app.main import app


def test_health_ok_without_loading_models(monkeypatch):
    monkeypatch.setattr("backend.app.main.settings.preload_models", False)
    with TestClient(app) as client:
        r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["llm_model"] == "mesolitica/Malaysian-Llama-3.2-1B-Instruct"
    assert body["warm_up"] == "idle"
