# Development Workflows

## 1. New Task Workflow

1. Run `dev_loop.sh baseline`.
2. Acquire lock with `task_lock_ops.sh acquire`.
3. Implement minimum change set.
4. Run `make test_fast` after each meaningful edit.
5. Run `dev_loop.sh pre_pr`.
6. Release lock.

## 2. Risky Change Workflow

Use for interface, CI, eval, or architecture changes.

1. Run New Task Workflow steps 1-5.
2. Run `dev_loop.sh full`.
3. Update `specs/` if contracts or thresholds moved.
4. Release lock only after full checks pass.

## 3. Emergency Recovery Workflow

1. Run `task_lock_ops.sh status <task>`.
2. Run `task_lock_ops.sh reap` if lock is expired.
3. Re-acquire lock with current owner.
4. Run `dev_loop.sh baseline` before new edits.

