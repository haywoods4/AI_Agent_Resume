from fastapi import FastAPI, Depends, Form, File, UploadFile, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Annotated
import uuid

from database import get_db, EvaluationRecord

app = FastAPI(title = "AI Resume Evaluator API (Alpha)")

# FIX: Locked down CORS to localhost instead of ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins = ["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods = ["GET", "POST"],
    allow_headers = ["Authorization", "Content-Type"],
)

# FIX: Added basic auth to bound the endpoint
async def verify_reviewer(authorization: Annotated[str | None, Header()] = None):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="UNAUTHORIZED")
    return authorization

# FIX: Renamed endpoint from /evaluate_resume to match frontend contract
@app.post("/api/v1/resumes/upload")
async def evaluate_resume(
    job_id: Annotated[str, Form(min_length=1, max_length=64)],
    candidate_id: Annotated[str, Form(min_length=1, max_length=128)],
    file: Annotated[UploadFile, File()],
    db: Session = Depends(get_db),
    token: str = Depends(verify_reviewer)
):
    # FIX: Bound request body size (Max 512 KiB)
    content = await file.read(512 * 1024 + 1)
    if len(content) > 512 * 1024:
        raise HTTPException(status_code=413, detail="Resume must not exceed 512 KiB")
    await file.close()

    # Simulate AI evaluation (replace with actual AI model integration)
    # FIX: Kept unmistakably separate from a real evaluation by marking as simulation
    ai_feedback = "SIMULATION ONLY: Awaiting Integration Lead AI Module"
    
    # Store the evaluation record in the database
    # FIX: Privacy boundary - no raw name or resume_text is saved or echoed
    evaluation_record = EvaluationRecord(
        evaluation_id=str(uuid.uuid4()),
        job_id=job_id,
        verdict="needs_review",
        sanitized_payload=f"candidate_id: {candidate_id}, feedback: {ai_feedback}",
        policy_evaluations="needs_review"
    )
    
    # FIX: Rollback on a failed write per peer review request
    try:
        db.add(evaluation_record)
        db.commit()
        db.refresh(evaluation_record)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Database write failed")
    
    return {
        "evaluation_id": evaluation_record.evaluation_id,
        "job_id": evaluation_record.job_id,
        "verdict": evaluation_record.verdict,
        "policy_evaluations": evaluation_record.policy_evaluations,
        "ai_feedback": ai_feedback
    }

# Interface Contract: Audit Logs Endpoint Stub
@app.get("/api/v1/audit-logs")
async def get_audit_logs(token: str = Depends(verify_reviewer)):
    return {"message": "Audit logs endpoint stub"}
