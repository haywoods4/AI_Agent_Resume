from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Inquiry(Contract):
    request_id: str = Field(min_length=1, max_length=128, pattern=r"^[a-zA-Z0-9_-]+$")
    tenant_id: str = Field(min_length=1, max_length=64)
    candidate_email: str | None = Field(default=None, max_length=254)
    candidate_phone: str | None = Field(default=None, max_length=30)
    query_type: Literal["lookup_by_email", "lookup_by_phone"]
    client_ts: str | None = Field(default=None, max_length=40)


class SkillEvidence(Contract):
    skill_id: str
    pages: list[int] = Field(max_length=30)


class ScreeningFacts(Contract):
    """Only this allowlisted data may cross the model boundary."""

    job_id: str
    required_skills: list[str]
    observed_skills: list[SkillEvidence]
    page_count: int = Field(ge=1, le=30)


class SkillAssessment(Contract):
    skill_id: str
    status: Literal["MENTIONED", "NOT_FOUND"]
    evidence_pages: list[int]
    review_focus: Literal["VERIFY_PROFICIENCY", "REQUEST_EVIDENCE"]


class AgentAssessment(Contract):
    skills: list[SkillAssessment]


class PolicyResult(Contract):
    policy_version: str
    status: Literal["REQUIREMENTS_DOCUMENTED", "MISSING_REQUIRED_EVIDENCE"]
    matched_skills: list[str]
    missing_skills: list[str]
    requires_human_review: Literal[True]


class Review(Contract):
    outcome: Literal["CONFIRMED_EVIDENCE", "FOLLOW_UP_REQUIRED"]
    reason: Literal["VERIFIED_AGAINST_RESUME", "INSUFFICIENT_EVIDENCE", "PARSER_LIMITATION"]


class Evaluation(Contract):
    evaluation_id: str
    candidate_id: str
    job_id: str
    status: Literal["READY_FOR_REVIEW", "MANUAL_REVIEW_REQUIRED", "REVIEWED"]
    facts: ScreeningFacts
    assessment: AgentAssessment | None
    policy: PolicyResult | None
    failure_code: str | None
    requires_human_review: Literal[True] = True
    model_version: str
    privacy_version: str = "allowlist-v1"
    review: Review | None = None
