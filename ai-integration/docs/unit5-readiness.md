# Unit 5: integration-lead readiness

## My scope and preserved team work

I am Justin Gaffney. My responsibility is AI feature implementation and integration layout. I assembled the existing AI module, Sophia’s backend foundation and the team interface specification on `justin/alpha-integration`, targeting `develop` in [PR #4](https://github.com/haywoods4/AI_Agent_Resume/pull/4). I preserved the original authors and commits. The interface commit also appears in Charles’s PR #5; it is already in this branch, so I did not duplicate it or change his PR.

I verified the posted UMGC requirements: functional Alpha, reproducible repository, CI, formal review, and an exactly 250-word individual refinement report based on real feedback and technical debt. The LMS displays Nov 18, 2026 at 8:57 PM without an identified timezone; the instruction page says Tuesday 11:59 PM ET. I leave that discrepancy for the course lead rather than inventing a deadline.

## Implemented flow

React login and activity feed → authenticated FastAPI upload → bounded parser → approved skill IDs/pages → actual pinned Hermes/Groq → validated findings → real OPA → SQLite audit/evaluation → immutable human evidence review.

I preserve the shared upload/audit routes and original evaluation/history contracts. I extract skill mentions, not years, degrees, certificates or suitability scores. Policy allowed/blocked/needs_review never accepts or rejects a candidate. Raw résumé text and contacts are not sent to the model or policy engine.

## Evidence and boundaries

- I completed synthetic **live Groq** allowed/blocked runs, persisted a human follow-up and retrieved audits. [Live evidence](live-verification-2026-11-15.md) records the actual model and latency; monetary cost remains unknown.
- I previously verified both Actions runs at `3e9f5c48b3dfad142435c61474f83e4a91896a04`. Current-head checks must pass again after the UI/login changes; PR #4 shows the authoritative current checks.
- I added real local username/password sign-in, hashed password storage, expiring/revocable HttpOnly sessions, same-origin checks, login throttling and expiry recovery. I added in-app registration: the first fresh-local account becomes owner; later accounts need owner approval, and existing configured credentials are preserved. This is localhost, one shared classroom tenant, one worker, not production identity.
- I visually tested incorrect/correct login, empty/populated feed, evidence expansion, acknowledgement reset on close, saved synthetic review and logout using a separate synthetic demo database. Browser file attachment was blocked by the extension’s file-access setting; I performed the actual synthetic upload via the API instead. I do not claim that browser attachment passed or that these UI checks called live Groq.
- I completed a [formal review of Sophia’s module](https://github.com/haywoods4/AI_Agent_Resume/pull/2#pullrequestreview-5835176477). Her [original module feedback](https://github.com/haywoods4/AI_Agent_Resume/pull/1#pullrequestreview-5822823062) and [JSON-error feedback](https://github.com/haywoods4/AI_Agent_Resume/pull/3#pullrequestreview-5906569923) are real, but neither is approval of this latest assembled branch.

## Lead review and reproduction

I follow the root README setup, create an account in the app or sign in to my existing account, and choose explicit demo or live mode. I run the root verification commands, including `../test_main.py`, OPA tests and the React build. CI supplies the optional Redis service absent from local testing.

The lead should review PR #4 against develop, verify current-head CI, exercise the two synthetic fixtures and immutable human review, and confirm merge order. I have not merged anything, changed teammates’ PRs or submitted coursework. My individual report must remain exactly 250 words and reflect only completed work; final submission remains a separate user action.

## Remaining technical debt

I limit SQLite to one worker; durable sessions, distributed throttling, authenticated roles/tenant claims and deployment HTTPS remain future shared-deployment work. I use literal skill matching, so context/negation and proficiency require human verification. I keep contact identifiers pseudonymous, not anonymous; SQLite is not encrypted at rest. I do not claim fairness validation, legal acceptance, broader candidate/job CRUD or arbitrary qualification extraction. I record unavailable billing cost honestly. Team acceptance and release approval remain pending.

## Keyless launch addition

I added a GitHub Codespaces launch configuration and a keyless pretrained MiniLM neural-inference mode. The separate original live Hermes/Groq mode remains intact. The keyless model receives only approved skill IDs, drives structured evidence predictions, and fails closed when predictions contradict the document facts. Actual model tests cover all 64 combinations of the six current catalog skills plus adversarial false predictions and real OPA API integration. This validates the narrow classroom evidence task, not general résumé understanding, proficiency or hiring fairness. The current PR checks cover this code; fresh Codespaces provisioning remains unverified until someone with authorized Codespaces access launches it. A repository button is not an always-on public site or a promise of unlimited free compute.
