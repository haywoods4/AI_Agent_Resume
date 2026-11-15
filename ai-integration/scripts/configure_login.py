"""Set a local reviewer login without displaying or storing the password."""

import getpass
import os
import sys
from pathlib import Path

from dotenv import set_key

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))
from app.sessions import hash_password  # noqa: E402


def main():
    username = input("Reviewer username: ").strip()
    password = getpass.getpass("New password (at least 12 characters): ")
    confirm = getpass.getpass("Confirm password: ")
    if not username or len(username) > 128 or not 12 <= len(password) <= 256:
        raise SystemExit("Use a username and a password of 12–256 characters. Nothing saved.")
    if password != confirm:
        raise SystemExit("Passwords do not match. Nothing saved.")
    path = root / ".env"
    if not path.exists():
        raise SystemExit("Run scripts/init_env.py first.")
    set_key(path, "REVIEWER_USERNAME", username)
    set_key(path, "REVIEWER_PASSWORD_HASH", hash_password(password))
    os.chmod(path, 0o600)
    print("Login configured. Restart the API and sign in with your username and password.")


if __name__ == "__main__":
    main()
