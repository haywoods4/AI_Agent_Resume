"""Local classroom account login. Sessions expire on restart and after eight hours."""

import asyncio
import hashlib
import os
import secrets
import sqlite3
import time
import uuid
from contextlib import contextmanager
from http.cookies import SimpleCookie
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

COOKIE = "resume_session"
ORIGINS = {
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "http://127.0.0.1:8000",
    "http://localhost:8000",
}


def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1).hex()
    return f"scrypt${salt}${digest}"


def verify_password(password, encoded):
    try:
        scheme, salt, _ = encoded.split("$")
        return scheme == "scrypt" and secrets.compare_digest(hash_password(password, salt), encoded)
    except (ValueError, TypeError):
        return False


class Login(BaseModel):
    username: str = Field(max_length=128)
    password: str = Field(max_length=256)


class Register(Login):
    password: str = Field(min_length=12, max_length=256)

    @field_validator("username")
    @classmethod
    def username_format(cls, value):
        value = value.strip().lower()
        if not 3 <= len(value) <= 64 or not all(
            c.isascii() and (c.isalnum() or c in "._-") for c in value
        ):
            raise ValueError("Use 3–64 letters, numbers, dots, dashes or underscores")
        return value


class Sessions:
    def __init__(self, settings):
        self.settings = settings
        self.active = {}
        self.attempts = []
        self.path = Path(settings.database).parent / "reviewer-accounts.sqlite"

    @contextmanager
    def database(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path)
        os.chmod(self.path, 0o600)
        db.row_factory = sqlite3.Row
        db.execute(
            "CREATE TABLE IF NOT EXISTS accounts (id TEXT PRIMARY KEY, "
            "username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, "
            "role TEXT NOT NULL, approved_by TEXT)"
        )
        try:
            with db:
                yield db
        finally:
            db.close()

    def identity(self, headers):
        cookie = SimpleCookie()
        try:
            cookie.load(headers.get(b"cookie", b"").decode())
            token = cookie[COOKIE].value if COOKIE in cookie else ""
        except Exception:
            return None
        self.active = {k: v for k, v in self.active.items() if v[0] > time.monotonic()}
        session = self.active.get(token)
        if not session:
            return None
        user = session[1]
        if user["id"] != self.settings.reviewer_id:
            with self.database() as db:
                row = db.execute("SELECT role FROM accounts WHERE id=?", (user["id"],)).fetchone()
            if not row:
                return None
            user = {**user, "role": row["role"]}
        return user

    def valid(self, headers):
        return self.identity(headers) is not None

    def throttle(self):
        now = time.monotonic()
        self.attempts = [t for t in self.attempts if t > now - 60]
        if len(self.attempts) >= 5:
            return JSONResponse({"error": "Too many attempts. Wait one minute."}, 429)
        self.attempts.append(now)
        return None

    def response(self, user):
        token = secrets.token_urlsafe(32)
        self.active = {
            k: v
            for k, v in self.active.items()
            if v[1]["id"] != user["id"] and v[0] > time.monotonic()
        }
        self.active[token] = (time.monotonic() + 8 * 3600, user)
        response = JSONResponse(user)
        response.set_cookie(
            COOKIE,
            token,
            httponly=True,
            secure=bool(self.settings.browser_origin),
            samesite="strict",
            max_age=8 * 3600,
            path="/api",
        )
        return response

    def router(self):
        router = APIRouter(prefix="/api/v1/auth")

        @router.post("/register")
        async def register(data: Register):
            limited = self.throttle()
            if limited is not None:
                return limited
            encoded = await asyncio.to_thread(hash_password, data.password)
            with self.database() as db:
                db.execute("BEGIN IMMEDIATE")
                existing = db.execute("SELECT 1 FROM accounts LIMIT 1").fetchone()
                reserved = self.settings.reviewer_username.strip().lower()
                if reserved and data.username == reserved:
                    return JSONResponse(
                        {"error": "That username is unavailable. Sign in instead."}, 409
                    )
                # Existing configured accounts can never be replaced by registration.
                role = (
                    "owner"
                    if not existing
                    and not (
                        self.settings.reviewer_username or self.settings.reviewer_password_hash
                    )
                    else "pending"
                )
                user = {
                    "id": "account_" + uuid.uuid4().hex,
                    "username": data.username,
                    "role": role,
                }
                try:
                    db.execute(
                        "INSERT INTO accounts VALUES (?, ?, ?, ?, ?)",
                        (
                            user["id"],
                            data.username,
                            encoded,
                            role,
                            "local-bootstrap" if role == "owner" else None,
                        ),
                    )
                except sqlite3.IntegrityError:
                    return JSONResponse(
                        {"error": "That username is unavailable. Sign in instead."}, 409
                    )
            return self.response(user)

        @router.post("/login")
        async def login(data: Login):
            limited = self.throttle()
            if limited is not None:
                return limited
            name = data.username.strip().lower()
            if (
                name == self.settings.reviewer_username.strip().lower()
                and self.settings.reviewer_password_hash
            ):
                encoded = self.settings.reviewer_password_hash
                user = {
                    "id": self.settings.reviewer_id,
                    "username": self.settings.reviewer_username,
                    "role": "owner",
                }
            else:
                with self.database() as db:
                    row = db.execute("SELECT * FROM accounts WHERE username=?", (name,)).fetchone()
                encoded = row["password_hash"] if row else hash_password("unused-dummy-password")
                user = (
                    {"id": row["id"], "username": row["username"], "role": row["role"]}
                    if row
                    else None
                )
            valid = await asyncio.to_thread(verify_password, data.password, encoded)
            if not valid or user is None:
                return JSONResponse({"error": "Username or password is incorrect."}, 401)
            return self.response(user)

        @router.get("/me")
        async def me(request: Request):
            return request.state.identity

        @router.get("/accounts")
        async def accounts(request: Request):
            if request.state.identity["role"] != "owner":
                return JSONResponse({"error": "Owner access required."}, 403)
            with self.database() as db:
                rows = db.execute(
                    "SELECT id, username, role FROM accounts WHERE role='pending'"
                ).fetchall()
            return {"accounts": [dict(row) for row in rows]}

        @router.post("/accounts/{account_id}/approve")
        async def approve(account_id: str, request: Request):
            actor = request.state.identity
            if actor["role"] != "owner":
                return JSONResponse({"error": "Owner access required."}, 403)
            with self.database() as db:
                result = db.execute(
                    "UPDATE accounts SET role='reviewer', approved_by=? "
                    "WHERE id=? AND role='pending'",
                    (actor["id"], account_id),
                )
            if result.rowcount == 0:
                return JSONResponse({"error": "Pending account not found."}, 404)
            return {"approved": True}

        @router.post("/logout")
        async def logout(request: Request):
            actor = request.state.identity
            self.active = {k: v for k, v in self.active.items() if v[1]["id"] != actor["id"]}
            response = JSONResponse({"signed_out": True})
            response.delete_cookie(COOKIE, path="/api")
            return response

        return router
