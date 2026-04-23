from __future__ import annotations

from fastapi.testclient import TestClient


def test_livez_returns_ok(monkeypatch):
    monkeypatch.delenv("CODEWATCH_REQUIRE_TOKEN", raising=False)
    from backend.main import create_app

    client = TestClient(create_app())
    resp = client.get("/livez")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_healthz_reports_checks(monkeypatch):
    monkeypatch.delenv("CODEWATCH_REQUIRE_TOKEN", raising=False)
    from backend.main import create_app

    client = TestClient(create_app())
    resp = client.get("/healthz")
    # DB works (even in test mode). Ollama may be down — either outcome is valid.
    assert resp.status_code in (200, 503)
    body = resp.json()
    assert "checks" in body
    assert "db" in body["checks"]
    assert "ollama" in body["checks"]
    assert body["checks"]["db"] is True
