"""Run allowed/blocked synthetic candidates against the running API; save safe evidence."""

import json
import time
import uuid
from pathlib import Path

import httpx
from dotenv import dotenv_values

root = Path(__file__).resolve().parent.parent
settings = dotenv_values(root / ".env")
results = []
with httpx.Client(
    base_url="http://127.0.0.1:8000",
    timeout=30,
    trust_env=False,
    headers={"Authorization": f"Bearer {settings['REVIEWER_TOKEN']}"},
) as client:
    mode = client.get("/health").json()["mode"]
    for expected in ("allowed", "blocked"):
        started = time.monotonic()
        response = client.post(
            "/api/v1/evaluations",
            data={
                "request_id": f"alpha-{uuid.uuid4().hex}",
                "job_id": "backend-engineer",
                "candidate_email": f"{expected}@example.invalid",
            },
            files={
                "resume": (
                    f"{expected}.txt",
                    (root / f"fixtures/{expected}.txt").read_bytes(),
                    "text/plain",
                )
            },
        )
        response.raise_for_status()
        result = response.json()
        assert result["policy_status"] == expected, result["failure_code"]
        assert result["requires_human_review"] is True
        assert result["ai_metrics"]["latency_ms"] < 10000
        results.append(
            {
                "expected": expected,
                "evaluation": result,
                "workflow_ms": int((time.monotonic() - started) * 1000),
            }
        )
path = root / "data/alpha-evidence.json"
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps({"mode": mode, "results": results}, indent=2))
print(f"Allowed and blocked cases passed in {mode} mode. Evidence: data/alpha-evidence.json")
if mode == "demo":
    print("Fixture-model evidence only. Repeat in hermes mode for the live AI release gate.")
