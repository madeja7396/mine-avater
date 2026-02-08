from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from pathlib import Path

from pipeline.image_io import load_rgb_image


@dataclass(frozen=True)
class VitConditioning:
    face_shift_x: float
    face_shift_y: float
    mouth_gain: float
    tone_shift: float


@dataclass(frozen=True)
class VitResult:
    conditioning: VitConditioning
    backend_used: str
    details: dict[str, float | str]


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _rgb_to_unit_values(raw_rgb: bytes) -> list[float]:
    if not raw_rgb:
        return []
    return [v / 255.0 for v in raw_rgb]


def _collect_reference_images(
    reference_image: Path,
    reference_images: list[Path] | None,
) -> list[Path]:
    paths = [reference_image]
    for p in reference_images or []:
        if p not in paths:
            paths.append(p)
    return paths


def _merge_conditionings(
    rows: list[VitConditioning],
) -> VitConditioning:
    if not rows:
        return VitConditioning(face_shift_x=0.0, face_shift_y=0.0, mouth_gain=1.0, tone_shift=0.0)
    n = float(len(rows))
    return VitConditioning(
        face_shift_x=sum(v.face_shift_x for v in rows) / n,
        face_shift_y=sum(v.face_shift_y for v in rows) / n,
        mouth_gain=sum(v.mouth_gain for v in rows) / n,
        tone_shift=sum(v.tone_shift for v in rows) / n,
    )


def _stable_noise_unit(key: str) -> float:
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    raw = int.from_bytes(digest[:8], "big")
    unit = raw / float((1 << 64) - 1)
    return (unit * 2.0) - 1.0


def _apply_reference_augmentation(
    conditioning: VitConditioning,
    seed_key: str,
    augmentation_copies: int,
    augmentation_strength: float,
    reference_count: int,
) -> tuple[VitConditioning, int]:
    copies = max(1, augmentation_copies)
    reference_rows = max(1, reference_count)
    total_rows = max(1, reference_rows * copies)
    strength = _clamp(augmentation_strength, 0.0, 1.0)
    if total_rows <= 1 or strength <= 0.0:
        return conditioning, 1

    rows: list[VitConditioning] = [conditioning]
    for idx in range(1, total_rows):
        n_x = _stable_noise_unit(f"{seed_key}:x:{idx}")
        n_y = _stable_noise_unit(f"{seed_key}:y:{idx}")
        n_m = _stable_noise_unit(f"{seed_key}:m:{idx}")
        n_t = _stable_noise_unit(f"{seed_key}:t:{idx}")
        rows.append(
            VitConditioning(
                face_shift_x=_clamp(conditioning.face_shift_x + n_x * 0.030 * strength, -0.2, 0.2),
                face_shift_y=_clamp(conditioning.face_shift_y + n_y * 0.030 * strength, -0.2, 0.2),
                mouth_gain=_clamp(conditioning.mouth_gain * (1.0 + n_m * 0.18 * strength), 0.5, 1.9),
                tone_shift=_clamp(conditioning.tone_shift + n_t * 0.080 * strength, -0.6, 0.6),
            )
        )
    return _merge_conditionings(rows), len(rows)


def _apply_overfit_guard(conditioning: VitConditioning, guard_strength: float) -> VitConditioning:
    g = _clamp(guard_strength, 0.0, 1.0)
    if g <= 0.0:
        return conditioning
    keep = 1.0 - g
    return VitConditioning(
        face_shift_x=conditioning.face_shift_x * keep,
        face_shift_y=conditioning.face_shift_y * keep,
        mouth_gain=1.0 + ((conditioning.mouth_gain - 1.0) * keep),
        tone_shift=conditioning.tone_shift * keep,
    )


