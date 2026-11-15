from dataclasses import replace

from fastapi.testclient import TestClient

from app.main import create_app
from app.sessions import hash_password
from tests.conftest import FixturePolicy

ORIGIN = {"Origin": "http://127.0.0.1:5173"}
PASSWORD = "synthetic-password-only"


def client_for(settings):
    return TestClient(
        create_app(settings, policy=FixturePolicy()),
        base_url="http://127.0.0.1:8000",
        headers=ORIGIN,
    )


def register(client, name):
    return client.post("/api/v1/auth/register", json={"username": name, "password": PASSWORD})


def login(client, name):
    return client.post("/api/v1/auth/login", json={"username": name, "password": PASSWORD})


def test_bootstrap_persists_and_second_signup_is_pending(settings):
    with client_for(settings) as c:
        first = register(c, "Owner")
        assert first.status_code == 200 and first.json()["role"] == "owner"
        assert PASSWORD not in first.text and "password_hash" not in first.text
        assert c.get("/api/v1/jobs").status_code == 200
        second = register(c, "colleague")
        assert second.json()["role"] == "pending"
        assert c.get("/api/v1/jobs").status_code == 403
        assert c.get("/api/v1/evaluations").status_code == 403
        assert c.get("/api/v1/auth/accounts").status_code == 403
        assert c.get("/api/v1/auth/me").json()["role"] == "pending"
    with client_for(settings) as c:
        assert login(c, "owner").json()["role"] == "owner"
        assert c.get("/api/v1/jobs").status_code == 200
        assert login(c, "colleague").json()["role"] == "pending"


def test_existing_owner_preserved_duplicate_and_approval(settings):
    settings = replace(
        settings, reviewer_username="Justin", reviewer_password_hash=hash_password(PASSWORD)
    )
    with client_for(settings) as c:
        assert register(c, "JUSTIN").status_code == 409
        pending = register(c, "colleague").json()
        assert pending["role"] == "pending"
        assert c.post(f"/api/v1/auth/accounts/{pending['id']}/approve").status_code == 403
        assert register(c, "COLLEAGUE").status_code == 409
        assert login(c, "Justin").json()["role"] == "owner"
        accounts = c.get("/api/v1/auth/accounts").json()["accounts"]
        assert len(accounts) == 1 and "password_hash" not in str(accounts)
        assert c.post(f"/api/v1/auth/accounts/{pending['id']}/approve").status_code == 200
        # Reset throttling independently of persisted accounts by restarting the app.
    with client_for(settings) as c:
        user = login(c, "colleague").json()
        assert user["role"] == "reviewer" and user["id"] == pending["id"]
        assert c.get("/api/v1/jobs").status_code == 200
        assert c.get("/api/v1/auth/accounts").status_code == 403
        assert login(c, "Justin").status_code == 200


def test_registration_validation_origin_and_throttle(settings):
    with client_for(settings) as c:
        data = {"username": "valid-user", "password": PASSWORD}
        assert (
            c.post(
                "/api/v1/auth/register", json=data, headers={"Origin": "https://evil.example"}
            ).status_code
            == 403
        )
        assert (
            c.post("/api/v1/auth/register", json={**data, "password": "short"}).status_code == 400
        )
        assert (
            c.post("/api/v1/auth/register", json={**data, "username": "<script>"}).status_code
            == 400
        )
        for i in range(5):
            assert register(c, f"user{i}").status_code == 200
        assert register(c, "user6").status_code == 429


def test_pending_cannot_upload_or_read_audits(settings):
    with client_for(settings) as c:
        register(c, "owner")
        register(c, "pending")
        assert c.post("/api/v1/resumes/upload").status_code == 403
        assert c.get("/api/v1/audit-logs").status_code == 403
        assert c.post("/api/v1/auth/logout").status_code == 200
        assert c.get("/api/v1/auth/me").status_code == 401


def test_accounts_hash_only_session_isolation_and_cookie_approval(settings):
    import sqlite3

    from app.sessions import COOKIE

    app = create_app(settings, policy=FixturePolicy())
    with TestClient(app, base_url="http://127.0.0.1:8000", headers=ORIGIN) as c:
        owner = register(c, "owner").json()
        owner_cookie = c.cookies.get(COOKIE)
        pending = register(c, "pending").json()
        pending_cookie = c.cookies.get(COOKIE)
        c.cookies.clear()
        c.cookies.set(COOKIE, owner_cookie)
        assert c.get("/api/v1/auth/me").json()["id"] == owner["id"]
        assert c.post(f"/api/v1/auth/accounts/{pending['id']}/approve").status_code == 200
        c.cookies.clear()
        c.cookies.set(COOKIE, pending_cookie)
        assert c.get("/api/v1/auth/me").json()["role"] == "reviewer"
        assert c.get("/api/v1/jobs").status_code == 200
        c.post("/api/v1/auth/logout")
        c.cookies.clear()
        c.cookies.set(COOKIE, owner_cookie)
        assert c.get("/api/v1/jobs").status_code == 200
    from pathlib import Path

    with sqlite3.connect(Path(settings.database).parent / "reviewer-accounts.sqlite") as db:
        rows = db.execute("SELECT password_hash, approved_by FROM accounts").fetchall()
        assert all(row[0].startswith("scrypt$") and PASSWORD not in row[0] for row in rows)
        assert any(row[1] == owner["id"] for row in rows)


def test_concurrent_bootstrap_has_exactly_one_owner(settings):
    from concurrent.futures import ThreadPoolExecutor

    # Separate application instances share the same durable account store.
    def create(name):
        with client_for(settings) as c:
            response = register(c, name)
            assert response.status_code == 200
            return response.json()["role"]

    with ThreadPoolExecutor(max_workers=2) as executor:
        roles = list(executor.map(create, ["owner-a", "owner-b"]))
    assert sorted(roles) == ["owner", "pending"]
