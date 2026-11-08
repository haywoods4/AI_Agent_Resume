import os
import socket
import subprocess
import time
from dataclasses import replace
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from redis.asyncio import Redis

from app.contracts import Inquiry
from app.lookup import CandidateLookup
from app.main import create_app
from app.privacy import identifier_hash
from app.store import Store
from tests.test_api import upload

OPA = Path(__file__).resolve().parent.parent / "tools" / "opa"


@pytest.mark.skipif(not OPA.exists(), reason="Run scripts/setup_opa.py to test the real OPA engine")
def test_real_opa_end_to_end(settings):
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    process = subprocess.Popen(
        [str(OPA), "run", "--server", "--addr", f"127.0.0.1:{port}", "policies/"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        with httpx.Client(trust_env=False, timeout=0.3) as health:
            for _ in range(40):
                try:
                    if health.get(f"http://127.0.0.1:{port}/health").status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                time.sleep(0.05)
            else:
                pytest.fail("OPA server did not start")
        settings = replace(
            settings, opa_url=f"http://127.0.0.1:{port}/v1/data/resume/screening/result"
        )
        with TestClient(
            create_app(settings),
            headers={
                "Authorization": f"Bearer {settings.reviewer_token}",
            },
        ) as client:
            result = upload(client).json()
            assert result["status"] == "READY_FOR_REVIEW", result
            assert result["policy"]["policy_version"] == "job-evidence-v1"
            assert result["policy"]["requires_human_review"] is True
            missing = upload(client, "missing", b"Python only").json()
            assert missing["policy"]["missing_skills"] == ["fastapi", "git", "sql"]
            assert missing["policy"]["status"] == "MISSING_REQUIRED_EVIDENCE"
    finally:
        process.terminate()
        process.wait(timeout=5)


@pytest.mark.skipif(not os.getenv("TEST_REDIS_URL"), reason="TEST_REDIS_URL is not configured")
async def test_real_redis_cache_and_sensitive_record_bypass(settings):
    cache = Redis.from_url(os.environ["TEST_REDIS_URL"], decode_responses=True)
    store = Store(settings.database)
    lookup = CandidateLookup(settings, store, cache)
    email = "candidate@fixture.invalid"
    digest = identifier_hash(settings.hmac_key, settings.tenant_id, "email", email)
    store.candidate(settings.tenant_id, digest)
    key = f"cand:{settings.tenant_id}:{digest}"
    await cache.delete(key)
    try:
        payload = Inquiry(
            request_id="one",
            tenant_id=settings.tenant_id,
            candidate_email=email,
            query_type="lookup_by_email",
        )
        assert (await lookup.inquiry(payload))["source"] == "sqlite_fallback"
        assert (await lookup.inquiry(payload.model_copy(update={"request_id": "two"})))[
            "source"
        ] == "redis"
        assert 0 < await cache.ttl(key) <= 900
        assert email not in await cache.get(key)
        store.db.execute("UPDATE candidates SET phi_flag=1")
        assert (await lookup.inquiry(payload.model_copy(update={"request_id": "three"})))[
            "source"
        ] == "sqlite_fallback"
    finally:
        await cache.delete(key)
        await cache.aclose()
        store.close()
