import asyncio
import json
import time

import httpx

from app.contracts import AgentAssessment, AIMetrics, PolicyResult, ScreeningFacts, SkillAssessment
from app.settings import Settings


class DependencyError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def validate_assessment(value: dict, facts: ScreeningFacts) -> AgentAssessment:
    assessment = AgentAssessment.model_validate(value)
    expected = {item.skill_id: item.pages for item in facts.observed_skills}
    if {item.skill_id for item in assessment.skills} != set(facts.required_skills):
        raise DependencyError("INVALID_AGENT_OUTPUT")
    if len(assessment.skills) != len(facts.required_skills):
        raise DependencyError("INVALID_AGENT_OUTPUT")
    for item in assessment.skills:
        present = item.skill_id in expected
        if (
            item.status != ("MENTIONED" if present else "NOT_FOUND")
            or item.evidence_pages != expected.get(item.skill_id, [])
            or item.review_focus != ("VERIFY_PROFICIENCY" if present else "REQUEST_EVIDENCE")
        ):
            raise DependencyError("UNSUPPORTED_AGENT_CLAIM")
    return assessment


class HermesClient:
    def __init__(self, settings: Settings, transport=None):
        self.settings = settings
        self.client = httpx.AsyncClient(
            timeout=settings.hermes_timeout, follow_redirects=False, transport=transport
        )
        self.failures = 0
        self.open_until = 0.0
        self.probing = False
        self.usage: dict[str, AIMetrics] = {}

    async def assess(self, facts: ScreeningFacts, request_id: str) -> AgentAssessment:
        if time.monotonic() < self.open_until or self.probing:
            raise DependencyError("AI_CIRCUIT_OPEN")
        probe = self.open_until > 0
        if probe:
            self.probing = True
        try:
            async with asyncio.timeout(self.settings.hermes_timeout):
                value = await self._request(facts, request_id)
                assessment = validate_assessment(value, facts)
            self.failures = 0
            self.open_until = 0.0
            return assessment
        except (
            httpx.HTTPError,
            TimeoutError,
            ValueError,
            KeyError,
            IndexError,
            TypeError,
        ) as error:
            self.failures += 1
            if self.failures >= 5 or probe:
                self.open_until = time.monotonic() + 10
            raise DependencyError("AI_UNAVAILABLE") from error
        except DependencyError:
            self.failures += 1
            if self.failures >= 5 or probe:
                self.open_until = time.monotonic() + 10
            raise
        finally:
            if probe:
                self.probing = False

    async def _request(self, facts: ScreeningFacts, request_id: str) -> dict:
        prompt = (
            "You organize job-related resume evidence for a human reviewer. "
            "You receive only privacy-filtered, canonical skill IDs and page references. "
            "A mention is not proof of proficiency; absence is not proof of inability. "
            "Do not rank candidates or recommend a hiring decision. Return JSON only: "
            '{"skills":[{"skill_id":"python","status":"MENTIONED",'
            '"evidence_pages":[1],"review_focus":"VERIFY_PROFICIENCY"}]}. '
            "Include exactly one item for every required skill. Copy observed pages exactly. "
            "For skills not observed use status NOT_FOUND, evidence_pages [], "
            "and review_focus REQUEST_EVIDENCE. Do not add prose or other fields."
        )
        # Raw documents and identity fields are impossible to pass through this typed boundary.
        async with self.client.stream(
            "POST",
            self.settings.hermes_url,
            headers={
                "Authorization": f"Bearer {self.settings.hermes_key}",
                "Idempotency-Key": request_id,
            },
            json={
                "model": self.settings.hermes_model,
                "stream": False,
                "messages": [
                    {"role": "system", "content": prompt + f" Evaluation boundary: {request_id}."},
                    {"role": "user", "content": facts.model_dump_json()},
                ],
            },
        ) as response:
            response.raise_for_status()
            content = bytearray()
            async for chunk in response.aiter_bytes():
                content.extend(chunk)
                if len(content) > 65536:
                    raise DependencyError("INVALID_AGENT_OUTPUT")
        envelope = json.loads(content)
        usage = envelope.get("usage") or {}
        self.usage[request_id] = AIMetrics(
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
        )
        choice = envelope["choices"][0]
        if choice.get("finish_reason") != "stop" or choice["message"].get("tool_calls"):
            raise DependencyError("INVALID_AGENT_OUTPUT")
        return json.loads(choice["message"]["content"])

    async def close(self):
        await self.client.aclose()


class DemoAgent:
    def __init__(self):
        self.usage: dict[str, AIMetrics] = {}

    async def assess(self, facts: ScreeningFacts, request_id: str) -> AgentAssessment:
        self.usage[request_id] = AIMetrics(cost_usd=0.0, cost_basis="local_fixture")
        observed = {item.skill_id: item.pages for item in facts.observed_skills}
        return AgentAssessment(
            skills=[
                SkillAssessment(
                    skill_id=skill,
                    status="MENTIONED" if skill in observed else "NOT_FOUND",
                    evidence_pages=observed.get(skill, []),
                    review_focus="VERIFY_PROFICIENCY" if skill in observed else "REQUEST_EVIDENCE",
                )
                for skill in facts.required_skills
            ]
        )

    async def close(self):
        pass


class OPAClient:
    def __init__(self, settings: Settings, transport=None):
        self.settings = settings
        self.client = httpx.AsyncClient(timeout=settings.opa_timeout, transport=transport)

    async def evaluate(self, facts: ScreeningFacts) -> PolicyResult:
        try:
            async with asyncio.timeout(self.settings.opa_timeout):
                response = await self.client.post(
                    self.settings.opa_url,
                    json={
                        "input": {
                            "required_skills": facts.required_skills,
                            "observed_skills": [item.skill_id for item in facts.observed_skills],
                        }
                    },
                )
                response.raise_for_status()
                if len(response.content) > 65536:
                    raise ValueError("Oversized policy response")
                result = PolicyResult.model_validate(response.json()["result"])
                # A mismatched response may mean the wrong policy URL or schema was deployed.
                expected = set(facts.required_skills) & {s.skill_id for s in facts.observed_skills}
                missing = set(facts.required_skills) - expected
                if set(result.matched_skills) != expected or set(result.missing_skills) != missing:
                    raise ValueError("Policy evidence mismatch")
                expected_status = (
                    "MISSING_REQUIRED_EVIDENCE" if missing else "REQUIREMENTS_DOCUMENTED"
                )
                if result.status != expected_status:
                    raise ValueError("Policy status mismatch")
                return result
        except (httpx.HTTPError, TimeoutError, ValueError, KeyError, TypeError) as error:
            raise DependencyError("POLICY_UNAVAILABLE") from error

    async def close(self):
        await self.client.aclose()
