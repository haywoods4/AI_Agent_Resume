"""I configure Groq locally without putting a key in Git or command history."""

import getpass
import os
import subprocess
import sys
from pathlib import Path

import httpx
from dotenv import set_key

root = Path(__file__).resolve().parent.parent
subprocess.run([sys.executable, str(root / "scripts/init_env.py")], check=True)
if not sys.stdin.isatty():
    raise SystemExit("Run this command in a local terminal to enter the Groq key.")
key = getpass.getpass("Groq API key (input hidden): ").strip()
if not key or any(c.isspace() for c in key):
    raise SystemExit("Enter a nonempty key without whitespace.")
try:
    with httpx.Client(timeout=15, follow_redirects=False) as client:
        response = client.get(
            "https://api.groq.com/openai/v1/models", headers={"Authorization": f"Bearer {key}"}
        )
        if response.status_code != 200:
            raise SystemExit(
                f"Groq rejected the check (HTTP {response.status_code}); key not saved."
            )
        if "llama-3.3-70b-versatile" not in {m["id"] for m in response.json()["data"]}:
            raise SystemExit("Configured model is unavailable for this account; key not saved.")
except (httpx.HTTPError, ValueError, KeyError):
    raise SystemExit("Could not verify Groq access; check the network and retry.") from None
path = root / "data/hermes/.env"
os.chmod(path, 0o600)
set_key(path, "GROQ_API_KEY", key)
set_key(root / ".env", "AI_MODE", "hermes")
print("Groq credentials and model access verified. Key saved in data/hermes/.env.")
print("Next: uv run python scripts/run_live.py, then scripts/alpha_smoke.py in another terminal.")
