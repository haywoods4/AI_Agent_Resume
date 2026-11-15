from dataclasses import replace

from fastapi.testclient import TestClient

from app.main import create_app
from app.sessions import COOKIE, hash_password, verify_password
from tests.conftest import FixturePolicy


def client_for(settings):
    config = replace(
        settings,
        reviewer_username="reviewer",
        reviewer_password_hash=hash_password("synthetic-password-only"),
    )
    return TestClient(
        create_app(config, policy=FixturePolicy()),
        base_url="http://127.0.0.1:8000",
        headers={"Origin": "http://127.0.0.1:5173"},
    )


def test_password_hash():
    encoded = hash_password("synthetic-password-only")
    assert "synthetic-password-only" not in encoded
    assert verify_password("synthetic-password-only", encoded)
    assert not verify_password("wrong", encoded)
    assert not verify_password("wrong", "bad")


def test_login_cookie_access_logout_and_revocation(settings):
    with client_for(settings) as client:
        assert client.get("/api/v1/jobs").status_code == 401
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "reviewer", "password": "synthetic-password-only"},
        )
        assert response.status_code == 200
        assert "httponly" in response.headers["set-cookie"].lower()
        assert "samesite=strict" in response.headers["set-cookie"].lower()
        token = client.cookies.get(COOKIE)
        assert client.get("/api/v1/jobs").status_code == 200
        assert client.post("/api/v1/auth/logout").status_code == 200
        assert client.get("/api/v1/jobs").status_code == 401
        client.cookies.set(COOKIE, token)
        assert client.get("/api/v1/jobs").status_code == 401


def test_wrong_login_throttle_and_cross_origin(settings):
    with client_for(settings) as client:
        payload = {"username": "reviewer", "password": "wrong"}
        assert (
            client.post(
                "/api/v1/auth/login", json=payload, headers={"Origin": "https://evil.example"}
            ).status_code
            == 403
        )
        for _ in range(5):
            assert client.post("/api/v1/auth/login", json=payload).status_code == 401
        assert client.post("/api/v1/auth/login", json=payload).status_code == 429


def test_login_requires_configuration(settings):
    with TestClient(
        create_app(settings, policy=FixturePolicy()),
        base_url="http://127.0.0.1:8000",
        headers={"Origin": "http://127.0.0.1:5173"},
    ) as client:
        response = client.post("/api/v1/auth/login", json={"username": "x", "password": "x"})
        assert response.status_code == 503


def test_expiration_and_new_login_revoke_old_session(settings, monkeypatch):
    import app.sessions as sessions

    clock = [1000.0]
    monkeypatch.setattr(sessions.time, "monotonic", lambda: clock[0])
    with client_for(settings) as client:
        payload = {"username": "reviewer", "password": "synthetic-password-only"}
        client.post("/api/v1/auth/login", json=payload)
        first = client.cookies.get(COOKIE)
        client.post("/api/v1/auth/login", json=payload)
        second = client.cookies.get(COOKIE)
        assert first != second
        client.cookies.clear()
        client.cookies.set(COOKIE, first)
        assert client.get("/api/v1/jobs").status_code == 401
        client.cookies.clear()
        client.cookies.set(COOKIE, second)
        assert client.get("/api/v1/jobs").status_code == 200
        clock[0] += 8 * 3600 + 1
        assert client.get("/api/v1/jobs").status_code == 401
