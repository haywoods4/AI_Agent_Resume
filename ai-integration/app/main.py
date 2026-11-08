import secrets
import sqlite3
import time
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from redis.asyncio import Redis

from app.contracts import Evaluation, Inquiry, Review
from app.lookup import CandidateLookup
from app.pipeline import ScreeningPipeline
from app.privacy import PrivacyError, jobs
from app.providers import DemoAgent, DependencyError, HermesClient, OPAClient
from app.settings import Settings
from app.store import ConflictError, Store


class RequestGuard:
    """Authenticate before buffering bodies; bound requests below multipart's disk-spool size."""

    def __init__(self, app, settings: Settings):
        self.app, self.settings = app, settings
        self.count = 0
        self.reset = time.monotonic() + 60

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not scope["path"].startswith("/api/"):
            return await self.app(scope, receive, send)
        headers = dict(scope.get("headers", []))
        expected = f"Bearer {self.settings.reviewer_token}".encode()
        if not secrets.compare_digest(headers.get(b"authorization", b""), expected):
            return await JSONResponse({"error": "UNAUTHORIZED"}, 401)(scope, receive, send)
        if time.monotonic() >= self.reset:
            self.count, self.reset = 0, time.monotonic() + 60
        self.count += 1
        if self.count > 120:
            return await JSONResponse(
                {"error": "RATE_LIMITED"}, 429, headers={"Retry-After": "60"}
            )(scope, receive, send)
        maximum = 600 * 1024 if scope["path"] == "/api/v1/evaluations" else 16384
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body.extend(message.get("body", b""))
            if len(body) > maximum:
                return await JSONResponse({"error": "PAYLOAD_TOO_LARGE"}, 413)(scope, receive, send)
            if not message.get("more_body", False):
                break
        delivered = False

        async def buffered_receive():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        async def private_send(message):
            if message["type"] == "http.response.start":
                message["headers"] += [
                    (b"cache-control", b"no-store"),
                    (b"x-content-type-options", b"nosniff"),
                ]
            await send(message)

        await self.app(scope, buffered_receive, private_send)


def create_app(settings: Settings | None = None, agent=None, policy=None, cache=None):
    settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app):
        settings.validate()
        jobs()  # Fail startup for invalid job configuration before processing any resume.
        store = Store(settings.database)
        actual_agent = agent or (DemoAgent() if settings.mode == "demo" else HermesClient(settings))
        actual_policy = policy or OPAClient(settings)
        actual_cache = cache or (
            Redis.from_url(
                settings.redis_url,
                socket_timeout=0.3,
                socket_connect_timeout=0.3,
                max_connections=8,
                decode_responses=True,
            )
            if settings.redis_url
            else None
        )
        app.state.store = store
        app.state.pipeline = ScreeningPipeline(settings, store, actual_agent, actual_policy)
        app.state.lookup = CandidateLookup(settings, store, actual_cache)
        try:
            yield
        finally:
            await actual_agent.close()
            await actual_policy.close()
            if actual_cache is not None:
                await actual_cache.aclose()
            store.close()

    app = FastAPI(title="Resume AI integration", version="0.1.0", lifespan=lifespan)
    app.add_middleware(RequestGuard, settings=settings)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, error):
        # FastAPI normally echoes rejected input; omit it to avoid reflecting contact data.
        return JSONResponse(
            {
                "error": "VALIDATION_ERROR",
                "fields": [{"location": e["loc"], "type": e["type"]} for e in error.errors()],
            },
            400,
        )

    @app.exception_handler(PrivacyError)
    async def invalid_document(request, error):
        return JSONResponse({"error": "VALIDATION_ERROR", "message": str(error)}, 400)

    @app.exception_handler(ConflictError)
    async def conflict(request, error):
        return JSONResponse({"error": "CONFLICT", "message": str(error)}, 409)

    @app.exception_handler(PermissionError)
    async def forbidden(request, error):
        return JSONResponse({"error": "FORBIDDEN"}, 403)

    @app.exception_handler(sqlite3.Error)
    async def database_error(request, error):
        return JSONResponse({"error": "DEPENDENCY", "message": "Result could not be saved"}, 503)

    @app.exception_handler(DependencyError)
    async def dependency_error(request, error):
        status = 429 if error.code == "CAPACITY_EXCEEDED" else 503
        return JSONResponse({"error": error.code}, status)

    @app.get("/health")
    async def health():
        return {"status": "ok", "mode": settings.mode}

    @app.get("/api/v1/jobs")
    async def job_catalog():
        return jobs()

    @app.post("/api/v1/candidates/inquiry")
    async def inquiry(payload: Inquiry):
        return await app.state.lookup.inquiry(payload)

    @app.post("/api/v1/evaluations", response_model=Evaluation)
    async def evaluate(
        request_id: Annotated[str, Form(min_length=1, max_length=128, pattern=r"^[a-zA-Z0-9_-]+$")],
        job_id: Annotated[str, Form(max_length=64)],
        candidate_email: Annotated[str, Form(max_length=254)],
        resume: Annotated[UploadFile, File()],
        candidate_phone: Annotated[str | None, Form(max_length=30)] = None,
    ):
        content = await resume.read(512 * 1024 + 1)
        await resume.close()
        if len(content) > 512 * 1024:
            raise HTTPException(413, "Resume must not exceed 512 KiB")
        return await app.state.pipeline.evaluate(
            request_id, job_id, candidate_email, candidate_phone, content, resume.filename or ""
        )

    @app.get("/api/v1/evaluations", response_model=list[Evaluation])
    async def evaluations():
        return app.state.store.list_evaluations(settings.tenant_id)

    @app.get("/api/v1/evaluations/{evaluation_id}", response_model=Evaluation)
    async def evaluation(evaluation_id: str):
        result = app.state.store.evaluation(settings.tenant_id, evaluation_id)
        if result is None:
            raise HTTPException(404, "Evaluation not found")
        return result

    @app.post("/api/v1/evaluations/{evaluation_id}/review", response_model=Evaluation)
    async def review(evaluation_id: str, payload: Review):
        if evaluation_id in app.state.pipeline.active_evaluations:
            raise ConflictError("Evaluation is still processing")
        if app.state.store.evaluation(settings.tenant_id, evaluation_id) is None:
            raise HTTPException(404, "Evaluation not found")
        result = app.state.store.review(
            settings.tenant_id, settings.reviewer_id, evaluation_id, payload
        )
        return result

    return app


app = create_app()
