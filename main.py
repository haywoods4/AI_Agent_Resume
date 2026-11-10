from fastapi import FastAPI, Depends, Form, File, UploadFile, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Annotated

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
@app.post("/api/v1/evaluations")
async def evaluate_resume(
    request_id: Annotated[str, Form(min_length=1, max_length=128)],
    job_id: Annotated[str, Form(min_length=1, max_length=64)],
    candidate_email: Annotated[str, Form(min_length=1, max_length=254)],
    resume: Annotated[UploadFile, File()],
    db: Session = Depends(get_db),
    token: str = Depends(verify_reviewer)
):
    # FIX: Bound request body size (Max 512 KiB)
    content = await resume.read(512 * 1024 + 1)
    if len(content) > 512 * 1024:
        raise HTTPException(status_code=413, detail="Resume must not exceed 512 KiB")
    await resume.close()

    # Simulate AI evaluation (replace with actual AI model integration)
    # FIX: Kept unmistakably separate from a real evaluation by marking as simulation
    ai_feedback = "SIMULATION ONLY: Awaiting Integration Lead AI Module"
    
    # Store the evaluation record in the database
    # FIX: Privacy boundary - no raw name or resume_text is saved or echoed
    evaluation_record = EvaluationRecord(
        request_id=request_id,
        job_id=job_id,
        status="needs_review",
        policy_status="needs_review",
        model_version="simulation-v1"
    )
    
    db.add(evaluation_record)
    db.commit()
    db.refresh(evaluation_record)
    
    return {
        "evaluation_id": evaluation_record.id,
        "request_id": evaluation_record.request_id,
        "job_id": evaluation_record.job_id,
        "status": evaluation_record.status,
        "policy_status": evaluation_record.policy_status,
        "ai_feedback": ai_feedback
    }
