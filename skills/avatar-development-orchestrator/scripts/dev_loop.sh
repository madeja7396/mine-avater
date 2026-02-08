#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-pre_pr}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"

case "$MODE" in
  baseline)
    make lint
    make check
    ;;
  pre_pr)
    make lint
    make check
    make test_fast
    make test_unit
    ;;
  full)
    make test_all
    ;;
  *)
    echo "ERROR: unknown_mode mode=$MODE (use baseline|pre_pr|full)"
    exit 1
    ;;
esac

echo "METRIC: dev_loop_completed mode=$MODE"

