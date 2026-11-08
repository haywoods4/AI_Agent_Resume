# Resume AI integration

Justin's integration contribution: FastAPI, SQLite, an actual pinned Hermes Agent adapter configured for Groq, strict outbound PII filtering, OPA rules, and a small React reference client. This is a runnable integration boundary for teammates to build against.

## Run the complete local demo

Requires Python 3.12, [uv](https://docs.astral.sh/uv/), Node 22+, and internet for installation. Run from this directory:

```sh
uv sync --frozen
uv run python scripts/init_env.py
uv run python scripts/setup_opa.py
uv run python scripts/demo.py
```

In another terminal:

```sh
cd react-client
npm ci
npm run dev
```

Open the URL Vite prints. Copy `REVIEWER_TOKEN` from the local `.env` into the access-token field. Upload a small text-based PDF, DOCX or TXT with skills such as Python, FastAPI, SQL and Git. Review the evidence against the original document and save the reviewer outcome. The demo uses a deterministic model fixture, **real OPA**, and SQLite at `data/demo.sqlite`; it does not call Groq.

## Use actual Hermes and Groq

On Linux/macOS, from this directory:

```sh
bash scripts/setup-hermes.sh
```

This downloads NousResearch's original source at the revision in `config/hermes-source.json` and installs its runtime with its own environment manager. It is not a substitute agent implementation. Edit `data/hermes/.env` locally and set `GROQ_API_KEY`. Keep its generated `API_SERVER_KEY` synchronized with `HERMES_API_KEY` in root `.env`. Leave `AI_MODE=hermes`. Never commit these files.

Run these in separate terminals:

```sh
bash scripts/hermes.sh gateway run
```

```sh
tools/opa run --server --addr 127.0.0.1:8181 policies/
```

```sh
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --env-file .env --no-access-log
```

Start React as above. `uv run python scripts/smoke_hermes.py` tests the live agent with synthetic skill facts. The configured Groq model is `llama-3.3-70b-versatile`; update both the Hermes profile and `INFERENCE_MODEL_VERSION` if changing it. Live provider inference requires a working Groq key and was not verified without one.

## Integration contracts

All `/api/` routes require `Authorization: Bearer <REVIEWER_TOKEN>`. The service currently represents one configured tenant and reviewer. Replace that boundary with the team's authentication service before shared deployment; do not expose the development servers publicly. Run one FastAPI worker for this SQLite prototype.

| Route | Purpose |
|---|---|
| `GET /api/v1/jobs` | Approved skill requirements from `config/jobs.json` |
| `POST /api/v1/evaluations` | Multipart `request_id`, `job_id`, `candidate_email`, optional `candidate_phone`, `resume` |
| `GET /api/v1/evaluations` | Latest 100 tenant evaluations |
| `GET /api/v1/evaluations/{id}` | Saved evidence, model and policy results |
| `POST /api/v1/evaluations/{id}/review` | Human review with outcome and reason; see `/docs` schema |
| `POST /api/v1/candidates/inquiry` | Candidate lookup contract, described below |
| `GET /health` | Process status and explicitly configured model mode |

FastAPI's `/docs` and `/openapi.json` are the authoritative schemas. `app/contracts.py` holds strict models; `react-client/src/api.ts` is the reference frontend adapter. Teammates can replace the reference UI without changing backend contracts. The job catalog is a class fixture, not a validated hiring rubric.

Candidate inquiry JSON has `request_id`, `tenant_id`, `query_type` (`lookup_by_email` or `lookup_by_phone`), the corresponding `candidate_email`/`candidate_phone`, and optional `client_ts`. A lookup miss returns HTTP 200 with `NOT_FOUND` and null candidate. The candidate interface's conflicting 404 example is resolved in favor of its explicit miss envelope. Contacts are tenant-scoped HMAC-SHA256 hashes. Optional `REDIS_URL` enables a 900-second cache; SQLite remains authoritative for sensitivity and records. Sensitive records bypass cache. Redis failures fall back to SQLite. Requests deduplicate for 24 hours; changing a payload under the same request ID returns 409. Reuse request IDs when retrying API calls. Reviews are immutable; identical retries succeed, conflicting edits return 409.

## Privacy and policy boundary

Raw uploads are limited to 512 KiB, parsed in a short-lived process with a six-second deadline and POSIX CPU/memory limits, and never intentionally stored or logged. Text PDFs are limited to 30 pages; encrypted/scanned-only PDFs are rejected. DOCX/TXT evidence uses section 1, not physical pagination. Multipart bodies remain below the disk-spooling threshold. Deployment proxies, OS swap and external logging remain deployment responsibilities.

The PII scrubbing boundary **projects text into approved skill IDs and page references**. No original sentences, names, contact details, schools, demographics or other free text are sent to Hermes/Groq or OPA. This is deliberately narrower than general résumé understanding: it recognizes literal aliases, not proficiency, negation or context. Reviewers must verify mentions against the original document. HMAC identifiers are pseudonymous, not anonymous; protect the SQLite file and stable HMAC key. Rotating that key requires migrating identifiers.

Hermes has tools and persistent memory disabled in its dedicated profile. Model output must exactly agree with observed evidence; hallucinated skills/pages or invalid JSON fail closed. OPA independently checks required-skill coverage and always requires human review. There is no candidate ranking or automated hiring decision. Model or policy failure persists `MANUAL_REVIEW_REQUIRED`, never a fabricated success. Restarting an interrupted request preserves the pending manual-review record.

Local SQLite stores only opaque candidate IDs, hashed contacts, optional phone last four, safe skill facts, structured results, immutable reviews and audit metadata. Do not commit databases. Deletion/retention, production identity, enterprise deployment, fairness validation and teammates' scoring/UI work are outside this integration contribution. No production concurrency or legal-compliance claims are made. Model timeout is 15 seconds plus bounded parsing and OPA time; the candidate-lookup budget is separate from evaluation latency.

The supplied customer-service flow/escalation documents describe the earlier project, superseded by the clarified résumé scope. The candidate interface informed lookup, caching, audit and idempotency; PostgreSQL is replaced by SQLite as requested. React, FastAPI, Groq, Hermes and OPA are connected through the boundaries above.

## Checks

```sh
uv run ruff check .
uv run pytest -q
tools/opa test policies/ -v
cd react-client
npm ci
npm run build
```

The real OPA integration test runs when `tools/opa` is installed. To exercise real Redis as well, set `TEST_REDIS_URL` to a dedicated local Redis database before pytest. CI supplies Redis and OPA. Provider tests mock only the network and assert the exact sanitized outbound payload, output validation and circuit breaker. Never describe the fixture demo as live LLM validation.

Upstream Hermes is MIT licensed; its downloaded source retains its LICENSE and attribution. OPA retains its upstream license. Generated dependencies and vendor downloads are ignored. No AI co-author trailers are added to this contribution.
