# Sync Policy

## Authoritative Files

1. `specs/quality_thresholds.json` for metric thresholds
2. `specs/interfaces.md` for intermediate artifact contract
3. `specs/architecture.md` for stage boundaries

## Mandatory Sync Paths

- If thresholds change:
  - Run `sync_thresholds.py`
  - Run `ci/check_eval_assets.py`
  - Run `make test_fast` and `make test_full`
- If interfaces change:
  - Update `pipeline/contracts.py`
  - Update related tests under `tests/`
  - Run `make check` and `make test_unit`
- If scaffold behavior changes:
  - Update scaffold tests
  - Run `make test_unit` and `make test_fast`

## Change Checklist

1. Update spec source file.
2. Synchronize dependent files.
3. Re-run checks.
4. Confirm no drift errors remain.

