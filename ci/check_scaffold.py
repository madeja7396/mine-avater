from __future__ import annotations

from pathlib import Path


REQUIRED_DIRS = [
    Path("current_tasks"),
    Path("specs"),
    Path("harness"),
    Path("pipeline"),
    Path("eval/fast"),
    Path("eval/full"),
    Path("ci"),
    Path("logs"),
    Path("tests"),
]

REQUIRED_FILES = [
    Path("README.md"),
    Path("AGENTS.md"),
    Path("CONTRIBUTING.md"),
    Path("Makefile"),
    Path("specs/quality.md"),
    Path("specs/interfaces.md"),
    Path("specs/architecture.md"),
    Path("specs/quality_thresholds.json"),
    Path("docs/guidelines/development.md"),
    Path("docs/guidelines/testing-ci.md"),
    Path("harness/task_lock.py"),
    Path("ci/eval_runner.py"),
    Path("ci/check_eval_assets.py"),
    Path("ci/check_project_skills.py"),
    Path("ci/smoke_scaffold.py"),
    Path("pipeline/contracts.py"),
    Path("pipeline/config.py"),
    Path("pipeline/engine.py"),
    Path("pipeline/preprocess.py"),
    Path("pipeline/vit.py"),
    Path("pipeline/generator.py"),
    Path("pipeline/postprocess.py"),
    Path("pipeline/scaffold.py"),
    Path("pipeline/run_scaffold.py"),
    Path("eval/fast/samples.json"),
    Path("eval/full/samples.json"),
    Path("scripts/bootstrap_dev.sh"),
    Path("skills/avatar-development-orchestrator/SKILL.md"),
    Path("skills/avatar-ci-guardian/SKILL.md"),
    Path("skills/avatar-spec-steward/SKILL.md"),
]


def main() -> int:
    errors: list[str] = []

    for path in REQUIRED_DIRS:
        if not path.is_dir():
            errors.append(f"ERROR: missing required directory {path}")

    for path in REQUIRED_FILES:
        if not path.is_file():
            errors.append(f"ERROR: missing required file {path}")

    if errors:
        print(f"ERROR: scaffold_invalid failures={len(errors)}")
        for error in errors:
            print(error)
        return 1

    print(
        "METRIC: scaffold_valid "
        f"directories={len(REQUIRED_DIRS)} files={len(REQUIRED_FILES)} failures=0"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
