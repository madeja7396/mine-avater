from __future__ import annotations

import argparse
from pathlib import Path

if __package__ in (None, ""):
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.config import GeneratorConfig, PostprocessConfig, PreprocessConfig, ScaffoldConfig
from pipeline.scaffold import run_scaffold_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run scaffold avatar pipeline.")
    parser.add_argument("--input-audio", required=True)
    parser.add_argument("--reference-image", required=True)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--window-ms", type=float, default=25.0)
    parser.add_argument("--hop-ms", type=float, default=10.0)
    parser.add_argument("--frame-count", type=int, default=12)
    parser.add_argument("--fps", type=int, default=25)
    parser.add_argument(
        "--generator-backend",
        choices=["heuristic", "vit-mock", "vit-hf", "vit-auto"],
        default="heuristic",
    )
    parser.add_argument("--vit-patch-size", type=int, default=16)
    parser.add_argument("--vit-image-size", type=int, default=224)
    parser.add_argument("--no-vit-fallback-mock", action="store_true")
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

    if args.frame_count <= 0:
        print(f"ERROR: invalid_frame_count value={args.frame_count}")
        return 1
    if args.fps <= 0:
        print(f"ERROR: invalid_fps value={args.fps}")
        return 1
    if args.window_ms <= 0.0 or args.hop_ms <= 0.0:
        print(
            "ERROR: invalid_window_or_hop "
            f"window_ms={args.window_ms} hop_ms={args.hop_ms}"
        )
        return 1
    if args.vit_patch_size <= 0 or args.vit_image_size <= 0:
        print(
            "ERROR: invalid_vit_size "
            f"vit_patch_size={args.vit_patch_size} vit_image_size={args.vit_image_size}"
        )
        return 1
    if (
        args.generator_backend in ("vit-hf", "vit-auto")
        and args.vit_image_size % args.vit_patch_size != 0
    ):
        print(
            "ERROR: invalid_vit_grid "
            f"vit_image_size={args.vit_image_size} vit_patch_size={args.vit_patch_size}"
        )
        return 1

    config = ScaffoldConfig(
        preprocess=PreprocessConfig(
            window_ms=args.window_ms,
            hop_ms=args.hop_ms,
            landmark_frames=args.frame_count,
        ),
        generator=GeneratorConfig(
            frame_count=args.frame_count,
            backend=args.generator_backend,
            vit_patch_size=args.vit_patch_size,
            vit_image_size=args.vit_image_size,
            vit_fallback_mock=not args.no_vit_fallback_mock,
        ),
        postprocess=PostprocessConfig(fps=args.fps),
    )

    output = run_scaffold_pipeline(
        input_audio=input_audio,
        reference_image=reference_image,
        workspace=workspace,
        config=config,
    )
    print(f"METRIC: scaffold_pipeline_completed output={output.output_video}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
