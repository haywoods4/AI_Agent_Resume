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

I open the URL Vite prints and sign in with my existing username/password or select Create an account on the page. I upload a small text-based PDF, DOCX or TXT with skills such as Python, FastAPI, SQL and Git. I review the evidence against the original document and save my reviewer outcome. I use a demo with a deterministic model fixture, **real OPA**, and SQLite at `data/demo.sqlite`; it does not call Groq.

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

I start React as above. `uv run python scripts/smoke_hermes.py` tests the live agent with synthetic skill facts. My setup queries the account model catalog and prefers production `openai/gpt-oss-20b`, then `openai/gpt-oss-120b`, with the original Llama model only if enabled. It updates both the Hermes profile and `INFERENCE_MODEL_VERSION`; the old Llama model is now enterprise-only in Groq’s catalog. Live provider inference requires a working Groq key and was not verified without one.

## Integration contracts

I preserve `Authorization: Bearer <REVIEWER_TOKEN>` for scripts and API clients; the browser instead uses local username/password login and an HttpOnly session cookie. I configure one classroom tenant. New reviewer accounts require owner approval; this does not provide separate customer workspaces. I bind development servers locally and run one FastAPI worker for my SQLite prototype.

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

I limit raw uploads to 512 KiB, parsed in a short-lived process with a six-second deadline and POSIX CPU limits (Linux also enforces a 512 MiB address-space cap; macOS does not support that cap reliably), and never intentionally stored or logged. Text PDFs are limited to 30 pages; encrypted/scanned-only PDFs are rejected. DOCX/TXT evidence uses section 1, not physical pagination. Multipart bodies remain below the disk-spooling threshold. Deployment proxies, OS swap and external logging remain deployment responsibilities.

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

## My in-app account setup

I choose **Create an account** on the sign-in page, enter a username and confirm a password of at least 12 characters. On a completely fresh local installation with no existing configured account, the first account becomes the owner. Registration is serialized in SQLite so simultaneous requests cannot create two owners. Later accounts remain pending and cannot read résumés or audits or submit evaluations. The owner signs in, opens **Account requests**, loads requests and explicitly approves intended collaborators. Approved reviewers share this one classroom workspace; they do not gain account-administration access.

I preserve any existing username/password in `.env` unchanged as the owner account. Registration cannot overwrite or claim its username. New accounts persist salted scrypt hashes in the ignored `data/reviewer-accounts.sqlite`; no plaintext passwords or hashes are returned to the browser. Demo and live modes use the same account file when their databases share the data directory. `configure_login.py` remains an optional legacy setup tool, not a required signup step.

I use random server-side sessions with HttpOnly, SameSite=Strict cookies. Sessions expire after eight hours, logout, API restart or a new login to the same account; one account’s logout does not revoke others. I limit authentication attempts and reject cross-origin writes. Reviewer actions record their actual account ID. The UI clears sensitive state when a session expires.

This remains **localhost HTTP, one classroom tenant and one API worker**, not a public production identity service. Cookie login accepts the documented local ports 5173/8000, deliberately without Secure for local HTTP. Shared hosting requires HTTPS/Secure cookies, deployment-specific trusted origins, durable sessions, distributed throttling, retention/access revocation/password recovery and an explicit owner-provisioning policy. I do not deploy this configuration publicly or claim separate user-owned workspaces. The API Bearer contract remains compatible.

My simple activity feed keeps upload and human evidence review prominent, with technical and audit details collapsed. No policy result becomes a hiring decision.

## My keyless neural demo

I use the [GitHub Codespaces launch guide](../CODESPACES.md) for a browser-hosted classroom workspace with no model API key. The default there is `AI_MODE=keyless`: actual pinned MiniLM ONNX neural inference on approved skill IDs, real OPA and SQLite. It is not Hermes/Groq or the deterministic demo fixture. I retain all three modes with explicit labels. The model chooses evidence matches; unsupported neural predictions fail closed at the same exact-evidence validator.

For a local development check only, I install `uv sync --frozen --extra keyless`, run `uv run --extra keyless python scripts/setup_keyless.py`, then `uv run --extra keyless python scripts/demo.py --keyless`. I do not need local installation when using Codespaces. I never describe a local test as proof that fresh cloud provisioning passed.
