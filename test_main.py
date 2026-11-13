import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import patch

from main import app
from database import Base, get_db

# Set up an isolated, in-memory SQLite database for testing
# StaticPool ensures the in-memory tables persist across test threads
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

# Override the database dependency to use the test database
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

# 1. Startup Test
def test_app_startup():
    """Verifies the application initializes and the client can connect."""
    response = client.get("/docs")  # Testing FastAPI's auto-generated docs endpoint
    assert response.status_code == 200

# 2. Authentication Test
def test_authentication_failure():
    """Verifies the endpoint rejects requests without a valid Bearer token."""
    response = client.post("/api/v1/resumes/upload", headers={})
    assert response.status_code == 401
    assert response.json()["detail"] == "UNAUTHORIZED"

# 3. Valid Request & Synthetic Privacy Check
def test_valid_request_and_privacy_check():
    """Verifies a valid upload and ensures no raw PII is echoed in the response."""
    file_content = b"Simulated resume content"
    files = {"file": ("resume.pdf", file_content, "application/pdf")}
    data = {
        "job_id": "job_101",
        "candidate_id": "cand_789"
    }
    headers = {"Authorization": "Bearer test-token"}
    
    response = client.post("/api/v1/resumes/upload", data=data, files=files, headers=headers)
    
    assert response.status_code == 200
    response_data = response.json()
    
    # Synthetic Privacy Check: Ensure no raw data leaks
    assert "candidate_name" not in response_data
    assert "resume_text" not in response_data
    assert "candidate_email" not in response_data
    
    # Verify contract response fields
    assert "evaluation_id" in response_data
    assert response_data["job_id"] == "job_101"
    assert response_data["verdict"] == "needs_review"
    assert response_data["policy_evaluations"] == "needs_review"

# 4. Invalid Request Test (File size boundary)
def test_invalid_request_file_too_large():
    """Verifies the 512 KiB file size limit rejects oversized files."""
    large_content = b"0" * (512 * 1024 + 10)  # Slightly over 512KB
    files = {"file": ("large.pdf", large_content, "application/pdf")}
    data = {
        "job_id": "job_101",
        "candidate_id": "cand_999"
    }
    headers = {"Authorization": "Bearer test-token"}
    
    response = client.post("/api/v1/resumes/upload", data=data, files=files, headers=headers)
    assert response.status_code == 413
    assert response.json()["detail"] == "Resume must not exceed 512 KiB"

# 5. Failed Database Write Test
def test_failed_database_write_rollback():
    """Verifies that a database commit failure triggers a rollback and returns 500."""
    file_content = b"Simulated resume content"
    files = {"file": ("resume.pdf", file_content, "application/pdf")}
    data = {
        "job_id": "job_fail",
        "candidate_id": "cand_fail"
    }
    headers = {"Authorization": "Bearer test-token"}
    
    # Mock the session commit to forcefully throw an exception and spy on rollback
    with patch("sqlalchemy.orm.Session.commit", side_effect=Exception("Simulated DB Write Failure")), \
         patch("sqlalchemy.orm.Session.rollback") as mock_rollback:
        response = client.post("/api/v1/resumes/upload", data=data, files=files, headers=headers)
        
        assert response.status_code == 500
        assert response.json()["detail"] == "Database write failed"
        mock_rollback.assert_called()


# 6. Audit Logs Endpoint Stub Test
def test_audit_logs_stub():
    """Verifies the GET /api/v1/audit-logs contract stub works with auth."""
    headers = {"Authorization": "Bearer test-token"}
    response = client.get("/api/v1/audit-logs", headers=headers)
    assert response.status_code == 200
    assert response.json() == {"message": "Audit logs endpoint stub"}
