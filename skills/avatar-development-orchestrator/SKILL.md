---
name: avatar-development-orchestrator
description: Orchestrate day-to-day and long-term development loops for the mine-avater repository with task locking, quality gates, and controlled handoff. Use when Codex needs to start or continue implementation tasks, split work safely across agents, run pre-implementation and pre-PR checks, or close work with lock release and validation.
---

# Avatar Development Orchestrator

## Overview

Run a repeatable development loop for this repository. Enforce `current_tasks` locking and repository quality gates before and after code changes.

## Workflow

1. Confirm repository health before edits.
2. Acquire a task lock before substantial implementation.
3. Implement in small increments and run focused checks.
4. Run pre-PR gate checks.
5. Release the task lock and leave clear next actions.

## Commands

Run baseline checks:

```bash
./skills/avatar-development-orchestrator/scripts/dev_loop.sh baseline
```

Acquire a lock:

```bash
./skills/avatar-development-orchestrator/scripts/task_lock_ops.sh acquire <task> <owner> [ttl_minutes]
```

Run pre-PR checks:

```bash
./skills/avatar-development-orchestrator/scripts/dev_loop.sh pre_pr
```

Release a lock:

```bash
./skills/avatar-development-orchestrator/scripts/task_lock_ops.sh release <task> <owner>
```

Run full convergence checks:

```bash
./skills/avatar-development-orchestrator/scripts/dev_loop.sh full
```

## Decision Rules

- Run `baseline` before starting a new task.
- Run `pre_pr` before merge proposals.
- Run `full` when touching interfaces, thresholds, CI, or scaffold logic.
- Keep lock ownership strict; use `--force` only for stale-lock recovery.

## References

- Detailed loop patterns: `references/workflows.md`
- Task naming and lock policy: `references/task-naming.md`
