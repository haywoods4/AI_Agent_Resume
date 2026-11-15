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
