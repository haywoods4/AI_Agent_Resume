from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.sessions import hash_password
from app.settings import codespaces_origin
from tests.conftest import FixturePolicy


def test_exact_codespace_origin(monkeypatch):
    monkeypatch.setenv("CODESPACES", "true")
    monkeypatch.setenv("CODESPACE_NAME", "safe-name-abc")
    monkeypatch.setenv("GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN", "app.github.dev")
    assert codespaces_origin() == "https://safe-name-abc-5173.app.github.dev"
    monkeypatch.setenv("GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN", "evil.example")
    with pytest.raises(ValueError):
        codespaces_origin()


def test_codespaces_cookie_and_cross_codespace_rejection(settings):
    origin = "https://safe-name-abc-5173.app.github.dev"
    config = replace(
        settings,
        browser_origin=origin,
        reviewer_username="owner",
        reviewer_password_hash=hash_password("synthetic-password-only"),
    )
    with TestClient(
        create_app(config, policy=FixturePolicy()), base_url=origin, headers={"Origin": origin}
    ) as client:
        data = {"username": "owner", "password": "synthetic-password-only"}
        response = client.post("/api/v1/auth/login", json=data)
        assert response.status_code == 200
        assert "secure" in response.headers["set-cookie"].lower()
        assert client.get("/api/v1/jobs").status_code == 200
        assert (
            client.post(
                "/api/v1/auth/logout", headers={"Origin": "https://other-5173.app.github.dev"}
            ).status_code
            == 403
        )
        assert client.post("/api/v1/auth/logout", headers={"Origin": ""}).status_code == 403
        assert client.post("/api/v1/auth/logout").status_code == 200
