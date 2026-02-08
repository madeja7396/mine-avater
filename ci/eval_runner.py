from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean
from typing import Any


DEFAULT_FILE_BY_MODE = {
    "fast": Path("eval/fast/samples.json"),
    "full": Path("eval/full/samples.json"),
}
DEFAULT_THRESHOLDS_FILE = Path("specs/quality_thresholds.json")


def load_payload(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_thresholds(path: Path) -> dict[str, float]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {key: float(value) for key, value in raw.items()}


def compare_thresholds(
    expected: dict[str, float],
    got: dict[str, Any],
    tol: float = 1e-9,
) -> list[str]:
    errors: list[str] = []
    got_keys = set(got.keys())
    expected_keys = set(expected.keys())

    missing = sorted(expected_keys - got_keys)
    extra = sorted(got_keys - expected_keys)
    if missing:
        errors.append(f"ERROR: thresholds missing_keys={','.join(missing)}")
    if extra:
        errors.append(f"ERROR: thresholds extra_keys={','.join(extra)}")

    for key in sorted(expected_keys & got_keys):
        exp = float(expected[key])
        actual = float(got[key])
        if abs(exp - actual) > tol:
            errors.append(
                f"ERROR: thresholds mismatch key={key} expected={exp:.6f} got={actual:.6f}"
            )
    return errors


def validate_sample(
    sample: dict[str, Any],
    thresholds: dict[str, float],
) -> list[str]:
    sample_id = sample["id"]
    errors: list[str] = []

    def gt_max(key: str, threshold_key: str) -> None:
        value = float(sample[key])
        threshold = float(thresholds[threshold_key])
        if value > threshold:
            errors.append(f"ERROR: {sample_id} {key}={value:.3f} > {threshold:.3f}")

    def lt_min(key: str, threshold_key: str) -> None:
        value = float(sample[key])
        threshold = float(thresholds[threshold_key])
        if value < threshold:
            errors.append(f"ERROR: {sample_id} {key}={value:.3f} < {threshold:.3f}")

    gt_max("lipsync_mae", "lipsync_mae_max")
    gt_max("mouth_breakage_rate", "mouth_breakage_rate_max")
    gt_max("temporal_jump", "temporal_jump_max")
    lt_min("psnr", "psnr_min")
    lt_min("ssim", "ssim_min")
    return errors


def validate_aggregate(
    aggregate: dict[str, Any],
    thresholds: dict[str, float],
) -> list[str]:
    errors: list[str] = []

    def gt_max(key: str, threshold_key: str) -> None:
        value = float(aggregate[key])
        threshold = float(thresholds[threshold_key])
        if value > threshold:
            errors.append(f"ERROR: aggregate {key}={value:.3f} > {threshold:.3f}")

    def lt_min(key: str, threshold_key: str) -> None:
        value = float(aggregate[key])
        threshold = float(thresholds[threshold_key])
        if value < threshold:
            errors.append(f"ERROR: aggregate {key}={value:.3f} < {threshold:.3f}")

    gt_max("oom_rate", "oom_rate_max")
    gt_max("failure_rate", "failure_rate_max")
    lt_min("throughput_fps", "throughput_fps_min")
    return errors


def summarize(samples: list[dict[str, Any]]) -> dict[str, float]:
    return {
        "lipsync_mae_mean": mean(float(item["lipsync_mae"]) for item in samples),
        "mouth_breakage_rate_mean": mean(
            float(item["mouth_breakage_rate"]) for item in samples
        ),
        "temporal_jump_mean": mean(float(item["temporal_jump"]) for item in samples),
        "psnr_mean": mean(float(item["psnr"]) for item in samples),
        "ssim_mean": mean(float(item["ssim"]) for item in samples),
    }


def run(mode: str, file_path: Path, thresholds_file: Path) -> int:
    payload = load_payload(file_path)
    thresholds = load_thresholds(thresholds_file)
    errors: list[str] = []

    payload_thresholds = payload.get("thresholds")
    if payload_thresholds is not None:
        errors.extend(compare_thresholds(thresholds, payload_thresholds))

    samples = payload["samples"]
    aggregate = payload["aggregate"]

    for sample in samples:
        errors.extend(validate_sample(sample, thresholds))
    errors.extend(validate_aggregate(aggregate, thresholds))

    if errors:
        print(f"ERROR: mode={mode} failed failures={len(errors)} samples={len(samples)}")
        for line in errors:
            print(line)
        return 1

    summary = summarize(samples)
    print(f"METRIC: mode={mode} passed samples={len(samples)} failures=0")
    for key, value in summary.items():
        print(f"METRIC: {key}={value:.4f}")
    print(
        "METRIC: aggregate "
        f"oom_rate={float(aggregate['oom_rate']):.4f} "
        f"failure_rate={float(aggregate['failure_rate']):.4f} "
        f"throughput_fps={float(aggregate['throughput_fps']):.2f}"
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run deterministic quality checks.")
    parser.add_argument("--mode", choices=["fast", "full"], required=True)
    parser.add_argument("--file", default=None)
    parser.add_argument("--thresholds-file", default=str(DEFAULT_THRESHOLDS_FILE))
    return parser


def main() -> int:
    args = build_parser().parse_args()
    file_path = Path(args.file) if args.file else DEFAULT_FILE_BY_MODE[args.mode]
    thresholds_file = Path(args.thresholds_file)
    return run(mode=args.mode, file_path=file_path, thresholds_file=thresholds_file)


if __name__ == "__main__":
    raise SystemExit(main())
