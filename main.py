"""I expose the integrated Alpha application from the repository root."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "ai-integration"))
from app.main import app, create_app  # noqa: E402,F401
