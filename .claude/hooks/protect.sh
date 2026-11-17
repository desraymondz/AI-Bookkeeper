#!/usr/bin/env bash
# See AGENTS.md#hard-rules and planning/decisions.md
set -euo pipefail
input="$(cat)"
tool="$(jq -r '.tool_name // ""' <<<"$input")"
path="$(jq -r '.tool_input.file_path // ""' <<<"$input")"
[ -z "$path" ] && exit 0
base="$(basename "$path")"

if [[ "$base" == .env* && "$base" != ".env.example" ]]; then
  echo "Blocked: $base holds secrets. Only .env.example may be edited." >&2
  exit 2
fi

if [[ "$path" == *"planning/04-test-spec.md" ]]; then
  norm() { sed -e 's/\[x\]/[ ]/g' -e 's/\[X\]/[ ]/g'; }
  case "$tool" in
    Write)
      echo "Blocked: 04-test-spec.md may only change by ticking [ ] to [x] with Edit. Expected results change via planning/decisions.md." >&2
      exit 2 ;;
    Edit)
      old="$(jq -r '.tool_input.old_string' <<<"$input" | norm)"
      new="$(jq -r '.tool_input.new_string' <<<"$input" | norm)"
      if [[ "$old" != "$new" ]]; then
        echo "Blocked: only [ ] to [x] status changes are allowed in 04-test-spec.md." >&2
        exit 2
      fi ;;
    MultiEdit)
      n="$(jq '.tool_input.edits | length' <<<"$input")"
      for ((i=0; i<n; i++)); do
        old="$(jq -r ".tool_input.edits[$i].old_string" <<<"$input" | norm)"
        new="$(jq -r ".tool_input.edits[$i].new_string" <<<"$input" | norm)"
        if [[ "$old" != "$new" ]]; then
          echo "Blocked: only [ ] to [x] status changes are allowed in 04-test-spec.md." >&2
          exit 2
        fi
      done ;;
  esac
fi
exit 0
