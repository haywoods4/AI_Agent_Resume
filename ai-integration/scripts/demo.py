"""Launch FastAPI in explicit fixture-model mode with the real OPA server."""

import os
import subprocess
import sys
import time
from pathlib import Path

import httpx
import uvicorn
from dotenv import load_dotenv

root = Path(__file__).resolve().parent.parent
os.chdir(root)
sys.path.insert(0, str(root))
subprocess.run([sys.executable, "scripts/init_env.py"], check=True)
load_dotenv(root / ".env", override=False)
os.environ["AI_MODE"] = "demo"
os.environ["DATABASE_PATH"] = "data/demo.sqlite"
binary = root / "tools" / ("opa.exe" if os.name == "nt" else "opa")
if not binary.exists():
    raise SystemExit("Run uv run python scripts/setup_opa.py first")
policy = subprocess.Popen(
    [str(binary), "run", "--server", "--addr", "127.0.0.1:8181", "policies/"],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)
try:
    with httpx.Client(trust_env=False, timeout=0.3) as client:
        for _ in range(40):
            if policy.poll() is not None:
                raise SystemExit("OPA failed to start; check whether port 8181 is already in use")
            try:
                if client.get("http://127.0.0.1:8181/health").is_success:
                    break
            except httpx.HTTPError:
                pass
            time.sleep(0.05)
        else:
            raise SystemExit("OPA did not become ready")
    print("Demo model (not live inference), real OPA, SQLite. Reviewer token is in .env.")
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000)
finally:
    policy.terminate()
    policy.wait(timeout=5)
