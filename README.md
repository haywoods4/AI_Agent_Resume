# AI Resume Evaluator 

## System Architecture
* **Frontend:** React (TypeScript, Vite)
* **Backend API:** Python  (FastAPI)
* **Database:** SQLite (Decision audits & evaluation records)
* **AI Integration:** Hermes Agent configured for Groq LLM
* **Security & Compliance:** Open Policy Agent (OPA) for privacy filtering

## Git & Branching Strategy
This repository follows a strict integration workflow to satisfy Alpha release quality gates. 

* **`main`**: Production environment. Direct commits are blocked.
* **`develop`**: Staging environment. All feature branches must merge here first.

**Pull Request (PR) Requirements:**
1. All PRs must target the `develop` branch.
2. Passing CI/CD status checks (tests, linting).
3. At least one approving peer review. (Note: Interface Designers must verify backend API contracts against documentation before approval).

## Local Development
The FastAPI application entry point is `main:app`. When running locally via Uvicorn, interactive API documentation is available at `/docs`.
