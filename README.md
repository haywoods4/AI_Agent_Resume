# AI résumé evaluator — Alpha integration

I assembled the backend foundation, interface specification and AI integration on `justin/alpha-integration` for review against `develop`. I keep `main` reserved for the team's Alpha release. I preserve the original contributions in the merge history.

## My quick demo setup

I use Python 3.12, uv, Node 22 or newer, and Git. From the repository root I run:

```sh
cd ai-integration
uv sync --frozen
uv run python scripts/init_env.py
uv run python scripts/configure_login.py
uv run python scripts/setup_opa.py
uv run python scripts/demo.py
```

In a second terminal I run:

```sh
cd ai-integration/react-client
npm ci
npm run dev
```

I open the Vite URL, sign in with my configured reviewer username and password, and upload `fixtures/allowed.txt` and `fixtures/blocked.txt` using the backend-engineer job. I check both policy outcomes, record a human review, and use “Check saved audits” under “Record lookup & audit tools” to verify persistence. This demo uses a **simulated model, real OPA and SQLite**, not live Groq.

From `ai-integration` I can also run `uv run python scripts/alpha_smoke.py` to save the safe results in `data/alpha-evidence.json`.

## My live Groq setup

I create my key at https://console.groq.com/keys, then run these commands from `ai-integration`:

```sh
uv run bash scripts/setup-hermes.sh
uv run python scripts/configure_groq.py
uv run python scripts/run_live.py
```

I enter my key at the hidden prompt; the command verifies account/model access and saves the key in the ignored `data/hermes/.env`. I stop the demo before starting live services because they use the same ports. I start React as above, then run `uv run python scripts/alpha_smoke.py` in another terminal to check the complete live workflow. I only claim live AI acceptance after that check succeeds in `hermes` mode. On Windows I use WSL for the Bash runtime scripts.

## My integrated boundaries

I run one FastAPI application and one SQLite store. Root `main.py` exposes that same application; `database.py` exposes its store instead of maintaining a separate SQLAlchemy database. I use the shared `/api/v1/resumes/upload` and `/api/v1/audit-logs` endpoints. I retain `/api/v1/evaluations` for review/history compatibility.

I record the effective Alpha contract in [the interface specification](interface_contracts_specification.md). I limit extraction to approved skill evidence; years of experience, degrees and certificates remain unimplemented rather than fabricated. PASS/FAIL describe documented skill coverage, not a hiring decision, and all outcomes require human review.

## My verification commands

```sh
cd ai-integration
uv run ruff check . ../main.py ../database.py ../test_main.py
uv run pytest -q tests ../test_main.py
tools/opa test policies/ -v
cd react-client
npm run build
```

I set `TEST_REDIS_URL` only when a local test Redis service is running. GitHub Actions supplies Redis and OPA. I use the existing [integration setup guide](ai-integration/README.md) for individual service commands and privacy limitations.

## My remaining release checks

I verified the posted UMGC assignment and completed the synthetic live Groq smoke run, saved review, and audit retrieval ([evidence](ai-integration/docs/live-verification-2026-11-15.md)). I still need team review of the integration decisions and final release approval. I have not merged any team PR or submitted coursework. I keep the local single-reviewer login and single-worker SQLite limitations explicit. My integration branch includes the other team PRs, so I will coordinate their merge order rather than merging competing versions independently.
