# Résumé Screening Alpha: Integration Handoff

**CMSC 495 · Unit 8 Final Project Portfolio**
**Lead integrator:** Justin Gaffney

Integration baseline: [develop at `8f281bc`](https://github.com/haywoods4/AI_Agent_Resume/tree/8f281bc1981343e20688bf824be049b663aea1c4). [PR #1](https://github.com/haywoods4/AI_Agent_Resume/pull/1) introduced the AI integration; [PR #4](https://github.com/haywoods4/AI_Agent_Resume/pull/4) combined it with the team's backend and interface work. Both are merged. Use this commit and the linked CI runs for the portfolio baseline as the code reference for the verification below. This baseline is not a production release.

## 1. Submit a résumé for evidence review

**React → FastAPI → parser → approved skill projection**

A signed-in reviewer selects a job from the catalog and uploads a résumé or chooses a synthetic example. The shared upload contract is `POST /api/v1/resumes/upload`; the React reference path `POST /api/v1/evaluations` reaches the same evaluation pipeline and store. FastAPI accepts text-based PDF, DOCX and TXT up to 512 KiB. It rejects unsupported or unparseable documents. The parser extracts evidence; the projection supplies only the job's approved skill IDs, where they were mentioned, and the page count. The model does not receive names, contact information or the raw résumé.

## 2. Assess the projected evidence, then check policy

**FastAPI → selected model adapter → response validation → OPA → SQLite**

Use the mode label to identify which adapter ran:

- **Keyless:** MiniLM ONNX inference runs locally in the Codespace without a Groq key.
- **Live:** The FastAPI adapter calls Hermes Agent, which calls the configured Groq model. The recorded synthetic run used `openai/gpt-oss-20b`.
- **Simulated:** A fixture adapter supports development; its output is not live inference evidence.

The pipeline checks model output against approved input. OPA evaluates required versus documented skills using structured evidence, not the résumé. In the upload envelope, `PASS` and `FAIL` describe evidence coverage only. Dependency failures can lead to `NEEDS_REVIEW`; the system does not invent an assessment. Neither a documented mention nor a missing item settles whether a person has the skill. Every result needs human review.

## 3. Save the human review and trace the outcome

**React evidence card → review API → SQLite → review feed and audit**

The reviewer can inspect skill evidence and save `CONFIRMED_EVIDENCE` or `FOLLOW_UP_REQUIRED` with a reason. The review endpoint is `POST /api/v1/evaluations/{evaluation_id}/review`. Completed evaluation snapshots are retrievable through `GET /api/v1/audit-logs`. The review is a recorded evidence check, not a recommendation or a hiring decision. The separate account store is for sign-in; it does not duplicate evaluation records.

## 4. Look up an existing candidate without sending identifiers to the model

**Authenticated inquiry → authoritative SQLite record → optional Redis projection**

`POST /api/v1/candidates/inquiry` accepts an authorized email or phone inquiry. The backend derives a tenant-scoped pseudonymous identifier. For a fresh inquiry, it checks SQLite first for current data and the sensitivity flag. If enabled, Redis can return a matching nonsensitive projection; sensitive records bypass Redis and failures fall back to SQLite. This optional path does not grant the model access to candidate identifiers and does not create a new evaluation.

## Contribution and limits

[Verification evidence](UNIT8_VERIFICATION.md) · [Video demo segment](UNIT8_DEMO.md)

As lead integrator, I contributed the model, policy and privacy workflow and integrated the team's backend and interface work with the React reviewer experience, shared evaluation API, and Codespaces demo. Linked pull requests record individual changes and preserve original contributions. Use the team roster and each member's confirmed contribution in the shared portfolio rather than crediting the integration role for the whole system.

The Alpha uses a single-worker classroom setup, a narrow skill catalog and shared demo workspace. It does not do OCR, validate proficiency, rank applicants, measure fairness or establish production capacity. See the pinned [interface contract](https://github.com/haywoods4/AI_Agent_Resume/blob/8f281bc1981343e20688bf824be049b663aea1c4/interface_contracts_specification.md) and [launch instructions](https://github.com/haywoods4/AI_Agent_Resume/blob/8f281bc1981343e20688bf824be049b663aea1c4/CODESPACES.md).
