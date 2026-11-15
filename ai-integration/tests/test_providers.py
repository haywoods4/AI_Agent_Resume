import json
from dataclasses import replace

import httpx
import pytest

from app.privacy import PIIScrubbingMiddleware
from app.providers import DemoAgent, DependencyError, HermesClient, OPAClient


async def test_hermes_receives_only_canonical_facts_and_authenticates(settings):
    facts = PIIScrubbingMiddleware().scrub(
        ["Secret Name, email@private.test. Python."], "backend-engineer"
    )
    fixture = await DemoAgent().assess(facts, "test")
    calls = []

    async def handler(request):
        calls.append(request)
        assert request.headers["authorization"] == "Bearer local-key"
        assert request.headers["idempotency-key"] == "eval_safe"
        body = json.loads(request.content)
        assert "Secret" not in str(body) and "private.test" not in str(body)
        assert json.loads(body["messages"][1]["content"]) == facts.model_dump()
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "content": fixture.model_dump_json(),
                        },
                    }
                ]
            },
        )

    client = HermesClient(replace(settings, hermes_key="local-key"), httpx.MockTransport(handler))
    try:
        assert await client.assess(facts, "eval_safe") == fixture
        assert len(calls) == 1
    finally:
        await client.close()


async def test_hallucinated_evidence_is_rejected(settings):
    facts = PIIScrubbingMiddleware().scrub(["No technical skills here"], "backend-engineer")
    fixture = (await DemoAgent().assess(facts, "test")).model_dump()
    fixture["skills"][0]["status"] = "MENTIONED"

    async def handler(request):
        return httpx.Response(
            200,
            json={
                "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(fixture)}}]
            },
        )

    client = HermesClient(settings, httpx.MockTransport(handler))
    try:
        with pytest.raises(DependencyError, match="UNSUPPORTED_AGENT_CLAIM"):
            await client.assess(facts, "eval_test")
    finally:
        await client.close()


async def test_five_failures_open_circuit(settings):
    calls = 0

    async def handler(request):
        nonlocal calls
        calls += 1
        return httpx.Response(503)

    client = HermesClient(settings, httpx.MockTransport(handler))
    facts = PIIScrubbingMiddleware().scrub(["Python"], "backend-engineer")
    try:
        for index in range(5):
            with pytest.raises(DependencyError):
                await client.assess(facts, str(index))
        with pytest.raises(DependencyError, match="AI_CIRCUIT_OPEN"):
            await client.assess(facts, "six")
        assert calls == 5
    finally:
        await client.close()


async def test_missing_opa_document_is_not_treated_as_a_pass(settings):
    client = OPAClient(settings, httpx.MockTransport(lambda request: httpx.Response(200, json={})))
    try:
        with pytest.raises(DependencyError, match="POLICY_UNAVAILABLE"):
            await client.evaluate(PIIScrubbingMiddleware().scrub(["Python"], "backend-engineer"))
    finally:
        await client.close()