def _mock_single_conditioning(
    image_path: Path,
    width: int,
    height: int,
    patch_size: int,
) -> tuple[VitConditioning, dict[str, float]]:
    patch_size = max(1, patch_size)
    rgb = load_rgb_image(image_path, width=width, height=height)
    unit = _rgb_to_unit_values(rgb)
    if not unit:
        unit = [0.0]

    patch_cols = max(1, width // patch_size)
    patch_rows = max(1, height // patch_size)
    patch_means: list[float] = []
    for py in range(patch_rows):
        for px in range(patch_cols):
            sx = px * patch_size
            sy = py * patch_size
            ex = min(width, sx + patch_size)
            ey = min(height, sy + patch_size)
            values = []
            for y in range(sy, ey):
                for x in range(sx, ex):
                    idx = (y * width + x) * 3
                    r = unit[idx]
                    g = unit[idx + 1]
                    b = unit[idx + 2]
                    values.append((0.299 * r) + (0.587 * g) + (0.114 * b))
            patch_means.append(sum(values) / max(1, len(values)))

    mean_all = sum(patch_means) / max(1, len(patch_means))
    var_all = sum((v - mean_all) ** 2 for v in patch_means) / max(1, len(patch_means))
    spread = math.sqrt(var_all)
    conditioning = VitConditioning(
        face_shift_x=(mean_all - 0.5) * 0.08,
        face_shift_y=(spread - 0.25) * 0.10,
        mouth_gain=1.0 + (spread - 0.25) * 0.6,
        tone_shift=(sum(unit[:64]) / max(1.0, min(64.0, float(len(unit))))) - 0.5,
    )
    return conditioning, {"token_count": float(len(patch_means)), "mean_all": mean_all, "spread": spread}


def compute_mock_vit_conditioning(
    reference_image: Path,
    width: int,
    height: int,
    patch_size: int,
    reference_images: list[Path] | None = None,
) -> VitResult:
    images = _collect_reference_images(reference_image, reference_images)
    rows: list[VitConditioning] = []
    meta_rows: list[dict[str, float]] = []
    for image_path in images:
        cond, meta = _mock_single_conditioning(
            image_path=image_path,
            width=width,
            height=height,
            patch_size=patch_size,
        )
        rows.append(cond)
        meta_rows.append(meta)
    conditioning = _merge_conditionings(rows)
    token_count = sum(v["token_count"] for v in meta_rows) / max(1.0, float(len(meta_rows)))
    mean_all = sum(v["mean_all"] for v in meta_rows) / max(1.0, float(len(meta_rows)))
    spread = sum(v["spread"] for v in meta_rows) / max(1.0, float(len(meta_rows)))
    return VitResult(
        conditioning=conditioning,
        backend_used="vit-mock",
        details={
            "token_count": token_count,
            "mean_all": mean_all,
            "spread": spread,
            "reference_count": float(len(images)),
        },
    )


def _build_tensor_from_rgb(raw_rgb: bytes) -> list[float]:
    unit = _rgb_to_unit_values(raw_rgb)
    return [(v - 0.5) / 0.5 for v in unit]


def compute_hf_vit_conditioning(
    reference_image: Path,
    image_size: int,
    patch_size: int,
    model_name: str,
    use_pretrained: bool,
    device: str,
    reference_images: list[Path] | None = None,
) -> VitResult:
    try:
        import torch
        from transformers import ViTConfig, ViTModel
    except Exception as exc:  # pragma: no cover - optional dependency path
        raise RuntimeError(f"transformers/torch unavailable: {exc}") from exc

    if patch_size <= 0 or image_size <= 0:
        raise RuntimeError("invalid vit image or patch size")

    run_device = device
    if device.startswith("cuda") and not torch.cuda.is_available():
        run_device = "cpu"

    if use_pretrained:
        model = ViTModel.from_pretrained(model_name)
        image_size = int(getattr(model.config, "image_size", image_size))
        patch_size = int(getattr(model.config, "patch_size", patch_size))
    else:
        if image_size % patch_size != 0:
            raise RuntimeError("vit image_size must be divisible by patch_size")
        config = ViTConfig(
            image_size=image_size,
            patch_size=patch_size,
            num_hidden_layers=2,
            hidden_size=192,
            intermediate_size=768,
            num_attention_heads=3,
        )
        model = ViTModel(config)

    images = _collect_reference_images(reference_image, reference_images)
    tensors: list[list[float]] = []
    for image_path in images:
        rgb = load_rgb_image(image_path, width=image_size, height=image_size)
        tensors.append(_build_tensor_from_rgb(rgb))
    pixel_values = torch.tensor(tensors, dtype=torch.float32).reshape(len(tensors), 3, image_size, image_size)

    model.eval()
    model.to(run_device)
    pixel_values = pixel_values.to(run_device)
    with torch.no_grad():
        output = model(pixel_values=pixel_values).last_hidden_state
        pooled_batch = output.mean(dim=1)
        cls_batch = output[:, 0, :]
        mean_value = float(pooled_batch.mean().item())
        std_value = float(pooled_batch.std().item())
        cls_mean = float(cls_batch.mean().item())

    conditioning = VitConditioning(
        face_shift_x=_clamp(cls_mean * 0.12, -0.1, 0.1),
        face_shift_y=_clamp((std_value - 0.5) * 0.10, -0.1, 0.1),
        mouth_gain=_clamp(1.0 + (std_value - 0.5) * 0.8, 0.6, 1.6),
        tone_shift=_clamp(mean_value * 0.35 + cls_mean * 0.15, -0.4, 0.4),
    )
    return VitResult(
        conditioning=conditioning,
        backend_used="vit-hf",
        details={
            "mean_value": mean_value,
            "std_value": std_value,
            "cls_mean": cls_mean,
            "image_size": float(image_size),
            "patch_size": float(patch_size),
            "pretrained": "true" if use_pretrained else "false",
            "device": run_device,
            "reference_count": float(len(images)),
        },
    )


def resolve_vit_conditioning(
    reference_image: Path,
    width: int,
    height: int,
    backend: str,
    patch_size: int,
    image_size: int,
    fallback_mock: bool,
    model_name: str,
    use_pretrained: bool,
    device: str,
    reference_images: list[Path] | None = None,
    spatial_params: dict[str, float] | None = None,
    spatial_weight: float = 0.0,
    enable_reference_augmentation: bool = False,
    augmentation_copies: int = 1,
    augmentation_strength: float = 0.15,
    overfit_guard_strength: float = 0.0,
) -> VitResult:
    def with_spatial(base: VitResult) -> VitResult:
        if not spatial_params:
            return VitResult(
                conditioning=base.conditioning,
                backend_used=base.backend_used,
                details={**base.details, "spatial_3d_applied": "false"},
            )

        weight = _clamp(spatial_weight, 0.0, 1.0)
        yaw = _clamp(float(spatial_params.get("yaw", 0.0)), -1.0, 1.0)
        pitch = _clamp(float(spatial_params.get("pitch", 0.0)), -1.0, 1.0)
        depth = _clamp(float(spatial_params.get("depth", 0.0)), -1.0, 1.0)

        cond = base.conditioning
        conditioned = VitConditioning(
            face_shift_x=_clamp(cond.face_shift_x + (yaw * 0.06 * weight), -0.15, 0.15),
            face_shift_y=_clamp(cond.face_shift_y + (pitch * 0.06 * weight), -0.15, 0.15),
            mouth_gain=_clamp(cond.mouth_gain * (1.0 + depth * 0.25 * weight), 0.5, 1.8),
            tone_shift=_clamp(cond.tone_shift + (depth * 0.10 * weight), -0.5, 0.5),
        )
        return VitResult(
            conditioning=conditioned,
            backend_used=base.backend_used,
            details={
                **base.details,
                "spatial_3d_applied": "true",
                "spatial_3d_weight": weight,
                "spatial_3d_yaw": yaw,
                "spatial_3d_pitch": pitch,
                "spatial_3d_depth": depth,
            },
        )

    def with_phase4(base: VitResult) -> VitResult:
        details = dict(base.details)
        cond = base.conditioning

        ref_count_raw = details.get("reference_count", 1.0)
        ref_count = int(ref_count_raw) if isinstance(ref_count_raw, (int, float)) else 1
        if enable_reference_augmentation:
            augmented, virtual_rows = _apply_reference_augmentation(
                conditioning=cond,
                seed_key=str(reference_image),
                augmentation_copies=augmentation_copies,
                augmentation_strength=augmentation_strength,
                reference_count=ref_count,
            )
            cond = augmented
            details["phase4_aug_applied"] = "true"
            details["phase4_aug_virtual_rows"] = float(virtual_rows)
            details["phase4_aug_copies"] = float(max(1, augmentation_copies))
            details["phase4_aug_strength"] = _clamp(augmentation_strength, 0.0, 1.0)
        else:
            details["phase4_aug_applied"] = "false"

        cond = _apply_overfit_guard(cond, overfit_guard_strength)
        details["phase4_overfit_guard_strength"] = _clamp(overfit_guard_strength, 0.0, 1.0)

        return VitResult(
            conditioning=cond,
            backend_used=base.backend_used,
            details=details,
        )

    if backend == "heuristic":
        return with_phase4(
            with_spatial(
                VitResult(
                    conditioning=VitConditioning(0.0, 0.0, 1.0, 0.0),
                    backend_used="heuristic",
                    details={"message": "heuristic mode"},
                )
            )
        )

    if backend == "vit-mock":
        return with_phase4(
            with_spatial(
                compute_mock_vit_conditioning(
                    reference_image=reference_image,
                    width=width,
                    height=height,
                    patch_size=patch_size,
                    reference_images=reference_images,
                )
            )
        )

    if backend in ("vit-hf", "vit-auto"):
        try:
            return with_phase4(
                with_spatial(
                    compute_hf_vit_conditioning(
                        reference_image,
                        image_size=image_size,
                        patch_size=patch_size,
                        model_name=model_name,
                        use_pretrained=use_pretrained,
                        device=device,
                        reference_images=reference_images,
                    )
                )
            )
        except Exception as exc:
            if backend == "vit-hf" and not fallback_mock:
                raise
            mock = compute_mock_vit_conditioning(
                reference_image=reference_image,
                width=width,
                height=height,
                patch_size=patch_size,
                reference_images=reference_images,
            )
            return with_phase4(
                with_spatial(
                    VitResult(
                        conditioning=mock.conditioning,
                        backend_used="vit-mock-fallback",
                        details={"reason": str(exc), **mock.details},
                    )
                )
            )

    raise ValueError(f"Unknown generator backend: {backend}")
