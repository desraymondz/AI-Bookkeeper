#!/usr/bin/env bash
# See AGENTS.md#commands
set -uo pipefail
ROOT="/Users/desmond/Documents/Side Projects/AI-Bookkeeper"
path="$(jq -r '.tool_input.file_path // ""')"
[ -z "$path" ] || [ ! -f "$path" ] && exit 0

case "$path" in
  "$ROOT"/api/*.py)
    if command -v uv >/dev/null && [ -f "$ROOT/api/pyproject.toml" ]; then
      cd "$ROOT/api"
      uv run --quiet ruff format "$path" >/dev/null 2>&1
      out="$(uv run --quiet ruff check --fix "$path" 2>&1)" || { echo "$out" >&2; exit 2; }
    fi ;;
  "$ROOT"/web/*.ts|"$ROOT"/web/*.tsx|"$ROOT"/web/*.js|"$ROOT"/web/*.jsx|"$ROOT"/web/*.json|"$ROOT"/web/*.css)
    if command -v pnpm >/dev/null && [ -d "$ROOT/web/node_modules" ]; then
      cd "$ROOT/web"
      out="$(pnpm exec biome check --write "$path" 2>&1)" || { echo "$out" >&2; exit 2; }
    fi ;;
esac
exit 0
