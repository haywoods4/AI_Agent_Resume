# Unit 8 workspace verification

## Run the reviewer workspace

For the keyless browser demo after this change is on the team branch, open [develop in GitHub Codespaces](https://codespaces.new/haywoods4/AI_Agent_Resume/tree/develop) and use the private preview on port 5173. GitHub sign-in, Codespaces availability and quota apply. To review this change before it is merged, use its PR branch instead of `develop`.

To run from a local checkout with Python 3.12, uv and Node 22 or newer:

```sh
cd ai-integration
uv sync --frozen --extra keyless
uv run --extra keyless python scripts/setup_opa.py
uv run --extra keyless python scripts/setup_keyless.py
uv run --extra keyless python scripts/demo.py --keyless
```

From the repository root in a second terminal, run `npm --prefix ai-integration/react-client ci` and `npm --prefix ai-integration/react-client run dev`. Open the Vite URL on port 5173. This runs the pinned local MiniLM model, real OPA and a local SQLite demo database; no Groq credential is needed.

Create a classroom reviewer account and use **Try complete example** and **Try missing-skills example**. Expand the result and compare it with the original example text. Save a follow-up review and reload to confirm it remains. Under **Record lookup & audit tools**, load the audit list and compare evaluation references. Use only synthetic résumés. A candidate email is optional for upload; omitting one means there is no email to look up for that record. Saved human reviews are immutable in this Alpha.

## Checks on this change

- Built the React client with TypeScript and Vite. Ruff passed. OPA passed 3 of 3 policy tests.
- The macOS (Apple silicon) Python run passed 60 tests and skipped 2: the real Redis case requires a configured test service, and the Codespaces process-group case requires Linux `setsid`. The GitHub Linux workflow supplies Redis and tests the launcher there. Local statement coverage for `ai-integration/app` was 90% (894 of 992 statements); this is not React coverage. One upstream Starlette/AnyIO deprecation warning was reported.
- Chrome with local real MiniLM, OPA and SQLite: desktop account creation, examples with 4 of 4 and 1 of 4 required skills mentioned, focus sent to the result, follow-up saved and visible after reload, and audit list with record references. At 390 px, the page did not overflow horizontally; a manual TXT upload worked with no email; oversize files were rejected before upload. Sign-in, sign-out, and remaining signed out after reload were verified.
- Intercepted browser responses tested a non-JSON 401, 413, and 500, plus a JSON storage 503. These were UI failure simulations, not a database failure in the live run. A dropped upload connection was also simulated; retrying the same input reused its request ID. The app asks the reviewer to verify saved history when the outcome is uncertain.
- Local loopback HTTP timings using real MiniLM, OPA and SQLite: 10 sequential recorded requests per example after one warm-up each, with no evaluation errors. Complete: median 128.91 ms (122.09–146.05 ms). Missing: median 124.41 ms (121.63–129.78 ms). These are end-to-end local upload timings, not Groq inference, concurrent load, or a production benchmark.

## What the safeguards show

Synthetic tests confirm the approved SQL identifier is emitted for explicitly catalogued SQL, PostgreSQL and SQLite wording. The phrase “joined related tables” alone is not mapped to SQL; this observable limitation is why the missing-evidence cue sends the reviewer back to the original. The model still receives a narrow skill projection and cannot determine proficiency or fairness. The classroom workspace intentionally shares records among approved reviewers. Per-opening access controls, correction of saved reviews through a traceable amendment, and production rollout were not added or verified.
