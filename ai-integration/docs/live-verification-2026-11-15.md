# My live Alpha verification

I completed a synthetic live workflow on my Mac on November 15, 2026. I used pinned upstream Hermes `21ae0e1238fdf466fa52a85a6ebf75d6899e49da`, Groq `openai/gpt-oss-20b`, real OPA 1.0.1, and SQLite through the shared upload API.

- My allowed fixture completed with policy_status `allowed`, AI latency 2,393 ms, total workflow 2,557 ms, and 1,413 prompt / 214 completion tokens.
- My blocked fixture completed with policy_status `blocked`, AI latency 841 ms, total workflow 962 ms, and 1,383 prompt / 211 completion tokens.
- Both required human review and had no failure code. Neither result made a hiring decision.
- I saved a synthetic `FOLLOW_UP_REQUIRED` review, retrieved it again, and verified the evaluation appeared in the audit endpoint. The returned audits did not contain the fixture email addresses.
- My privacy projection tests check that only approved skill IDs/page references cross the model boundary. This run used synthetic fixtures, not real applicants.
- Monetary cost was unavailable and remained null. These two successful requests do not establish production latency, fairness, hiring validity, or load capacity.

My Mac checks passed Ruff, 33 backend tests, three OPA policy tests, root application import, and the React TypeScript/production build. One optional Redis test was skipped locally because no local test Redis service was installed. CI supplies Redis; I report its current-head result separately in the PR.

The automated smoke and review checks exercised the live API. The previously supplied dashboard screenshot used a simulated model and must not be presented as a live Groq browser test. I have not merged the integration PR or submitted coursework.
