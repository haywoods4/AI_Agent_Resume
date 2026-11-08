"""Generate local secrets without printing them or overwriting existing configuration."""

import os
import secrets
import shutil
from pathlib import Path

from dotenv import dotenv_values

root = Path(__file__).resolve().parent.parent
env_path = root / ".env"
if not env_path.exists():
    content = (root / ".env.example").read_text()
    for key in ["HERMES_API_KEY", "REVIEWER_TOKEN", "PII_HMAC_KEY"]:
        content = content.replace(f"{key}=\n", f"{key}={secrets.token_hex(32)}\n")
    env_path.write_text(content)
    os.chmod(env_path, 0o600)
profile = root / "data" / "hermes"
profile.mkdir(parents=True, exist_ok=True, mode=0o700)
if not (profile / "config.yaml").exists():
    shutil.copyfile(root / "config/hermes-config.yaml", profile / "config.yaml")
if not (profile / ".env").exists():
    values = dotenv_values(env_path)
    if not values.get("HERMES_API_KEY"):
        raise SystemExit("Set HERMES_API_KEY in .env before initializing the Hermes profile")
    (profile / ".env").write_text(f"API_SERVER_KEY={values['HERMES_API_KEY']}\nGROQ_API_KEY=\n")
    os.chmod(profile / ".env", 0o600)
print("Configuration prepared. Reviewer token: .env. Set GROQ_API_KEY in data/hermes/.env.")
