#!/usr/bin/env bash
set -euo pipefail

ACTION="${1:-}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"

if [[ -z "$ACTION" ]]; then
  echo "ERROR: missing_action (use acquire|release|status|reap)"
  exit 1
fi

case "$ACTION" in
  acquire)
    TASK="${2:-}"
    OWNER="${3:-}"
    TTL="${4:-120}"
    if [[ -z "$TASK" || -z "$OWNER" ]]; then
      echo "ERROR: usage acquire <task> <owner> [ttl_minutes]"
      exit 1
    fi
    python3 harness/task_lock.py acquire "$TASK" "$OWNER" --ttl-minutes "$TTL"
    ;;
  release)
    TASK="${2:-}"
    OWNER="${3:-}"
    if [[ -z "$TASK" || -z "$OWNER" ]]; then
      echo "ERROR: usage release <task> <owner>"
      exit 1
    fi
    python3 harness/task_lock.py release "$TASK" "$OWNER"
    ;;
  status)
    TASK="${2:-}"
    if [[ -z "$TASK" ]]; then
      echo "ERROR: usage status <task>"
      exit 1
    fi
    python3 harness/task_lock.py status "$TASK"
    ;;
  reap)
    python3 harness/task_lock.py reap
    ;;
  *)
    echo "ERROR: unknown_action action=$ACTION (use acquire|release|status|reap)"
    exit 1
    ;;
esac

