#!/usr/bin/env bash
# See README.md (Run it locally) and planning/03-tech-stack.md section 13.
set -euo pipefail
command -v ngrok >/dev/null || { echo "ngrok is not installed: https://ngrok.com/download" >&2; exit 1; }
if [[ -n "${NGROK_DOMAIN:-}" ]]; then
  exec ngrok http --url="$NGROK_DOMAIN" 8000
fi
exec ngrok http 8000
