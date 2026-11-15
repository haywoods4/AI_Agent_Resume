import pytest

from app.contracts import PolicyResult
from app.settings import Settings


@pytest.fixture
def settings(tmp_path):
    return Settings(
        database=str(tmp_path / "resume.sqlite"),
        mode="demo",
        reviewer_token="test-reviewer-token-at-least-24",
        hmac_key="test-hmac-key-at-least-24-characters",
    )


class FixturePolicy:
    async def evaluate(self, facts):
        observed = {s.skill_id for s in facts.observed_skills}
        required = set(facts.required_skills)
        missing = required - observed
        return PolicyResult(
            policy_version="fixture-policy-v1",
            status="MISSING_REQUIRED_EVIDENCE" if missing else "REQUIREMENTS_DOCUMENTED",
            matched_skills=sorted(required & observed),
            missing_skills=sorted(missing),
            requires_human_review=True,
        )

    async def close(self):
        pass
