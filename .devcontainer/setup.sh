#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../ai-integration"
python -m pip install --disable-pip-version-check uv==0.13.5
uv sync --frozen --extra keyless
uv run python scripts/init_env.py
uv run python scripts/setup_opa.py
uv run --extra keyless python scripts/setup_keyless.py
npm --prefix react-client ci
npm --prefix react-client run build
printf '\nSetup complete. The private forwarded port 5173 opens the app.\n'
