#!/usr/bin/env bash
# See planning/03-tech-stack.md#12-testing-strategy
set -uo pipefail
ROOT="/Users/desmond/Documents/Side Projects/AI-Bookkeeper"
input="$(cat)"
[ "$(jq -r '.stop_hook_active // false' <<<"$input")" = "true" ] && exit 0

cap() { perl -e 'alarm shift; exec @ARGV' "$@"; }
fail=0
log=""

if [ -f "$ROOT/api/pyproject.toml" ] && [ -d "$ROOT/api/tests" ] && command -v uv >/dev/null; then
  out="$(cd "$ROOT/api" && cap 20 uv run --quiet pytest -m "not integration" -q -x 2>&1)"; rc=$?
  # 5 = no tests collected
  if [ $rc -ne 0 ] && [ $rc -ne 5 ]; then fail=1; log+="API unit tests failed:\n$(tail -30 <<<"$out")\n"; fi
fi

if [ -f "$ROOT/web/package.json" ] && [ -d "$ROOT/web/node_modules" ] && command -v pnpm >/dev/null; then
  out="$(cd "$ROOT/web" && cap 15 pnpm exec vitest run --passWithNoTests 2>&1)"; rc=$?
  if [ $rc -ne 0 ]; then fail=1; log+="Web tests failed:\n$(tail -30 <<<"$out")\n"; fi
fi

if [ $fail -ne 0 ]; then printf "%b" "$log" >&2; exit 2; fi
exit 0
