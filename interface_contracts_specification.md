# My Alpha integration contract decisions

I integrated the shared routes below with the working pipeline. I retain the original interface proposal after this section for traceability; where it differs, this section documents my implemented Alpha behavior for team review.

- I expose `POST /api/v1/resumes/upload` with multipart `file`, catalog `job_id`, optional UUID `candidate_id`, optional `request_id` for retries, and optional `candidate_email` as a compatibility extension. I accept either an ID or email, not both. I generate an opaque identity when neither is provided. I accept PDF/DOCX/TXT up to512KiB. I use catalog IDs such as `backend-engineer`, not arbitrary job UUIDs.
- I authenticate all `/api/` requests against the configured reviewer token before buffering uploads. Any arbitrary bearer string is rejected. I serve the frontend through Vite's same-origin API proxy.
- I return `evaluation_id`, `candidate_id`, `job_id`, UTC `timestamp`, `verdict` (`PASS`, `FAIL`, `NEEDS_REVIEW`), `sanitized_payload.skills`, structured `policy_evaluations`, and a truthful `pii_scrubbed_summary` describing projection rather than claiming specific PII detection. I also include the existing evaluation fields for the React review UI. A dependency failure returns `NEEDS_REVIEW`, never a fabricated FAIL or PASS.
- I use `/api/v1/audit-logs` for tenant-scoped persisted completed decision snapshots, with job/verdict/date filters, limit1–100, offset, and total_records. I require timezone-aware date filters. I expose all four required audit fields plus model metrics. I retain initial AI-request audit snapshots internally, including interrupted requests.
- I connect FastAPI to the actual Hermes Agent HTTP API at `/v1/chat/completions`; Hermes uses Groq's `llama-3.3-70b-versatile`. I do not assume that a model named `hermes-3-llama-3-8b` is offered by Groq. Hermes Agent and the provider model are separate components.
- I send only approved skill IDs and page references to the model. I do not claim extraction of experience, degrees or certifications. I call OPA at `/v1/data/resume/screening/result`, validate its evidence result, and map it to the shared verdict envelope. I require human review for every outcome.
- I consolidate the SQLite persistence in `app/store.py`. I do not run the old simulated root endpoint or maintain a second `db.sqlite3`. I preserve the backend contribution in Git history and use root `main.py` as the integrated entry point.

## Original interface proposal (retained for review)

# Agentic Hiring Platform: Interface Contracts & Specifications

This document outlines the interface contracts, endpoints, data payloads, and schemas required for communication across each subsystem boundary in the agentic hiring platform.

---

## Part 1: Quick Reference Summary

### 1. React UI ⟷ FastAPI Backend Contracts

| Endpoint & Method | Payload Type / Format | Key Fields & Parameters | Description |
| :--- | :--- | :--- | :--- |
| **`POST /api/v1/resumes/upload`** | `multipart/form-data` | `file` (Binary: PDF/DOCX)<br>`job_id` (String UUID)<br>`candidate_id` (String UUID, optional) | Submits raw candidate resume files from the React frontend to the backend pipeline. |
| **Upload Response** | `application/json` | `evaluation_id`, `candidate_id`, `job_id`, `timestamp`, `verdict` (`PASS`/`FAIL`), `sanitized_payload`, `policy_evaluations`, `pii_scrubbed_summary` | Returns the final audited evaluation verdict and structured details back to the React dashboard. |
| **`GET /api/v1/audit-logs`** | Query Parameters & JSON Response | `job_id`, `verdict`, `start_date`, `end_date`, `limit`, `offset`<br>*Response:* `total_records`, `logs[]` | Retrieves historical audit logs and evaluation outcomes for compliance tracking. |

---

### 2. FastAPI Backend ⟷ LLM API (Hermes via Groq) Contracts

| Direction / Endpoint | Payload Structure | Key Fields | Description |
| :--- | :--- | :--- | :--- |
| **Request to Groq**<br>`POST /api/v1/resumes/extract-qualifications` | `application/json` | `model`: `"hermes-3-llama-3-8b"`<br>`response_format`: `{"type": "json_object"}`<br>`messages`: System prompt & sanitized resume text | FastAPI sends sanitized text (with PII removed) to extract candidate qualifications into structured JSON. |
| **Response from Groq** | `application/json` | `choices[0].message.content` (JSON string payload) | Returns extracted candidate metrics (e.g., `years_experience`, `degree_level`, `skills`). |

---

### 3. FastAPI Backend ⟷ Open Policy Agent (OPA) Contracts

| Direction / Endpoint | Payload Structure | Key Fields | Description |
| :--- | :--- | :--- | :--- |
| **Request to OPA**<br>`POST /v1/data/hiring/decision` | `application/json` | `input.job_requirements`: Minimum rules & required skills<br>`input.candidate`: Parsed JSON from Groq | FastAPI passes the structured JSON payload and job requirements to OPA for deterministic rule evaluation. |
| **Response from OPA** | `application/json` | `result.allow` (boolean)<br>`result.verdict` (`PASS`/`FAIL`)<br>`result.evaluations[]` (Rule breakdown) | Returns the strict pass/fail policy enforcement decision and explainability details. |

---

