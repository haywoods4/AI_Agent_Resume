# Résumé Screening Alpha

A classroom résumé-review application built with React, FastAPI, SQLite and Open Policy Agent (OPA). It checks documented skill evidence against a job's requirements, records policy outcomes and saves a review trail. Every result requires human review; the application does not rank applicants or make hiring decisions.

## Try the keyless demo

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/haywoods4/AI_Agent_Resume/tree/justin/alpha-integration)

1. Sign in to GitHub and create the codespace from this public repository.
2. Wait for setup, then open the private **Resume Alpha** preview on port **5173**.
3. Create an account and choose **Try complete example** or **Try missing-skills example**. Compare the complete and missing-skills examples, expand their evidence and save a human review.

The default cloud demo runs actual **MiniLM neural inference**, OPA and SQLite without an API key or a server on your computer. GitHub login, Codespaces eligibility and available quota are still required. This is a private development preview, not an anonymous or always-on hosted website. See [the launch guide](CODESPACES.md) for setup, costs and troubleshooting.

**Branch status:** the integrated Alpha is on [`justin/alpha-integration`](https://github.com/haywoods4/AI_Agent_Resume/tree/justin/alpha-integration), awaiting team approval in [PR #4](https://github.com/haywoods4/AI_Agent_Resume/pull/4) against `develop`. The default `main` branch does not yet contain this integrated Alpha. Updated interface contracts from [PR #5](https://github.com/haywoods4/AI_Agent_Resume/pull/5) have merged into `develop` and are included in this integration branch.

## Share with the team or professor

Share the **Open in GitHub Codespaces** button above, not a personal `app.github.dev` preview URL. Each person signs in with their own GitHub account and creates their own isolated workspace from the public repository. They do not need repository collaborator access, Justin’s credentials or a model API key. Their GitHub account must be eligible for Codespaces, and their own compute/storage allowance applies. A preview remains private to its Codespace owner unless they separately change its visibility.

## What is included

- Account creation and sign-in, with immediate demo access and owner approval for additional live-workspace reviewers.
- Synthetic examples and résumé upload, approved-skill evidence extraction and explicit policy outcomes.
- Saved human reviews, SQLite audit history and optional tenant-scoped Redis contact lookup.
- Three clearly labeled execution modes: keyless local MiniLM, live Hermes Agent with Groq, and a simulated fixture mode for development.

The model receives approved skill IDs and page references, not raw résumé text or contact details. These are narrow evidence checks, not general qualification extraction: experience, degrees, proficiency and context still need human assessment. Use synthetic data for the classroom demo. Accounts in the same workspace share records; this is not a production multi-tenant service.

## Platform support

The interface runs in a browser; Codespaces runs the services on Linux independently of the visitor’s operating system. Verified environments are Linux Codespaces and local macOS. Windows setup uses WSL and has not been separately verified. Historical Mac setup fixes address portability, not a Mac-only product requirement.

## Run the simulated demo locally

Prerequisites: Python 3.12, uv, Node 22 or newer and Git. From the repository root:

```sh
cd ai-integration
uv sync --frozen
uv run python scripts/init_env.py
uv run python scripts/setup_opa.py
uv run python scripts/demo.py
```

In a second terminal:

```sh
cd ai-integration/react-client
npm ci
npm run dev
```

Open the Vite URL and create an account or sign in. Demo accounts enter immediately and share the synthetic demo workspace. The first account owns the workspace; additional accounts receive reviewer access, not owner permissions. This local command uses a **simulated model**, with real OPA and SQLite. It is not evidence of live AI inference.

## Run live Hermes/Groq

Stop the demo first because the modes share ports. Create a key at [Groq](https://console.groq.com/keys), then run from `ai-integration`:

```sh
uv run bash scripts/setup-hermes.sh
uv run python scripts/configure_groq.py
uv run python scripts/run_live.py
```

The hidden prompt verifies model access and stores the key in ignored local configuration. Never commit it. Start React as above; run `uv run python scripts/alpha_smoke.py` in another terminal to check synthetic allowed/blocked upload cases and save local verification results. Bash runtime scripts require WSL on Windows. See [the integration guide](ai-integration/README.md) for service configuration and limitations.

## Verification

A fresh GitHub Codespaces session was tested on November 15, 2026: setup, private HTTPS preview, account creation, complete/missing-skills examples, evidence inspection, saved review, logout and sign-in persistence. That browser run used keyless MiniLM, not Groq.

The separate [live Hermes/Groq verification](ai-integration/docs/live-verification-2026-11-15.md) records successful synthetic API evaluations, saved review and audit retrieval. CI at `d1ba66e4` passed lint, 52 backend tests, three OPA policy tests and the React production build. These checks do not establish production security, fairness or hiring validity.

```sh
cd ai-integration
uv run --extra keyless ruff check . ../main.py ../database.py ../test_main.py
uv run --extra keyless pytest -q tests ../test_main.py
tools/opa test policies/ -v
npm --prefix react-client ci
npm --prefix react-client run build
```

Keyless tests require the pinned model installed by `scripts/setup_keyless.py`; CI installs it automatically. Set `TEST_REDIS_URL` only for a running test Redis service. Team review and release approval are still required.
