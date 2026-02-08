# Failure Playbook

## 1. Lint/Syntax

Signals:
- `py_compile`
- `SyntaxError`
- `IndentationError`

Action:
- Run `make lint`.
- Fix parse/import issues before any other gate.

## 2. Scaffold Drift

Signals:
- `scaffold_invalid`
- `missing required file`

Action:
- Run `make check_scaffold`.
- Restore required repository structure and core files.

## 3. Eval Asset Drift

Signals:
- `eval_assets_invalid`
- `thresholds mismatch`

Action:
- Run `make check_eval_assets`.
- Synchronize `specs/quality_thresholds.json` and `eval/*/samples.json`.

## 4. Fast Eval or Unit Regressions

Signals:
- `mode=fast failed`
- unittest failures

Action:
- Run `make test_fast` and `make test_unit`.
- Fix smallest failing unit first.

## 5. Full Eval Regressions

Signals:
- `mode=full failed`

Action:
- Run `make test_full` after fast/unit gates are green.
- Review model quality metric changes before threshold updates.

