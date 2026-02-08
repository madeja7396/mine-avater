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
    parser.add_argument("--disable-watermark", action="store_true")
    parser.add_argument("--watermark-label", default="MINE-AVATER/RESEARCH-ONLY")
    parser.add_argument(
        "--generator-backend",
        choices=["heuristic", "vit-mock", "vit-hf", "vit-auto"],
        default="heuristic",
    )
    parser.add_argument("--vit-patch-size", type=int, default=16)
    parser.add_argument("--vit-image-size", type=int, default=224)
    parser.add_argument("--vit-reference-dir", default=None)
    parser.add_argument("--vit-reference-limit", type=int, default=8)
    parser.add_argument("--no-vit-fallback-mock", action="store_true")
    parser.add_argument("--vit-model-name", default="google/vit-base-patch16-224")
    parser.add_argument("--vit-use-pretrained", action="store_true")
    parser.add_argument("--vit-device", default="cpu")
    parser.add_argument("--vit-enable-3d-conditioning", action="store_true")
    parser.add_argument("--vit-3d-conditioning-weight", type=float, default=0.35)
    parser.add_argument("--vit-enable-reference-augmentation", action="store_true")
    parser.add_argument("--vit-augmentation-copies", type=int, default=1)
    parser.add_argument("--vit-augmentation-strength", type=float, default=0.15)
    parser.add_argument("--vit-overfit-guard-strength", type=float, default=0.0)
    parser.add_argument("--temporal-spatial-loss-weight", type=float, default=0.0)
    parser.add_argument("--temporal-smooth-factor", type=float, default=0.35)
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
    if not args.watermark_label.strip():
        print("ERROR: invalid_watermark_label empty")
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
    if args.vit_reference_limit <= 0:
        print(f"ERROR: invalid_vit_reference_limit value={args.vit_reference_limit}")
        return 1
    if args.vit_3d_conditioning_weight < 0.0 or args.vit_3d_conditioning_weight > 1.0:
        print(
            "ERROR: invalid_vit_3d_conditioning_weight "
            f"value={args.vit_3d_conditioning_weight}"
        )
        return 1
    if args.vit_augmentation_copies <= 0:
        print(f"ERROR: invalid_vit_augmentation_copies value={args.vit_augmentation_copies}")
        return 1
    if args.vit_augmentation_strength < 0.0 or args.vit_augmentation_strength > 1.0:
        print(
            "ERROR: invalid_vit_augmentation_strength "
            f"value={args.vit_augmentation_strength}"
        )
        return 1
    if args.vit_overfit_guard_strength < 0.0 or args.vit_overfit_guard_strength > 1.0:
        print(
            "ERROR: invalid_vit_overfit_guard_strength "
            f"value={args.vit_overfit_guard_strength}"
        )
        return 1
    if args.temporal_spatial_loss_weight < 0.0 or args.temporal_spatial_loss_weight > 1.0:
        print(
            "ERROR: invalid_temporal_spatial_loss_weight "
            f"value={args.temporal_spatial_loss_weight}"
        )
        return 1
    if args.temporal_smooth_factor < 0.0 or args.temporal_smooth_factor > 1.0:
        print(f"ERROR: invalid_temporal_smooth_factor value={args.temporal_smooth_factor}")
        return 1
    if args.vit_reference_dir is not None and not Path(args.vit_reference_dir).is_dir():
        print(f"ERROR: vit_reference_dir_not_found path={args.vit_reference_dir}")
        return 1
    if (
        args.generator_backend in ("vit-hf", "vit-auto")
        and args.vit_image_size % args.vit_patch_size != 0
        and not args.vit_use_pretrained
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
            vit_reference_dir=args.vit_reference_dir,
            vit_reference_limit=args.vit_reference_limit,
            vit_patch_size=args.vit_patch_size,
            vit_image_size=args.vit_image_size,
            vit_fallback_mock=not args.no_vit_fallback_mock,
            vit_model_name=args.vit_model_name,
            vit_use_pretrained=args.vit_use_pretrained,
            vit_device=args.vit_device,
            vit_enable_3d_conditioning=args.vit_enable_3d_conditioning,
            vit_3d_conditioning_weight=args.vit_3d_conditioning_weight,
            vit_enable_reference_augmentation=args.vit_enable_reference_augmentation,
            vit_augmentation_copies=args.vit_augmentation_copies,
            vit_augmentation_strength=args.vit_augmentation_strength,
            vit_overfit_guard_strength=args.vit_overfit_guard_strength,
            temporal_spatial_loss_weight=args.temporal_spatial_loss_weight,
            temporal_smooth_factor=args.temporal_smooth_factor,
        ),
        postprocess=PostprocessConfig(
            fps=args.fps,
            watermark_enabled=not args.disable_watermark,
            watermark_label=args.watermark_label.strip(),
        ),
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
