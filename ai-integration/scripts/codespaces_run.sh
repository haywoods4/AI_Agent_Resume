#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ "${CODESPACES:-}" != "true" || -z "${CODESPACE_NAME:-}" ]]; then
  echo 'This launcher is only for GitHub Codespaces. Use the root README locally.' >&2
  exit 1
fi
# No public port or billing settings are changed by this script.
api_pid=""
ui_pid=""
cleanup() {
  trap - EXIT TERM INT
  # Terminate only the two process groups created below, including OPA/Vite children.
  for pid in "$api_pid" "$ui_pid"; do
    [[ -n "$pid" ]] && kill -TERM -- "-$pid" 2>/dev/null || true
  done
  wait "${api_pid:-}" "${ui_pid:-}" 2>/dev/null || true
}
trap cleanup EXIT TERM INT
echo 'Keyless local MiniLM neural inference, real OPA and SQLite. No Groq key required.'
setsid uv run --extra keyless python scripts/demo.py --keyless &
api_pid=$!
setsid npm --prefix react-client run dev -- --host 0.0.0.0 &
ui_pid=$!
# Either process exiting ends the companion process instead of leaving a false healthy preview.
wait -n "$api_pid" "$ui_pid"
