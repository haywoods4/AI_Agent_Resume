#!/usr/bin/env bash
set -euo pipefail
project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source_dir="$project_root/vendor/hermes-agent"
revision="$(python -c 'import json,sys; print(json.load(open(sys.argv[1]))["commit"])' "$project_root/config/hermes-source.json")"
if [ ! -d "$source_dir/.git" ]; then
  mkdir -p "$project_root/vendor"
  git init "$source_dir"
  git -C "$source_dir" remote add origin https://github.com/NousResearch/hermes-agent.git
  git -C "$source_dir" fetch --depth 1 origin "$revision"
  git -C "$source_dir" checkout --detach FETCH_HEAD
fi
if [ "$(git -C "$source_dir" rev-parse HEAD)" != "$revision" ]; then
  echo 'Existing Hermes checkout differs from the pin; preserve it and use a fresh vendor folder.' >&2
  exit 1
fi
export HERMES_HOME="$project_root/data/hermes"
export HERMES_RUNTIME_DIR="$project_root/data/hermes-runtime"
export UV_CACHE_DIR="$project_root/data/uv-cache"
mkdir -p "$HERMES_HOME" "$HERMES_RUNTIME_DIR"
if [ ! -f "$HERMES_HOME/config.yaml" ]; then cp "$project_root/config/hermes-config.yaml" "$HERMES_HOME/config.yaml"; fi
cd "$source_dir"
scripts/run-in-hermes-env python -m hermes_cli.main --version
echo 'Set GROQ_API_KEY in data/hermes/.env, then start bash scripts/hermes.sh gateway run.'
