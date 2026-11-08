# Resume AI integration

My integration contribution uses FastAPI, SQLite, an actual pinned Hermes Agent adapter configured for Groq, strict outbound PII filtering, OPA rules, and a small React reference client. I keep my contribution in this folder so my teammates can integrate their modules through the documented API.

## Run the complete local demo

I use Python 3.12, [uv](https://docs.astral.sh/uv/), Node 22+, and internet for installation. I run these commands from this directory:

```sh
uv sync --frozen
uv run python scripts/init_env.py
uv run python scripts/setup_opa.py
uv run python scripts/demo.py
```

I open another terminal and run:

```sh
cd react-client
npm ci
npm run dev
```

I open the URL Vite prints and copy `REVIEWER_TOKEN` from the local `.env` into the access-token field. I upload a small text-based PDF, DOCX or TXT with skills such as Python, FastAPI, SQL and Git. I review the evidence against the original document and save my reviewer outcome. I use a demo with a deterministic model fixture, **real OPA**, and SQLite at `data/demo.sqlite`; it does not call Groq.

## Use actual Hermes and Groq

On Linux/macOS, I run this from this directory:

```sh
bash scripts/setup-hermes.sh
```

I download NousResearch's original source at the revision in `config/hermes-source.json` and installs its runtime with its own environment manager. It is not a substitute agent implementation. I edit `data/hermes/.env` locally and set `GROQ_API_KEY`. I keep its generated `API_SERVER_KEY` synchronized with `HERMES_API_KEY` in root `.env`. I leave `AI_MODE=hermes` and keep these secret files out of version control.

I run these in separate terminals:

```sh
bash scripts/hermes.sh gateway run
```

```sh
tools/opa run --server --addr 127.0.0.1:8181 policies/
```

```sh
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --env-file .env --no-access-log
```

I start React as above. `uv run python scripts/smoke_hermes.py` tests the live agent with synthetic skill facts. The configured Groq model is `llama-3.3-70b-versatile`; update both the Hermes profile and `INFERENCE_MODEL_VERSION` if changing it. Live provider inference requires a working Groq key and was not verified without one.

## Integration contracts

I require `Authorization: Bearer <REVIEWER_TOKEN>`. I currently configure one configured tenant and reviewer. I will replace that boundary with my team’s authentication service before shared deployment. I bind development servers locally and run one FastAPI worker for my SQLite prototype.

| Route | Purpose |
|---|---|
| `GET /api/v1/jobs` | Approved skill requirements from `config/jobs.json` |
| `POST /api/v1/evaluations` | Multipart `request_id`, `job_id`, `candidate_email`, optional `candidate_phone`, `resume` |
| `GET /api/v1/evaluations` | Latest 100 tenant evaluations |
| `GET /api/v1/evaluations/{id}` | Saved evidence, model and policy results |
| `POST /api/v1/evaluations/{id}/review` | Human review with outcome and reason; see `/docs` schema |
| `POST /api/v1/candidates/inquiry` | Candidate lookup contract, described below |
| `GET /health` | Process status and explicitly configured model mode |

FastAPI's `/docs` and `/openapi.json` are the authoritative schemas. `app/contracts.py` holds strict models; `react-client/src/api.ts` is the reference frontend adapter. I provide the frontend adapter so I can connect my teammates’ UI without changing backend contracts. The job catalog is a class fixture, not a validated hiring rubric.

Candidate inquiry JSON has `request_id`, `tenant_id`, `query_type` (`lookup_by_email` or `lookup_by_phone`), the corresponding `candidate_email`/`candidate_phone`, and optional `client_ts`. A lookup miss returns HTTP 200 with `NOT_FOUND` and null candidate. The candidate interface's conflicting 404 example is resolved in favor of its explicit miss envelope. Contacts are tenant-scoped HMAC-SHA256 hashes. Optional `REDIS_URL` enables a 900-second cache; SQLite remains authoritative for sensitivity and records. Sensitive records bypass cache. Redis failures fall back to SQLite. Requests deduplicate for 24 hours; changing a payload under the same request ID returns 409. Reuse request IDs when retrying API calls. Reviews are immutable; identical retries succeed, conflicting edits return 409.

## Privacy and policy boundary

I limit raw uploads to 512 KiB, parsed in a short-lived process with a six-second deadline and POSIX CPU/memory limits, and never intentionally stored or logged. Text PDFs are limited to 30 pages; encrypted/scanned-only PDFs are rejected. DOCX/TXT evidence uses section 1, not physical pagination. Multipart bodies remain below the disk-spooling threshold. Deployment proxies, OS swap and external logging remain deployment responsibilities.

The PII scrubbing boundary **projects text into approved skill IDs and page references**. No original sentences, names, contact details, schools, demographics or other free text are sent to Hermes/Groq or OPA. This is deliberately narrower than general résumé understanding: it recognizes literal aliases, not proficiency, negation or context. Reviewers must verify mentions against the original document. HMAC identifiers are pseudonymous, not anonymous; protect the SQLite file and stable HMAC key. Rotating that key requires migrating identifiers.

I disable tools and persistent memory in my dedicated Hermes profile. Model output must exactly agree with observed evidence; hallucinated skills/pages or invalid JSON fail closed. OPA independently checks required-skill coverage and always requires human review. There is no candidate ranking or automated hiring decision. Model or policy failure persists `MANUAL_REVIEW_REQUIRED`, never a fabricated success. Restarting an interrupted request preserves the pending manual-review record.

I store only opaque candidate IDs, hashed contacts, optional phone last four, safe skill facts, structured results, immutable reviews and audit metadata in local SQLite. I keep databases out of version control. Deletion/retention, production identity, enterprise deployment, fairness validation and teammates' scoring/UI work are outside this integration contribution. No production concurrency or legal-compliance claims are made. Model timeout defaults to 9 seconds (configuration must remain below 10) plus bounded parsing and OPA time; the candidate-lookup budget is separate from evaluation latency.

I implement the AI résumé-screening scope from the Unit 5 assignment and Week 1–4 sprint backlog. I use SQLite and connect React, FastAPI, Groq, Hermes and OPA through the boundaries above.

## Checks

```sh
uv run ruff check .
uv run pytest -q
tools/opa test policies/ -v
cd react-client
npm ci
npm run build
```

I run the real OPA integration test when `tools/opa` is installed. I exercise real Redis by setting `TEST_REDIS_URL` to a dedicated local Redis database before pytest. CI supplies Redis and OPA. Provider tests mock only the network and assert the exact sanitized outbound payload, output validation and circuit breaker. I distinguish fixture-demo evidence from live LLM validation.

Upstream Hermes is MIT licensed; its downloaded source retains its LICENSE and attribution. OPA retains its upstream license. Generated dependencies and vendor downloads are ignored.

I track my assignment evidence and remaining dependencies in [Unit 5 readiness and ownership](docs/unit5-readiness.md).