## Part 2: Detailed Endpoint & Schema Specifications

### 1. UI (React) ⟷ Backend (FastAPI)

#### A. Resume Upload Request
* **Endpoint:** `POST /api/v1/resumes/upload`
* **Content-Type:** `multipart/form-data`

```json
{
  "file": "<Binary File: resume.pdf | resume.docx>",
  "job_id": "string (UUID)",
  "candidate_id": "string (UUID, optional)"
}
```

#### B. Resume Processing & Verdict Response
* **Content-Type:** `application/json`

```json
{
  "evaluation_id": "eval-98234-abc",
  "candidate_id": "cand-5501-xyz",
  "job_id": "job-102938",
  "timestamp": "2026-11-09T19:57:00Z",
  "verdict": "PASS",
  "sanitized_payload": {
    "years_experience": 5,
    "degree_level": "Bachelor",
    "degree_field": "Computer Science",
    "skills": ["React", "Python", "FastAPI", "SQLite"],
    "certifications": ["AWS Certified Developer"],
    "meets_minimum_experience": true
  },
  "policy_evaluations": [
    {
      "rule_id": "rule_experience_threshold",
      "description": "Candidate must have at least 3 years of software engineering experience.",
      "passed": true,
      "details": "Extracted 5 years >= required 3 years."
    },
    {
      "rule_id": "rule_required_degree",
      "description": "Candidate must hold a Bachelor degree or higher in CS or related field.",
      "passed": true,
      "details": "Degree: Bachelor in Computer Science."
    }
  ],
  "pii_scrubbed_summary": {
    "pii_detected": true,
    "redacted_fields": ["email", "phone_number", "address", "name"]
  }
}
```

#### C. Fetch Audit Logs Request
* **Endpoint:** `GET /api/v1/audit-logs`
* **Query Parameters:** `job_id`, `verdict`, `start_date`, `end_date`, `limit`, `offset`
* **Content-Type:** `application/json`

```json
{
  "total_records": 128,
  "limit": 20,
  "offset": 0,
  "logs": [
    {
      "audit_id": "aud-1029-fff",
      "timestamp": "2026-11-09T18:30:12Z",
      "evaluation_id": "eval-98234-abc",
      "verdict": "PASS",
      "rules_triggered": ["rule_experience_threshold", "rule_required_degree"],
      "execution_time_ms": 142
    }
  ]
}
```

---

### 2. FastAPI Backend ⟷ LLM API (Hermes via Groq)

FastAPI sends sanitized text (with PII removed) to the Hermes model hosted on Groq to extract candidate data into structured JSON.

#### A. Groq API Request (Hermes Model / Structured JSON Output)
* **Endpoint:** `POST /v1/chat/completions` (via Groq API)
* **Content-Type:** `application/json`

```json
{
  "model": "hermes-3-llama-3-8b",
  "response_format": { "type": "json_object" },
  "messages": [
    {
      "role": "system",
      "content": "You are a data extraction parser. Extract candidate metrics from sanitized resume text into structured JSON format."
    },
    {
      "role": "user",
      "content": "Sanitized Resume Text:\nExperience: 5 years in full-stack development... Skills: React, Python, SQLite..."
    }
  ]
}
```

#### B. Groq API Response (Hermes Output)
* **Content-Type:** `application/json`

```json
{
  "id": "chatcmpl-hermes-789xyz",
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": "{\"years_experience\": 5, \"degree_level\": \"Bachelor\", \"degree_field\": \"Computer Science\", \"skills\": [\"React\", \"Python\", \"FastAPI\", \"SQLite\"], \"certifications\": [\"AWS Certified Developer\"]}"
      }
    }
  ]
}
```

---

### 3. FastAPI Backend ⟷ Open Policy Agent (OPA)

FastAPI sends the structured JSON payload extracted by Hermes to OPA for evaluation against hard-coded Rego policy rules.

#### A. OPA Data Query Request
* **Endpoint:** `POST /v1/data/hiring/decision`
* **Content-Type:** `application/json`

```json
{
  "input": {
    "job_requirements": {
      "min_years_experience": 3,
      "required_degrees": ["Bachelor", "Master", "PhD"],
      "allowed_fields": ["Computer Science", "Software Engineering", "Data Science"],
      "required_skills": ["React", "Python"]
    },
    "candidate": {
      "years_experience": 5,
      "degree_level": "Bachelor",
      "degree_field": "Computer Science",
      "skills": ["React", "Python", "FastAPI", "SQLite"],
      "certifications": ["AWS Certified Developer"]
    }
  }
}
```

#### B. OPA Evaluation Response
* **Content-Type:** `application/json`

```json
{
  "result": {
    "allow": true,
    "verdict": "PASS",
    "evaluations": [
      {
        "rule_id": "rule_experience_threshold",
        "description": "Candidate must have at least 3 years of software engineering experience.",
        "passed": true
      },
      {
        "rule_id": "rule_required_degree",
        "description": "Candidate must hold an accepted degree level and field.",
        "passed": true
      },
      {
        "rule_id": "rule_required_skills",
        "description": "Candidate must possess all mandatory core skills.",
        "passed": true
      }
    ]
  }
}
```
