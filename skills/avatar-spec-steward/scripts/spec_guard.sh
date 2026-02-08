#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"

python3 ci/check_eval_assets.py
python3 ci/check_scaffold.py
make test_fast
make test_unit

echo "METRIC: spec_guard_completed"

