from __future__ import annotations

import argparse
from pathlib import Path

if __package__ in (None, ""):
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.scaffold import run_scaffold_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run scaffold avatar pipeline.")
    parser.add_argument("--input-audio", required=True)
    parser.add_argument("--reference-image", required=True)
    parser.add_argument("--workspace", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    input_audio = Path(args.input_audio)
    reference_image = Path(args.reference_image)
    workspace = Path(args.workspace)

    if not input_audio.is_file():
        print(f"ERROR: input_audio_not_found path={input_audio}")
        return 1
    if not reference_image.is_file():
        print(f"ERROR: reference_image_not_found path={reference_image}")
        return 1

    output = run_scaffold_pipeline(
        input_audio=input_audio,
        reference_image=reference_image,
        workspace=workspace,
    )
    print(f"METRIC: scaffold_pipeline_completed output={output.output_video}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
