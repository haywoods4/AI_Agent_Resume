from fastapi.testclient import TestClient

from app.main import create_app
from app.providers import DependencyError
from tests.conftest import FixturePolicy


def upload(
    client, request_id="req-1", content=b"Jane Secretname jane@private.test Python FastAPI SQL Git"
):
    return client.post(
        "/api/v1/evaluations",
        data={
            "request_id": request_id,
            "job_id": "backend-engineer",
            "candidate_email": "jane@private.test",
        },
        files={"resume": ("resume.txt", content, "text/plain")},
    )


def test_end_to_end_evaluation_lookup_review_and_replay(settings):
    app = create_app(settings, policy=FixturePolicy())
    with TestClient(app, headers={"Authorization": f"Bearer {settings.reviewer_token}"}) as client:
        first = upload(client)
        assert first.status_code == 200, first.text
        result = first.json()
        assert result["status"] == "READY_FOR_REVIEW"
        assert result["policy"]["status"] == "REQUIREMENTS_DOCUMENTED"
        assert result["requires_human_review"] is True
        assert "Secretname" not in first.text and "private.test" not in first.text
        assert upload(client).json()["evaluation_id"] == result["evaluation_id"]
        assert upload(client, content=b"Different resume").status_code == 409
        inquiry = client.post(
            "/api/v1/candidates/inquiry",
            json={
                "request_id": "lookup-1",
                "tenant_id": settings.tenant_id,
                "candidate_email": "jane@private.test",
                "query_type": "lookup_by_email",
            },
        )
        assert inquiry.json()["candidate"]["candidate_id"] == result["candidate_id"]
        assert inquiry.json()["source"] == "sqlite_fallback"
        review = {"outcome": "CONFIRMED_EVIDENCE", "reason": "VERIFIED_AGAINST_RESUME"}
        reviewed = client.post(f"/api/v1/evaluations/{result['evaluation_id']}/review", json=review)
        assert reviewed.json()["status"] == "REVIEWED"
        assert upload(client).json()["review"] == review
        raw_rows = str(app.state.store.db.execute("SELECT * FROM candidates").fetchall())
        assert "jane@private.test" not in raw_rows
        payload = app.state.store.db.execute("SELECT payload FROM evaluations").fetchone()[0]
        assert "Secretname" not in payload and "private.test" not in payload


def test_auth_tenant_boundary_and_invalid_upload(settings):
    with TestClient(create_app(settings, policy=FixturePolicy())) as client:
        assert client.get("/api/v1/jobs").status_code == 401
        client.headers["Authorization"] = f"Bearer {settings.reviewer_token}"
        assert (
            client.post(
                "/api/v1/candidates/inquiry",
                json={
                    "request_id": "r",
                    "tenant_id": "other",
                    "candidate_email": "a@b.test",
                    "query_type": "lookup_by_email",
                },
            ).status_code
            == 403
        )
        assert client.get("/api/v1/evaluations/missing").status_code == 404
        assert upload(client, content=b"").status_code == 400
        assert upload(client, content=b"x" * (513 * 1024)).status_code == 413


def test_provider_failure_persists_manual_review_and_survives_restart(settings):
    class FailedAgent:
        async def assess(self, facts, request_id):
            raise DependencyError("AI_UNAVAILABLE")

        async def close(self):
            pass

    with TestClient(
        create_app(settings, agent=FailedAgent(), policy=FixturePolicy()),
        headers={"Authorization": f"Bearer {settings.reviewer_token}"},
    ) as client:
        response = upload(client)
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "MANUAL_REVIEW_REQUIRED"
        assert result["failure_code"] == "AI_UNAVAILABLE"
        assert result["policy"] is None
    with TestClient(
        create_app(settings, policy=FixturePolicy()),
        headers={"Authorization": f"Bearer {settings.reviewer_token}"},
    ) as client:
        replay = upload(client).json()
        assert replay["evaluation_id"] == result["evaluation_id"]
        assert replay["failure_code"] == "AI_UNAVAILABLE"


def test_policy_failure_does_not_approve_candidate(settings):
    class FailedPolicy:
        async def evaluate(self, facts):
            raise DependencyError("POLICY_UNAVAILABLE")

        async def close(self):
            pass

    with TestClient(
        create_app(settings, policy=FailedPolicy()),
        headers={"Authorization": f"Bearer {settings.reviewer_token}"},
    ) as client:
        result = upload(client).json()
        assert result["status"] == "MANUAL_REVIEW_REQUIRED"
        assert result["failure_code"] == "POLICY_UNAVAILABLE"
        assert result["requires_human_review"] is True
