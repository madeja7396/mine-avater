# Task Naming

Use stable, grep-friendly lock names.

## Naming Pattern

`<area>_<action>`

Examples:
- `pipeline_preprocess`
- `pipeline_generator`
- `ci_eval_gate`
- `spec_threshold_update`
- `docs_guideline_sync`

## Rules

- Keep names lowercase and ASCII.
- Avoid timestamps in task names.
- Reuse existing names for the same workstream.
- Split mixed-scope work into separate locks.

