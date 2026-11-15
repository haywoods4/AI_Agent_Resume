"""I use one SQLite store for evaluation records and decision audits.

I consolidated the backend foundation into app.store.Store so the root API and
integration API cannot write incompatible outcomes to separate databases.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "ai-integration"))
from app.store import Store  # noqa: E402,F401
