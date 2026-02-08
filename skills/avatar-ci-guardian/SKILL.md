---
name: avatar-ci-guardian
description: Diagnose and resolve CI failures for the mine-avater repository by mapping failing logs to reproducible local gates and minimal fixes. Use when GitHub Actions jobs fail, when local checks diverge from CI results, or when Codex needs a strict failure-triage workflow for lint, scaffold checks, eval checks, fast/full eval, and unit tests.
---

# Avatar Ci Guardian

## Overview

Convert CI log output into concrete reproduction steps and correction order. Prioritize the smallest failing gate first, then run dependent gates.

## Workflow

1. Collect CI log snippet or job output.
2. Run `scripts/triage_ci_log.py` on that log.
3. Reproduce the first failing gate locally.
4. Apply minimal fix and rerun that gate.
5. Rerun `make check`, `make test_fast`, and `make test_unit`.
6. Run `make test_full` when the failure involved interfaces or thresholds.

## Commands

Triage from a file:

```bash
python3 skills/avatar-ci-guardian/scripts/triage_ci_log.py --log /path/to/ci.log
```

Triage from stdin:

```bash
cat /path/to/ci.log | python3 skills/avatar-ci-guardian/scripts/triage_ci_log.py
```

Run the suggested gate locally and iterate.

## Failure Priorities

1. Syntax/lint failures
2. Scaffold and eval asset consistency
3. Fast evaluation and unit tests
4. Full evaluation

## References

- Failure mapping and fix heuristics: `references/failure-playbook.md`
