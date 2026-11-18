#!/usr/bin/env bash
# See planning/decisions.md#D-031
set -euo pipefail

root="$(git rev-parse --show-toplevel)"
main_root="$(dirname "$(git rev-parse --path-format=absolute --git-common-dir)")"

usage() {
  echo "usage: scripts/wt.sh new <TASK-ID> | integrate | sync-all" >&2
  exit 2
}

cmd="${1:-}"
case "$cmd" in
  new)
    task="${2:-}"
    [ -n "$task" ] || usage
    target="$(dirname "$main_root")/$(basename "$main_root")-wt-$task"
    git -C "$main_root" worktree add "$target" -b "task/$task" preview
    make -C "$target" sync
    echo "Worktree ready: $target"
    ;;
  integrate)
    cd "$root"
    if ! git merge preview --no-edit; then
      echo "Merge conflict while merging preview. Resolve the conflicts, commit, then run make sync." >&2
      exit 1
    fi
    make sync
    ;;
  sync-all)
    git -C "$main_root" worktree list --porcelain | sed -n 's/^worktree //p' | while read -r path; do
      echo "== $path"
      make -C "$path" sync
    done
    ;;
  *)
    usage
    ;;
esac
