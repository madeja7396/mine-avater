from __future__ import annotations

import json
from pathlib import Path
from typing import Any


THRESHOLDS_FILE = Path("specs/quality_thresholds.json")
EVAL_FILES = [
    Path("eval/fast/samples.json"),
    Path("eval/full/samples.json"),
]

REQUIRED_TOP_LEVEL_KEYS = {"thresholds", "aggregate", "samples"}
REQUIRED_SAMPLE_KEYS = {
    "id",
    "lipsync_mae",
    "mouth_breakage_rate",
    "temporal_jump",
    "psnr",
    "ssim",
}
REQUIRED_AGGREGATE_KEYS = {"oom_rate", "failure_rate", "throughput_fps"}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def as_float_dict(raw: dict[str, Any]) -> dict[str, float]:
    return {key: float(value) for key, value in raw.items()}


def validate_numeric_fields(payload: dict[str, Any], file_path: Path) -> list[str]:
    errors: list[str] = []

    aggregate = payload.get("aggregate", {})
    for key in REQUIRED_AGGREGATE_KEYS:
        try:
            float(aggregate[key])
        except (KeyError, TypeError, ValueError):
            errors.append(f"ERROR: {file_path} invalid aggregate.{key}")

    samples = payload.get("samples", [])
    if not isinstance(samples, list) or not samples:
        errors.append(f"ERROR: {file_path} samples must be non-empty list")
        return errors

    for sample in samples:
        sample_id = sample.get("id", "unknown")
        for key in REQUIRED_SAMPLE_KEYS - {"id"}:
            try:
                float(sample[key])
            except (KeyError, TypeError, ValueError):
                errors.append(f"ERROR: {file_path} sample={sample_id} invalid {key}")
    return errors


def validate_file(file_path: Path, thresholds: dict[str, float]) -> list[str]:
    payload = load_json(file_path)
    errors: list[str] = []

    top_keys = set(payload.keys())
    missing = sorted(REQUIRED_TOP_LEVEL_KEYS - top_keys)
    if missing:
        errors.append(f"ERROR: {file_path} missing_keys={','.join(missing)}")

    payload_thresholds_raw = payload.get("thresholds", {})
    try:
        payload_thresholds = as_float_dict(payload_thresholds_raw)
    except (TypeError, ValueError):
        payload_thresholds = {}
        errors.append(f"ERROR: {file_path} thresholds must be numeric")

    if set(payload_thresholds.keys()) != set(thresholds.keys()):
        errors.append(f"ERROR: {file_path} thresholds keys mismatch")
    else:
        for key, expected in thresholds.items():
            if abs(payload_thresholds[key] - expected) > 1e-9:
                errors.append(
                    f"ERROR: {file_path} thresholds mismatch key={key} "
                    f"expected={expected:.6f} got={payload_thresholds[key]:.6f}"
                )

    errors.extend(validate_numeric_fields(payload, file_path))
    return errors


def main() -> int:
    thresholds = as_float_dict(load_json(THRESHOLDS_FILE))
    errors: list[str] = []

    for file_path in EVAL_FILES:
        if not file_path.exists():
            errors.append(f"ERROR: missing eval file {file_path}")
            continue
        errors.extend(validate_file(file_path, thresholds))

    if errors:
        print(f"ERROR: eval_assets_invalid failures={len(errors)}")
        for error in errors:
            print(error)
        return 1

    print(f"METRIC: eval_assets_valid files={len(EVAL_FILES)} failures=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

