from __future__ import annotations

import math
import struct
from dataclasses import dataclass
from pathlib import Path


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


def _bytes_to_unit_values(raw: bytes, count: int) -> list[float]:
    if not raw:
        return [0.0] * count
    values: list[float] = []
    idx = 0
    while len(values) < count:
        values.append(raw[idx % len(raw)] / 255.0)
        idx += 1
    return values


def compute_mock_vit_conditioning(
    reference_image: Path,
    width: int,
    height: int,
    patch_size: int,
) -> VitResult:
    raw = reference_image.read_bytes()
    unit = _bytes_to_unit_values(raw, 2048)
    token_count = max(1, (max(width, patch_size) // patch_size) * (max(height, patch_size) // patch_size))
    chunk = max(1, len(unit) // token_count)

    patch_means: list[float] = []
    for i in range(token_count):
        s = i * chunk
        e = min(len(unit), s + chunk)
        frame = unit[s:e] if s < len(unit) else unit[-chunk:]
        patch_means.append(sum(frame) / max(1, len(frame)))

    mean_all = sum(patch_means) / len(patch_means)
    var_all = sum((v - mean_all) ** 2 for v in patch_means) / len(patch_means)
    spread = math.sqrt(var_all)

    conditioning = VitConditioning(
        face_shift_x=(mean_all - 0.5) * 0.08,
        face_shift_y=(spread - 0.25) * 0.10,
        mouth_gain=1.0 + (spread - 0.25) * 0.6,
        tone_shift=(sum(unit[:64]) / 64.0 - 0.5) * 0.30,
    )
    return VitResult(
        conditioning=conditioning,
        backend_used="vit-mock",
        details={
            "token_count": float(token_count),
            "mean_all": mean_all,
            "spread": spread,
        },
    )


def _build_tensor_from_bytes(raw: bytes, image_size: int) -> list[float]:
    count = 3 * image_size * image_size
    unit = _bytes_to_unit_values(raw, count)
    return [v * 2.0 - 1.0 for v in unit]


def compute_hf_vit_conditioning(
    reference_image: Path,
    image_size: int,
    patch_size: int,
) -> VitResult:
    try:
        import torch
        from transformers import ViTConfig, ViTModel
    except Exception as exc:  # pragma: no cover - optional dependency path
        raise RuntimeError(f"transformers/torch unavailable: {exc}") from exc

    if patch_size <= 0 or image_size <= 0:
        raise RuntimeError("invalid vit image or patch size")
    if image_size % patch_size != 0:
        raise RuntimeError("vit image_size must be divisible by patch_size")

    raw = reference_image.read_bytes()
    data = _build_tensor_from_bytes(raw, image_size=image_size)
    pixel_values = torch.tensor(data, dtype=torch.float32).reshape(1, 3, image_size, image_size)

    config = ViTConfig(
        image_size=image_size,
        patch_size=patch_size,
        num_hidden_layers=2,
        hidden_size=192,
        intermediate_size=768,
        num_attention_heads=3,
    )
    model = ViTModel(config)
    model.eval()
    with torch.no_grad():
        output = model(pixel_values=pixel_values).last_hidden_state
        pooled = output.mean(dim=1).squeeze(0)
        mean_value = float(pooled.mean().item())
        std_value = float(pooled.std().item())

    conditioning = VitConditioning(
        face_shift_x=_clamp(mean_value * 0.12, -0.1, 0.1),
        face_shift_y=_clamp((std_value - 0.5) * 0.10, -0.1, 0.1),
        mouth_gain=_clamp(1.0 + (std_value - 0.5) * 0.8, 0.6, 1.6),
        tone_shift=_clamp(mean_value * 0.35, -0.4, 0.4),
    )
    return VitResult(
        conditioning=conditioning,
        backend_used="vit-hf",
        details={"mean_value": mean_value, "std_value": std_value},
    )


def resolve_vit_conditioning(
    reference_image: Path,
    width: int,
    height: int,
    backend: str,
    patch_size: int,
    image_size: int,
    fallback_mock: bool,
) -> VitResult:
    if backend == "heuristic":
        return VitResult(
            conditioning=VitConditioning(0.0, 0.0, 1.0, 0.0),
            backend_used="heuristic",
            details={"message": "heuristic mode"},
        )

    if backend == "vit-mock":
        return compute_mock_vit_conditioning(reference_image, width, height, patch_size)

    if backend in ("vit-hf", "vit-auto"):
        try:
            return compute_hf_vit_conditioning(reference_image, image_size=image_size, patch_size=patch_size)
        except Exception as exc:
            if backend == "vit-hf" and not fallback_mock:
                raise
            mock = compute_mock_vit_conditioning(reference_image, width, height, patch_size)
            return VitResult(
                conditioning=mock.conditioning,
                backend_used="vit-mock-fallback",
                details={"reason": str(exc), **mock.details},
            )

    raise ValueError(f"Unknown generator backend: {backend}")

