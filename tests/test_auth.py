from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def auth_client(tmp_path, monkeypatch):
    """Spin up the FastAPI app with bearer auth enabled and an isolated token."""
    token_file = tmp_path / "token"
    token_file.write_text("test-token-value")
    monkeypatch.setenv("CODEWATCH_REQUIRE_TOKEN", "1")
    monkeypatch.setenv("CODEWATCH_TOKEN_PATH", str(token_file))

    # Re-import to pick up fresh env. FastAPI apps memoize dep graphs at
    # include_router time, but since we only gate behind the env lookup inside
    # require_token the dep runs fresh each request.
    from backend.main import create_app

    app = create_app()
    return TestClient(app), "test-token-value"


def test_health_endpoints_do_not_require_auth(auth_client):
    client, _ = auth_client
    assert client.get("/livez").status_code == 200
    # /healthz may be 503 if deps are down in CI; either way it must not be 401.
    assert client.get("/healthz").status_code in (200, 503)


def test_protected_route_rejects_missing_token(auth_client):
    client, _ = auth_client
    resp = client.get("/api/projects")
    assert resp.status_code == 401
    assert resp.headers.get("WWW-Authenticate") == "Bearer"


def test_protected_route_rejects_wrong_token(auth_client):
    client, _ = auth_client
    resp = client.get("/api/projects", headers={"Authorization": "Bearer wrong-token"})
    assert resp.status_code == 401


def test_protected_route_accepts_valid_token(auth_client):
    client, token = auth_client
    resp = client.get("/api/projects", headers={"Authorization": f"Bearer {token}"})
    # Could be 200 with [] or 500 if DB not wired; either way it must not be 401.
    assert resp.status_code != 401


def test_auth_disabled_by_default(tmp_path, monkeypatch):
    monkeypatch.delenv("CODEWATCH_REQUIRE_TOKEN", raising=False)
    from backend.main import create_app

    app = create_app()
    client = TestClient(app)
    # With auth disabled, unauthenticated access returns the list, not 401.
    resp = client.get("/api/projects")
    assert resp.status_code == 200


def test_ws_token_helper(monkeypatch, tmp_path):
    token_file = tmp_path / "token"
    token_file.write_text("ws-token")
    monkeypatch.setenv("CODEWATCH_REQUIRE_TOKEN", "1")
    monkeypatch.setenv("CODEWATCH_TOKEN_PATH", str(token_file))

    from backend.core.auth import check_ws_token

    assert check_ws_token("ws-token") is True
    assert check_ws_token("bad") is False
    assert check_ws_token(None) is False

    monkeypatch.delenv("CODEWATCH_REQUIRE_TOKEN")
    # Auth disabled → always True, even with no token.
    assert check_ws_token(None) is True
