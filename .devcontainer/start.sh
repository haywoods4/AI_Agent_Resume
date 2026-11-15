#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../ai-integration"
mkdir -p data
# flock prevents duplicate services when another editor attaches to this codespace.
nohup flock -n /tmp/resume-alpha-start.lock bash scripts/codespaces_run.sh > data/codespaces.log 2>&1 < /dev/null &
printf 'Starting Alpha. Open the private Resume Alpha port 5173. See ai-integration/data/codespaces.log if startup fails.\n'
