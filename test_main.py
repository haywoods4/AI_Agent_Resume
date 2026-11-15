"""I verify the shared Alpha contract against the integrated backend."""

import sys
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent / "ai-integration"))
from app.main import create_app  # noqa: E402
from app.providers import DependencyError  # noqa: E402
from app.settings import Settings  # noqa: E402
from tests.conftest import FixturePolicy  # noqa: E402


@pytest.fixture
def client(tmp_path):
    settings = Settings(
        database=str(tmp_path / "alpha.sqlite"),
        mode="demo",
        reviewer_token="alpha-reviewer-secret-24-characters",
        hmac_key="alpha-hmac-independent-secret-24",
    )
    application = create_app(settings, policy=FixturePolicy())
    with TestClient(
        application, headers={"Authorization": f"Bearer {settings.reviewer_token}"}
    ) as api:
        yield api


def submit(client, request_id="alpha", text=b"Python FastAPI SQL Git", **fields):
    return client.post(
        "/api/v1/resumes/upload",
        data={"job_id": "backend-engineer", "request_id": request_id, **fields},
        files={"file": ("resume.txt", text, "text/plain")},
    )


def test_upload_optional_identity_and_stable_retry(client):
    result = submit(client).json()
    assert result["verdict"] == "PASS"
    assert result["policy_status"] == "allowed"
    assert result["requires_human_review"] is True
    assert result["timestamp"]
    assert result["sanitized_payload"]["skills"] == ["fastapi", "git", "python", "sql"]
    assert submit(client).json() == result
    assert submit(client, text=b"Python").status_code == 409
    assert client.get("/api/v1/audit-logs").json()["total_records"] == 1


def test_supplied_candidate_id_and_redaction(client):
    identity = str(uuid4())
    result = submit(
        client, text=b"Secret Name secret@example.invalid Python", candidate_id=identity
    )
    assert result.status_code == 200
    assert result.json()["candidate_id"] == identity
    assert result.json()["verdict"] == "FAIL"
    assert "Secret Name" not in result.text
    assert "secret@example.invalid" not in result.text
    assert "secret@example.invalid" not in client.get("/api/v1/audit-logs").text


def test_invalid_and_arbitrary_bearer_rejected(client):
    for token in ("", "Bearer anything", "Bearer "):
        assert (
            client.get(
                "/api/v1/audit-logs", headers={"Authorization": token}
            ).status_code
            == 401
        )
        assert (
            client.post(
                "/api/v1/resumes/upload", headers={"Authorization": token}
            ).status_code
            == 401
        )
    assert submit(client, candidate_id="email@example.invalid").status_code == 400
    assert submit(client, text=b"").status_code == 400
    assert submit(client, text=b"x" * (513 * 1024)).status_code == 413
    assert client.get("/api/v1/audit-logs?limit=1000").status_code == 400
    assert (
        client.get("/api/v1/audit-logs?start_date=2026-01-01T00:00:00").status_code
        == 400
    )


def test_audit_filters_and_pagination(client):
    submit(client, "pass")
    submit(client, "fail", b"Python")
    assert client.get("/api/v1/audit-logs?verdict=PASS").json()["total_records"] == 1
    assert client.get("/api/v1/audit-logs?job_id=missing").json()["total_records"] == 0
    page = client.get("/api/v1/audit-logs?limit=1&offset=1").json()
    assert page["total_records"] == 2 and len(page["logs"]) == 1
    assert page["logs"][0]["verdict"] == "PASS"
    assert page["logs"][0]["job_requirements"]
    assert page["logs"][0]["approved_inputs"]
    assert page["logs"][0]["model_version"]
    assert page["logs"][0]["policy_result"]


def test_failure_is_audited_needs_review(client):
    async def failed(facts):
        raise DependencyError("POLICY_UNAVAILABLE")

    client.app.state.pipeline.policy.evaluate = failed
    result = submit(client).json()
    assert result["verdict"] == "NEEDS_REVIEW"
    assert result["policy_evaluations"] == []
    assert (
        client.get("/api/v1/audit-logs?verdict=NEEDS_REVIEW").json()["total_records"]
        == 1
    )


def test_audit_tenant_isolation(client):
    submit(client)
    settings = replace(client.app.state.pipeline.settings, tenant_id="another-tenant")
    with TestClient(
        create_app(settings, policy=FixturePolicy()),
        headers={"Authorization": f"Bearer {settings.reviewer_token}"},
    ) as other:
        assert other.get("/api/v1/audit-logs").json()["total_records"] == 0


def test_failed_write_rolls_back_and_can_retry(client):
    db = client.app.state.store.db
    db.execute(
        "CREATE TRIGGER fail_save BEFORE INSERT ON evaluations "
        "BEGIN SELECT RAISE(ABORT, 'fixture failure'); END"
    )
    result = submit(client)
    assert result.status_code == 503
    assert result.json()["error"] == "DEPENDENCY"
    assert db.execute("SELECT count(*) FROM evaluations").fetchone()[0] == 0
    assert db.execute("SELECT count(*) FROM decision_audit").fetchone()[0] == 0
    db.execute("DROP TRIGGER fail_save")
    assert submit(client).json()["verdict"] == "PASS"


def test_error_contract_is_documented_and_does_not_echo_input(client):
    schema = client.get("/openapi.json").json()
    responses = schema["paths"]["/api/v1/resumes/upload"]["post"]["responses"]
    assert {"400", "401", "413", "503"} <= set(responses)
    result = submit(client, candidate_id="private@example.invalid")
    assert result.json()["error"] == "VALIDATION_ERROR"
    assert "private@example.invalid" not in result.text
