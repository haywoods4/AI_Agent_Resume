# Unit 5: integration-lead readiness

## Source and ownership

I reviewed **Unit 5 Assignment 1 Instructions.pdf**, **Week2_SprintBacklog.pdf** (internally titled “Week 1–4 Sprint”), and the supplied data-flow screenshot. I use SQLite in place of PostgreSQL. I follow the revised backlog’s human-review behavior when interpreting the screenshot’s pass/fail wording.

I am Justin Gaffney, an integration lead. My assignment responsibility is **AI feature implementation and integration layout**. I share the integration-lead role with William Forest. I keep my contribution separate so I can coordinate interfaces and responsibilities with him when his implementation is available.

I will coordinate architecture decisions with Sophia Haywood and Md Abul Hashim, and shared API/interface specifications with Similun Krachokchol, Charles Le and Dawit Godie. I provide working integration schemas for that discussion.

## Actual integration layout

React reference client → authenticated FastAPI upload → bounded local document parser → approved skill buckets → Hermes Agent / Groq structured extraction → validated model findings → OPA → SQLite evaluation and decision audit → React human review.

I send the agent canonical skill mentions and page references instead of raw sanitized prose. I implement Week 4's approved-bucket requirement with a stronger, narrower privacy boundary. I limit extraction to skill evidence; I do not claim to extract arbitrary qualifications, years of experience or degrees. I give the agent no database credentials, SQL tool, policy editor or other tools. I route record writes and policy requests through FastAPI.

## Requirement-to-evidence map

| Requirement | Evidence / status |
|---|---|
| Modular AI wrapper with simulated and unexpected responses | `app/providers.py`, provider tests; real Hermes setup pinned to upstream source |
| Approved job-relevant inputs only | `app/privacy.py`; PII exclusion and equivalent-profile tests |
| Candidate-to-job workflow | `app/pipeline.py`; `/api/v1/evaluations` |
| Allowed / blocked / needs review | `Evaluation.policy_status`; all errors retain `needs_review`; blocked means missing documented requirements, not automatic candidate rejection |
| OPA uses AI findings | Validated `assessment.skills` becomes the OPA observed-skills input |
| Four audit fields | SQLite `decision_audit`: `job_requirements`, `approved_inputs`, `model_version`, `policy_result` plus AI metrics and phase |
| Every admitted AI request logged | `ai_request` snapshot committed before invocation; `completed` snapshot and evaluation saved atomically; interrupted requests retain the initial record |
| Under-ten-second AI target | Nine-second default wrapper deadline; timeout test; measured AI latency persisted. This bounds waiting, not a claim that live Groq always completes on time |
| Cost tracking | Token usage recorded when Hermes supplies it; demo cost explicitly zero; live billing cost explicitly unavailable, never incorrectly reported as free. Reconcile provider billing before claiming monetary-cost acceptance |
| Allowed / blocked React examples | `fixtures/allowed.txt`, `fixtures/blocked.txt`; `scripts/alpha_smoke.py` saves evidence and dashboard history |
| Audit / safe pause on policy failure | Real OPA tests plus failure tests; no fabricated policy approval |
| Integration compatibility | Strict Pydantic schemas, OpenAPI, frontend adapter, isolated contribution folder |
| CI / meaningful version control | Workflow and commits included; **remote CI run still blocked by repository write authorization** |
| Functional live AI alpha | **Pending a local Groq key and successful live smoke run**. Demo is not evidence of live AI functionality |
| Formal review of teammate module | **Pending teammate code**; I am waiting for my teammates to implement their modules |
| Exactly 250-word refinement report | **Pending real peer feedback and resulting changes**; use the worksheet below, not invented reviews |

## Demonstration and submission procedure

1. I follow the main README to start the demo or live services and React.
2. I run `uv run python scripts/alpha_smoke.py`. I open both new records in React and verify the displayed policy statuses, skill evidence, latency and human-review controls. I preserve `data/alpha-evidence.json` locally.
3. For live-AI acceptance, I repeat in `AI_MODE=hermes` with a local Groq key; I save evidence showing mode `hermes`. The fixture run cannot satisfy this gate.
4. I run CI checks. After GitHub write access is restored, I push `justin/resume-ai-integration`, open a PR, and record the successful Actions URL. I align this workflow with the team's actual Unit 4 pipeline when available; I have not received that pipeline.
5. I review an actual teammate module using `peer-review-worksheet.md`; I request feedback on this PR. I implement justified corrections and link the commits/tests.
6. I write exactly 250 words using those real observations. I submit the **shared repository link** and the individual report. The assignment does not require inventing a release tag, feedback, or collaboration history.

## Team-owned integration dependencies and technical debt

- Candidate/job CRUD and schemas from Weeks 1–2, production identity, policy-based data access, and the final team dashboard require team ownership and interface agreement. I supply upload, a fixture job catalog and token-based access; I do not claim complete implementation of those team backlog tasks.
- One reviewer token and one tenant are a temporary classroom boundary. Replace with authenticated roles and tenant claims before multi-user use. Current access checks happen before input is accepted or results saved; they are not a complete OPA authorization policy.
- SQLite is intentionally single-worker. Multi-worker request deduplication and distributed rate limiting are deferred; do not deploy with multiple workers and claim the same guarantees.
- Literal skill matching trades extraction breadth for privacy. Test negation/context cases with human reviewers before broadening extraction. Equivalent synthetic qualifications produce identical structured outcomes, not a numeric hiring score.
- HMAC identifiers are pseudonymous and not encryption. No raw resume is retained. SQLite is not encrypted at rest; use an encrypted deployment volume if the team stores sensitive fields. Do not claim that requirement is fully satisfied by hashing.
- Cost is unknown when the provider omits billing details. Store that uncertainty; reconcile with Groq billing rather than inventing a zero price.
- Startup fixtures and local checks are real engineering evidence, but are **not teammate feedback**. I identified these debts during my own implementation; I have not received independent peer feedback.
