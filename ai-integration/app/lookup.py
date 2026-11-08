import asyncio
import json
import time

from redis.exceptions import RedisError

from app.contracts import Inquiry
from app.privacy import PrivacyError, identifier_hash
from app.settings import Settings
from app.store import Store


class CandidateLookup:
    def __init__(self, settings: Settings, store: Store, cache=None):
        self.settings, self.store, self.cache = settings, store, cache
        self.failures = 0
        self.open_until = 0.0

    async def inquiry(self, payload: Inquiry):
        if payload.tenant_id != self.settings.tenant_id:
            raise PermissionError("Tenant does not match authenticated identity")
        kind = "email" if payload.query_type == "lookup_by_email" else "phone"
        value = payload.candidate_email if kind == "email" else payload.candidate_phone
        if not value:
            raise PrivacyError("The selected identifier is required")
        digest = identifier_hash(self.settings.hmac_key, payload.tenant_id, kind, value)
        started = time.monotonic()
        status, source = "ERROR", "sqlite_fallback"
        try:
            replay = self.store.replay(
                payload.tenant_id, "inquiry", payload.request_id, kind + digest
            )
            if replay:
                status, source = replay["status"], replay["source"]
                return replay
            # Authoritative classification prevents a previously cached sensitive record leaking.
            row = self.store.lookup(payload.tenant_id, kind, digest)
            candidate = self.store.public_candidate(row) if row else None
            key = f"cand:{payload.tenant_id}:{digest}"
            if row and not row["phi_flag"] and self.cache and time.monotonic() >= self.open_until:
                try:
                    async with asyncio.timeout(0.3):
                        cached = await self.cache.get(key)
                    self.failures = 0
                    if cached and json.loads(cached) == candidate:
                        source = "redis"
                    else:
                        async with asyncio.timeout(0.3):
                            await self.cache.setex(key, 900, json.dumps(candidate))
                except (TimeoutError, ValueError, OSError, RedisError):
                    self.failures += 1
                    if self.failures >= 5:
                        self.open_until = time.monotonic() + 10
            status = "FOUND" if candidate else "NOT_FOUND"
            result = {
                "request_id": payload.request_id,
                "status": status,
                "source": source,
                "candidate": candidate,
            }
            self.store.remember(
                payload.tenant_id, "inquiry", payload.request_id, kind + digest, result
            )
            return result
        finally:
            self.store.audit(
                payload.tenant_id,
                payload.request_id,
                "inquiry",
                status,
                source,
                int((time.monotonic() - started) * 1000),
            )
