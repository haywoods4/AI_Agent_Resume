"""I start the actual Hermes/Groq service, OPA and FastAPI together for the Alpha."""

import os
import subprocess
import sys
import time
from pathlib import Path

import httpx
import uvicorn
from dotenv import dotenv_values, load_dotenv

root = Path(__file__).resolve().parent.parent
os.chdir(root)
sys.path.insert(0, str(root))
load_dotenv(root / ".env")
profile = dotenv_values(root / "data/hermes/.env")
if not profile.get("GROQ_API_KEY"):
    raise SystemExit("First run: uv run python scripts/configure_groq.py")
if not (root / "vendor/hermes-agent/scripts/run-in-hermes-env").exists():
    raise SystemExit("First run: uv run bash scripts/setup-hermes.sh")
if not (root / "tools/opa").exists():
    raise SystemExit("First run: uv run python scripts/setup_opa.py")
if profile.get("API_SERVER_KEY") != os.environ.get("HERMES_API_KEY"):
    raise SystemExit("Synchronize HERMES_API_KEY in .env with API_SERVER_KEY in data/hermes/.env")
os.environ["AI_MODE"] = "hermes"
processes = []
try:
    for command, health, headers in (
        (
            [str(root / "tools/opa"), "run", "--server", "--addr", "127.0.0.1:8181", "policies/"],
            "http://127.0.0.1:8181/health",
            {},
        ),
        (
            ["bash", "scripts/hermes.sh", "gateway", "run"],
            "http://127.0.0.1:8642/v1/models",
            {"Authorization": f"Bearer {os.environ['HERMES_API_KEY']}"},
        ),
    ):
        process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        processes.append(process)
        with httpx.Client(timeout=1, trust_env=False) as client:
            for _ in range(120):
                if process.poll() is not None:
                    raise SystemExit(
                        "A service exited; check ports and run it separately for diagnostics."
                    )
                try:
                    if client.get(health, headers=headers).is_success:
                        break
                except httpx.HTTPError:
                    pass
                time.sleep(0.5)
            else:
                raise SystemExit(
                    "Service startup timed out; run the README service commands separately."
                )
    print("Live Hermes/Groq mode, real OPA and SQLite. Run alpha_smoke.py to verify inference.")
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, access_log=False)
finally:
    for process in reversed(processes):
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
