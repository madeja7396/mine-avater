#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


DEFAULT_THRESHOLDS = Path("specs/quality_thresholds.json")
DEFAULT_EVAL_FILES = [
    Path("eval/fast/samples.json"),
    Path("eval/full/samples.json"),
]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync eval thresholds from specs.")
    parser.add_argument("--thresholds", default=str(DEFAULT_THRESHOLDS))
    parser.add_argument("--eval-file", action="append", default=[])
    args = parser.parse_args()

    thresholds_path = Path(args.thresholds)
    eval_files = [Path(p) for p in args.eval_file] if args.eval_file else DEFAULT_EVAL_FILES

    thresholds = load_json(thresholds_path)
    updated = 0
    for file_path in eval_files:
        payload = load_json(file_path)
        if payload.get("thresholds") == thresholds:
            continue
        payload["thresholds"] = thresholds
        write_json(file_path, payload)
        updated += 1
        print(f"METRIC: thresholds_synced file={file_path}")

    print(f"METRIC: sync_thresholds_completed updated={updated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

