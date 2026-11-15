# Alpha interface contracts

## Scope and integration status

This specification aligns the original interface proposal with the implemented Alpha in [integration PR #4](https://github.com/haywoods4/AI_Agent_Resume/pull/4), reviewed at commit `d405ca70fc217fec90997d46092897cf3f15dd30`. PR #5 changes documentation and its validation only. It does not introduce backend, database, Redis or model implementations into `develop`. PR #4 remains a separate team review and merge decision.

Individual contributions target `develop`; `main` remains the release branch. The original proposal and its authorship remain in Git history. This revision replaces conflicting endpoint, privacy and model examples rather than prescribing another database implementation.

## Part 1: React and FastAPI

| Endpoint | Input | Behavior |
| --- | --- | --- |
| `GET /api/v1/jobs` | authenticated request | Approved job catalog, not arbitrary job UUIDs. |
| `POST /api/v1/resumes/upload` | multipart `file`, `job_id`; optional `candidate_id`, `candidate_email`, `request_id` | Shared upload contract. Supply a UUID candidate ID or email, not both. An opaque UUID is generated when neither is supplied. |
| `POST /api/v1/evaluations` | multipart `resume`, `job_id`, `candidate_email`, `request_id`; optional `candidate_phone` | Existing React reference-client endpoint; same pipeline and store, not a second service. |
| `GET /api/v1/evaluations` | authenticated request | Tenant-scoped review feed. |
| `GET /api/v1/evaluations/{evaluation_id}` | stored opaque ID | Saved evaluation, or not found. |
| `POST /api/v1/evaluations/{evaluation_id}/review` | review object below | Immutable evidence review; not a hiring decision. |
| `GET /api/v1/audit-logs` | optional job/verdict/date filters, limit 1–100, offset | Persisted completed decision snapshots with total count. Dates require timezones. |

Upload accepts text-based PDF, DOCX or TXT, maximum 512 KiB. Unsupported, encrypted, oversized or unparseable documents fail closed. Scanned-image OCR, experience, degrees and certifications are not implemented. `backend-engineer` and `frontend-engineer` are catalog job IDs. Treat returned evaluation and candidate IDs as opaque: the shared upload accepts UUIDs, while the existing internal path may return `cand_`-prefixed identifiers.

Browser access uses server-side sessions and HttpOnly cookies; the configured bearer-token API remains supported. In live mode, later accounts remain pending until the owner approves them. In demo/keyless mode, registration grants immediate effective reviewer access to synthetic classroom records without persisting live approval or granting owner privileges. One classroom workspace is shared among approved reviewers; this is not a production multi-organization account system. Protected routes enforce authentication and configured tenant scope.

The shared upload response includes `evaluation_id`, `candidate_id`, `job_id`, UTC `timestamp`, `verdict`, `sanitized_payload.skills`, `policy_evaluations`, and `pii_scrubbed_summary`, plus the review client's evaluation fields. `PASS` and `FAIL` describe evidence completeness only; every result requires human review. Dependency failures produce `NEEDS_REVIEW`, never an invented assessment. The summary describes allowlisted projection, not perfect PII detection.

```json
{
  "outcome": "FOLLOW_UP_REQUIRED",
  "reason": "INSUFFICIENT_EVIDENCE"
}
```

Review outcomes: `CONFIRMED_EVIDENCE` or `FOLLOW_UP_REQUIRED`. Reasons: `VERIFIED_AGAINST_RESUME`, `INSUFFICIENT_EVIDENCE`, or `PARSER_LIMITATION`.

## Part 2: Model boundary

FastAPI projects the document into approved canonical skill IDs and page references before any model call. Names, contact details, raw document text, schools and demographics do not cross that boundary. A skill mention is not proof of proficiency; missing evidence is not proof of missing ability.

- **Hermes/Groq mode:** FastAPI calls the Hermes Agent HTTP endpoint `/v1/chat/completions`; Hermes calls the separately configured Groq provider model. The verified configuration uses `openai/gpt-oss-20b`. Hermes is the agent runtime, not the name of a model hosted by Groq. Provider keys remain outside the repository.
- **Keyless mode:** the pinned local MiniLM ONNX model compares approved skill evidence without a Groq key. It does not execute Hermes and is not presented as a general reasoning model. Unsupported predictions fail validation. This narrow catalog exercise does not establish better accuracy than exact matching.
- **Simulated mode:** explicitly labeled development simulation, not live inference.

The typed model-boundary object is:

```json
{
  "job_id": "backend-engineer",
  "required_skills": ["python", "fastapi", "sql", "git"],
  "observed_skills": [{"skill_id": "python", "pages": [1]}],
  "page_count": 1
}
```

Model assessments contain `skills[]`, each with `skill_id`, `status` (`MENTIONED` or `NOT_FOUND`), `evidence_pages`, and `review_focus` (`VERIFY_PROFICIENCY` or `REQUEST_EVIDENCE`). Validate the response against the approved input rather than accepting invented qualifications.

## Part 3: Open Policy Agent

OPA receives structured evidence, not resume text. The implemented endpoint is `POST /v1/data/resume/screening/result`.

```json
{
  "input": {
    "required_skills": ["python", "fastapi", "sql", "git"],
    "observed_skills": ["python"]
  }
}
```

```json
{
  "result": {
    "policy_version": "job-evidence-v1",
    "status": "MISSING_REQUIRED_EVIDENCE",
    "matched_skills": ["python"],
    "missing_skills": ["fastapi", "git", "sql"],
    "requires_human_review": true
  }
}
```

The other policy status is `REQUIREMENTS_DOCUMENTED`. The pipeline maps these to `blocked`/`allowed` and the shared `FAIL`/`PASS` envelope, but neither approves or rejects employment. Unavailable or invalid dependencies require manual review. Completed decision audits preserve inputs, model version, policy result and metrics.

## Part 4: SQLite and optional Redis lookup

### One authoritative store

The implemented store is `ai-integration/app/store.py`, default `data/resume.sqlite`, with WAL and foreign keys enabled. SQLite connection timeout is one second with a bounded WAL-initialization retry; the earlier proposed five-second timeout is not an implemented guarantee. Runtime databases and secrets stay untracked. The separate account database is for authentication, not a duplicate candidate/evaluation store.

| Table | Responsibility |
| --- | --- |
| `candidates` | Tenant-scoped identifiers and sensitivity flag; uniqueness on `(tenant,email_hash)` and `(tenant,phone_hash)`. |
| `evaluations` | Saved structured evaluation, tenant and candidate reference. |
| `requests` | Tenant/operation/request-ID replay protection and payload fingerprint; expires after 86400 seconds. |
| `reviews` | Immutable reviewer outcome linked to an evaluation. |
| `decision_audit` | Model/policy decision snapshots with approved inputs and metrics. |
| `audit` | Operational inquiry/evaluation events and latency. |

Inquiry events and evaluations remain distinct: a lookup need not create an evaluation. Existing audit and replay tables record inquiries; no additional `inquiries` or competing `evaluations` table is prescribed.

### Lookup request and response

Use `POST /api/v1/candidates/inquiry`, not `/customers` endpoints. The caller sends an identifier to the authenticated backend; it does **not** calculate a public SHA-256 hash. The backend normalizes it and derives HMAC-SHA256 over the tenant, identifier kind and normalized value using a server-held secret. These are pseudonymous identifiers, not anonymous data.

```json
{
  "request_id": "lookup-example-001",
  "tenant_id": "group2-corp",
  "query_type": "lookup_by_email",
  "candidate_email": "synthetic@example.test"
}
```

For phone lookup use `query_type: lookup_by_phone` and `candidate_phone` in international `+country-code` format. Tenant must match the authenticated configuration. A request ID reused for a different lookup conflicts.

Example cache hit (synthetic digest and valid UUID; internal IDs may use the opaque legacy form):

```json
{
  "request_id": "lookup-example-001",
  "status": "FOUND",
  "source": "redis",
  "candidate": {
    "candidate_id": "550e8400-e29b-41d4-a716-446655440000",
    "email_hash": "hmac-sha256:0000000000000000000000000000000000000000000000000000000000000000",
    "phone_last4": null,
    "phi_flag": false
  }
}
```

Example not found:

```json
{
  "request_id": "lookup-example-002",
  "status": "NOT_FOUND",
  "source": "sqlite_fallback",
  "candidate": null
}
```

A cache miss or unavailable Redis returns the same response shape with `source: sqlite_fallback`. The API does not promise `cache_hit`, `ttl_seconds`, `cache_write_status` or an inquiry-history array. Operational audit records contain the source and latency.

### Freshness and privacy rules

1. For fresh, non-replayed inquiries, read the authoritative SQLite record and sensitivity flag before considering Redis. This is deliberately not unconditional Redis-first lookup.
2. Cache key: `cand:{tenant}:{hmac_digest}`. Cache only a nonsensitive public candidate projection, with a 900-second TTL. The 86400-second replay lifetime is separate from Redis freshness.
3. Accept a cache value only when it exactly matches the current authoritative projection. Refresh mismatched data. Sensitive records bypass Redis; this does not itself remove the authorized SQLite projection from the response.
4. Redis timeout, malformed data or connection failure falls back to SQLite. After five Redis failures, the circuit pauses Redis attempts for ten seconds. Each operation is bounded by a 0.3-second cache timeout.
5. A replay can return its prior result until replay expiry. It is not a new current-state lookup; use a new request ID to request fresh state. Privacy reclassification and replay invalidation need dedicated design before production.

## Errors and verification boundary

Errors use `error`, with optional `message` and validation `fields`; rejected input values are omitted. Expected HTTP categories are 400 validation, 401 unauthenticated, 403 unauthorized tenant/role/origin, 409 conflicting retry or immutable review, 413 oversized upload, 429 rate/capacity limit, and 503 unsaved database/dependency failure. A saved manual-review result can be HTTP 200; that is different from a failed database save.

PR #4's integration tests cover cache hit/miss, sensitive-record bypass, tenant isolation and replay. Redis-failure fallback and stale-cache comparison are implemented but still need dedicated verification. Documentation CI here validates JSON examples and required contract sections only, not the runtime. Future changes must keep both implementations and their tests aligned; a passing document check is not deployment or Alpha acceptance.

### Implementation references

All references below are pinned to the reviewed integration version, not an assumption that it has merged:

- [Routes and upload adapter](https://github.com/haywoods4/AI_Agent_Resume/blob/d405ca70fc217fec90997d46092897cf3f15dd30/ai-integration/app/main.py)
- [Typed payloads](https://github.com/haywoods4/AI_Agent_Resume/blob/d405ca70fc217fec90997d46092897cf3f15dd30/ai-integration/app/contracts.py)
- [Privacy and identifier hashing](https://github.com/haywoods4/AI_Agent_Resume/blob/d405ca70fc217fec90997d46092897cf3f15dd30/ai-integration/app/privacy.py)
- [SQLite store](https://github.com/haywoods4/AI_Agent_Resume/blob/d405ca70fc217fec90997d46092897cf3f15dd30/ai-integration/app/store.py)
- [Lookup and Redis](https://github.com/haywoods4/AI_Agent_Resume/blob/d405ca70fc217fec90997d46092897cf3f15dd30/ai-integration/app/lookup.py)
