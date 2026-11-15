"""I configure Groq locally without putting a key in Git or command history."""

import getpass
import os
import subprocess
import sys
from pathlib import Path

import httpx
from dotenv import dotenv_values, set_key

SUPPORTED_MODELS = ("openai/gpt-oss-20b", "openai/gpt-oss-120b", "llama-3.3-70b-versatile")


def select_model(catalog):
    available = {item["id"] for item in catalog["data"] if item.get("active", True)}
    for model in SUPPORTED_MODELS:
        if model in available:
            return model
    raise ValueError("No supported production text model is enabled for this account")


def main():
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
            model = select_model(response.json())
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        raise SystemExit(
            "No supported model could be verified; check Groq model permissions/network. "
            "Key not saved."
        ) from None
    # Keep the existing profile's tool/memory/security configuration unchanged.
    config_path = root / "data/hermes/config.yaml"
    config = config_path.read_text()
    previous = dotenv_values(root / ".env").get("INFERENCE_MODEL_VERSION", "")
    previous = previous.removeprefix("groq/")
    known = tuple(dict.fromkeys((previous, *SUPPORTED_MODELS)))
    replaced = False
    for candidate in known:
        if candidate and f"default: {candidate}" in config:
            config = config.replace(f"default: {candidate}", f"default: {model}")
            config = config.replace(f"- {candidate}", f"- {model}")
            replaced = True
            break
    if not replaced:
        raise SystemExit(
            "Unrecognized Hermes model configuration; preserve it and review manually."
        )
    config_path.write_text(config)
    path = root / "data/hermes/.env"
    os.chmod(path, 0o600)
    set_key(path, "GROQ_API_KEY", key)
    set_key(root / ".env", "AI_MODE", "hermes")
    set_key(root / ".env", "INFERENCE_MODEL_VERSION", f"groq/{model}")
    print(f"Groq credentials and model access verified: {model}.")
    print("Key saved in data/hermes/.env; live inference has not been tested yet.")
    print("Next: uv run python scripts/run_live.py, then scripts/alpha_smoke.py.")


if __name__ == "__main__":
    main()
