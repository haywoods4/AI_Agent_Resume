#!/usr/bin/env bash
set -euo pipefail
project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export HERMES_HOME="$project_root/data/hermes"
export HERMES_RUNTIME_DIR="$project_root/data/hermes-runtime"
export UV_CACHE_DIR="$project_root/data/uv-cache"
cd "$project_root/vendor/hermes-agent"
exec scripts/run-in-hermes-env python -m hermes_cli.main "$@"
