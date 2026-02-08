---
name: avatar-spec-steward
description: Keep architecture, interface, and quality specifications consistent with executable checks in the mine-avater repository. Use when Codex changes thresholds, pipeline interfaces, CI/test policies, scaffold behavior, or any files under specs/eval/ci that must stay synchronized to prevent configuration drift.
---

# Avatar Spec Steward

## Overview

Maintain spec integrity across human-readable docs and machine checks. Prevent drift between `specs/quality_thresholds.json` and `eval/*/samples.json`.

## Workflow

1. Update authoritative spec files first.
2. Synchronize dependent eval assets.
3. Run repository consistency checks.
4. Update tests/docs tied to changed contract.
5. Verify all gates before handoff.

## Commands

Synchronize thresholds:

```bash
python3 skills/avatar-spec-steward/scripts/sync_thresholds.py
```

Run drift checks:

```bash
./skills/avatar-spec-steward/scripts/spec_guard.sh
```

## Guardrails

- Treat `specs/quality_thresholds.json` as authoritative for metric thresholds.
- Update `specs/interfaces.md` and contract tests together.
- Avoid threshold relaxation without explicit reason in change notes.
- Run full gate checks for architecture or interface changes.

## References

- Synchronization policy and checklist: `references/sync-policy.md`
