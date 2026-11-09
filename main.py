from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db, EvaluationRecord
app = FastAPI(title = "AI Resume Evaluator API (Alpha)")
app.add_middleware(
    CORSMiddleware,
    allow_origins = ["*"],
    allow_methods = ["*"],
    allow_headers = ["*"],
)
class ResumeInput(BaseModel):
    candidate_name: str
    resume_text: str  
@app.post("/evaluate_resume")
def evaluate_resume(resume_input: ResumeInput, db: Session = Depends(get_db)): 
    # Simulate AI evaluation (replace with actual AI model integration)
    ai_feedback = f"AI Feedback for {resume_input.candidate_name}: Your resume looks great!"
    
    # Store the evaluation record in the database
    evaluation_record = EvaluationRecord(
        candidate_name=resume_input.candidate_name,
        resume_text=resume_input.resume_text,
        ai_feedback=ai_feedback
    )
    db.add(evaluation_record)
    db.commit()
    db.refresh(evaluation_record)
    
    return {
        "candidate_name": evaluation_record.candidate_name,
        "resume_text": evaluation_record.resume_text,
        "ai_feedback": evaluation_record.ai_feedback
    }