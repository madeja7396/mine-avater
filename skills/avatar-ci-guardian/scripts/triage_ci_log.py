#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


PATTERNS = [
    (
        r"py_compile|SyntaxError|IndentationError",
        "lint",
        "make lint",
        "Fix syntax or import issues first.",
    ),
    (
        r"check_scaffold\.py|scaffold_invalid|missing required",
        "scaffold",
        "make check_scaffold",
        "Restore required files/directories before other checks.",
    ),
    (
        r"check_eval_assets\.py|eval_assets_invalid|thresholds mismatch",
        "eval_assets",
        "make check_eval_assets",
        "Align specs/quality_thresholds.json with eval samples.",
    ),
    (
        r"mode=fast failed|eval_runner\.py --mode fast",
        "fast_eval",
        "make test_fast",
        "Fix metric regressions or sample thresholds.",
    ),
    (
        r"FAILED \(failures=|unittest",
        "unit_tests",
        "make test_unit",
        "Fix behavioral regressions and keep tests deterministic.",
    ),
    (
        r"mode=full failed|eval_runner\.py --mode full",
        "full_eval",
        "make test_full",
        "Run after fast and unit are green.",
    ),
]


def load_log(path: str | None) -> str:
    if path:
        return Path(path).read_text(encoding="utf-8")
    return sys.stdin.read()


def triage(log_text: str) -> list[tuple[str, str, str]]:
    findings: list[tuple[str, str, str]] = []
    seen = set()
    for pattern, gate, command, guidance in PATTERNS:
        if re.search(pattern, log_text, flags=re.IGNORECASE):
            if gate in seen:
                continue
            findings.append((gate, command, guidance))
            seen.add(gate)
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Map CI logs to local reproduction gates.")
    parser.add_argument("--log", default=None, help="Path to CI log file. Uses stdin if omitted.")
    args = parser.parse_args()

    log_text = load_log(args.log)
    findings = triage(log_text)

    if not findings:
        print("WARN: no_known_gate_matched")
        print("METRIC: ci_triage_detected=0")
        return 0

    print(f"METRIC: ci_triage_detected={len(findings)}")
    for idx, (gate, command, guidance) in enumerate(findings, start=1):
        print(f"GATE[{idx}]: {gate}")
        print(f"COMMAND[{idx}]: {command}")
        print(f"GUIDANCE[{idx}]: {guidance}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

