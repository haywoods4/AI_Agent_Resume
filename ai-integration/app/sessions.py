"""Local, single-reviewer login. Sessions expire on restart and after eight hours."""

import asyncio
import hashlib
import secrets
import time
from http.cookies import SimpleCookie

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

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


class Sessions:
    def __init__(self, settings):
        self.settings = settings
        self.active = {}
        self.attempts = []

    def valid(self, headers):
        cookie = SimpleCookie()
        try:
            cookie.load(headers.get(b"cookie", b"").decode())
            token = cookie[COOKIE].value if COOKIE in cookie else ""
        except Exception:
            return False
        self.active = {k: v for k, v in self.active.items() if v > time.monotonic()}
        return token in self.active

    def router(self):
        router = APIRouter(prefix="/api/v1/auth")

        @router.post("/login")
        async def login(data: Login, request: Request):
            now = time.monotonic()
            self.attempts = [t for t in self.attempts if t > now - 60]
            if len(self.attempts) >= 5:
                return JSONResponse({"error": "Too many attempts. Wait one minute."}, 429)
            self.attempts.append(now)
            if not self.settings.reviewer_password_hash or not self.settings.reviewer_username:
                return JSONResponse(
                    {"error": "Run scripts/configure_login.py to set up login."}, 503
                )
            valid = await asyncio.to_thread(
                verify_password, data.password, self.settings.reviewer_password_hash
            )
            if not (
                valid
                and secrets.compare_digest(
                    data.username.encode(), self.settings.reviewer_username.encode()
                )
            ):
                return JSONResponse({"error": "Username or password is incorrect."}, 401)
            # A fresh login revokes older sessions for this single reviewer.
            token = secrets.token_urlsafe(32)
            self.active = {token: now + 8 * 3600}
            response = JSONResponse({"username": self.settings.reviewer_username})
            response.set_cookie(
                COOKIE, token, httponly=True, samesite="strict", max_age=8 * 3600, path="/api"
            )
            return response

        @router.post("/logout")
        async def logout():
            self.active.clear()
            response = JSONResponse({"signed_out": True})
            response.delete_cookie(COOKIE, path="/api")
            return response

        return router
