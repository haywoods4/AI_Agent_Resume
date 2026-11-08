import asyncio
import hashlib
import hmac
import re
import time
import uuid
from pathlib import Path

from app.contracts import Evaluation
from app.parser import parse_document
from app.privacy import PIIScrubbingMiddleware, identifier_hash, normalize_identifier
from app.providers import DependencyError
from app.settings import Settings
from app.store import ConflictError, Store


class ScreeningPipeline:
    def __init__(self, settings: Settings, store: Store, agent, policy):
        self.settings, self.store, self.agent, self.policy = settings, store, agent, policy
        self.inflight: set[str] = set()
        self.active_evaluations: set[str] = set()
        self.parsing = asyncio.Semaphore(2)

    async def evaluate(self, request_id, job_id, email, phone, content, filename):
        if request_id in self.inflight:
            raise ConflictError("REQUEST_IN_PROGRESS: retry the same request_id after completion")
        if len(self.inflight) >= 16:
            raise DependencyError("CAPACITY_EXCEEDED")
        tenant = self.settings.tenant_id
        email_hash = identifier_hash(self.settings.hmac_key, tenant, "email", email)
        phone_hash = (
            identifier_hash(self.settings.hmac_key, tenant, "phone", phone) if phone else None
        )
        last4 = normalize_identifier(phone, "phone")[-4:] if phone else None
        fingerprint = hmac.new(
            self.settings.hmac_key.encode(),
            content
            + b"\0"
            + job_id.encode()
            + b"\0"
            + email_hash.encode()
            + b"\0"
            + (phone_hash or "").encode()
            + b"\0"
            + Path(filename).suffix.lower().encode(),
            hashlib.sha256,
        ).hexdigest()
        replay = self.store.replay(tenant, "evaluation", request_id, fingerprint)
        if replay:
            return self.store.evaluation(tenant, replay["evaluation_id"])
        self.inflight.add(request_id)
        evaluation_id = None
        started = time.monotonic()
        try:
            async with self.parsing:
                pages = await parse_document(content, filename)
            facts = PIIScrubbingMiddleware().scrub(pages, job_id)
            sensitive = any(
                re.search(r"\b(ssn|diagnosis|medical|disability)\b", p, re.I) for p in pages
            )
            # Sensitive-term classification is conservative cache policy, not our privacy guarantee.
            # The outbound whitelist removes ALL raw text, regardless of this flag.
            del pages
            candidate_id = self.store.candidate(tenant, email_hash, phone_hash, last4, sensitive)
            evaluation = Evaluation(
                evaluation_id=f"eval_{uuid.uuid4().hex}",
                candidate_id=candidate_id,
                job_id=job_id,
                status="MANUAL_REVIEW_REQUIRED",
                facts=facts,
                assessment=None,
                policy=None,
                failure_code="PROCESSING_INTERRUPTED",
                model_version=self.settings.model_version
                if self.settings.mode == "hermes"
                else "demo-fixture-v1",
            )
            # Persist before remote work: a crash cannot silently erase an admitted evaluation.
            self.store.save_evaluation(tenant, evaluation, request_id, fingerprint)
            evaluation_id = evaluation.evaluation_id
            self.active_evaluations.add(evaluation_id)
            try:
                evaluation.assessment = await self.agent.assess(facts, evaluation.evaluation_id)
                evaluation.policy = await self.policy.evaluate(facts)
                evaluation.status = "READY_FOR_REVIEW"
                evaluation.failure_code = None
            except DependencyError as error:
                evaluation.failure_code = error.code
            self.store.save_evaluation(tenant, evaluation, request_id, fingerprint)
            self.store.audit(
                tenant,
                request_id,
                "evaluate",
                evaluation.status,
                self.settings.mode,
                int((time.monotonic() - started) * 1000),
            )
            return evaluation
        finally:
            self.inflight.remove(request_id)
            self.active_evaluations.discard(evaluation_id)
