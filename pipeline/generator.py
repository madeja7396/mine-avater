from __future__ import annotations

import json
import re
import struct
import zlib
from pathlib import Path

from pipeline.preprocess import get_image_size
from pipeline.vit import VitConditioning, resolve_vit_conditioning


def read_npy_f32_matrix(path: Path) -> list[list[float]]:
    raw = path.read_bytes()
    if not raw.startswith(b"\x93NUMPY"):
        raise ValueError(f"Invalid NPY header: {path}")

    major = raw[6]
    minor = raw[7]
    if (major, minor) != (1, 0):
        raise ValueError(f"Unsupported NPY version: {(major, minor)}")

    header_len = int.from_bytes(raw[8:10], "little")
    header = raw[10 : 10 + header_len].decode("latin1")
    shape_match = re.search(r"'shape': \((\d+), (\d+)\)", header)
    if not shape_match:
        raise ValueError(f"NPY shape missing: {path}")
    rows = int(shape_match.group(1))
    cols = int(shape_match.group(2))

    offset = 10 + header_len
    count = rows * cols
    if count == 0:
        return []
    values = struct.unpack("<" + ("f" * count), raw[offset : offset + (4 * count)])
    matrix: list[list[float]] = []
    for i in range(rows):
        matrix.append(list(values[i * cols : (i + 1) * cols]))
    return matrix


def load_mouth_landmarks(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"Invalid landmarks payload: {path}")
    return payload


def _chunk(kind: bytes, payload: bytes) -> bytes:
    return (
        struct.pack(">I", len(payload))
        + kind
        + payload
        + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
    )


def write_png_rgb(path: Path, width: int, height: int, pixels: bytes) -> None:
    if len(pixels) != width * height * 3:
        raise ValueError("Invalid RGB payload length")

    scanlines = bytearray()
    stride = width * 3
    for y in range(height):
        scanlines.append(0)  # filter: none
        start = y * stride
        scanlines.extend(pixels[start : start + stride])

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    idat = zlib.compress(bytes(scanlines), level=6)
    png = b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", idat) + _chunk(b"IEND", b"")
    path.write_bytes(png)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _render_frame(
    width: int,
    height: int,
    mouth_cx: float,
    mouth_cy: float,
    mouth_open: float,
    energy: float,
    vit: VitConditioning,
) -> bytes:
    pixels = bytearray(width * height * 3)
    skin_r, skin_g, skin_b = 220, 186, 160

    # Slightly animate background brightness using audio energy.
    bg_boost = int(25.0 * _clamp(energy, 0.0, 1.0) + 30.0 * vit.tone_shift)
    for y in range(height):
        for x in range(width):
            idx = (y * width + x) * 3
            pixels[idx] = int(_clamp(40 + bg_boost + (x * 30 // max(1, width - 1)), 0, 255))
            pixels[idx + 1] = int(_clamp(55 + (y * 20 // max(1, height - 1)), 0, 255))
            pixels[idx + 2] = 75

    face_cx = int(width * (0.5 + vit.face_shift_x))
    face_cy = int(height * (0.5 + vit.face_shift_y))
    face_rx = int(width * 0.32)
    face_ry = int(height * 0.40)

    for y in range(height):
        dy = (y - face_cy) / max(1.0, float(face_ry))
        for x in range(width):
            dx = (x - face_cx) / max(1.0, float(face_rx))
            if dx * dx + dy * dy <= 1.0:
                idx = (y * width + x) * 3
                pixels[idx] = int(_clamp(skin_r + vit.tone_shift * 25.0, 0, 255))
                pixels[idx + 1] = int(_clamp(skin_g + vit.tone_shift * 15.0, 0, 255))
                pixels[idx + 2] = int(_clamp(skin_b + vit.tone_shift * 8.0, 0, 255))

    mx = int(_clamp(mouth_cx, 0.2, 0.8) * width)
    my = int(_clamp(mouth_cy, 0.2, 0.9) * height)
    mr_x = max(3, int(width * 0.10))
    mr_y = max(2, int(height * (0.015 + 0.20 * _clamp(mouth_open, 0.0, 1.0))))

    for y in range(max(0, my - mr_y * 2), min(height, my + mr_y * 2)):
        for x in range(max(0, mx - mr_x * 2), min(width, mx + mr_x * 2)):
            dx = (x - mx) / max(1.0, float(mr_x))
            dy = (y - my) / max(1.0, float(mr_y))
            if dx * dx + dy * dy <= 1.0:
                idx = (y * width + x) * 3
                pixels[idx] = 110
                pixels[idx + 1] = 25
                pixels[idx + 2] = 35

    return bytes(pixels)


def generate_frames(
    reference_image: Path,
    audio_features: Path,
    mouth_landmarks: Path,
    output_dir: Path,
    frame_count: int = 12,
) -> int:
    result = generate_frames_with_backend(
        reference_image=reference_image,
        audio_features=audio_features,
        mouth_landmarks=mouth_landmarks,
        output_dir=output_dir,
        frame_count=frame_count,
    )
    return int(result["frame_count"])


def generate_frames_with_backend(
    reference_image: Path,
    audio_features: Path,
    mouth_landmarks: Path,
    output_dir: Path,
    frame_count: int = 12,
    backend: str = "heuristic",
    vit_patch_size: int = 16,
    vit_image_size: int = 224,
    vit_fallback_mock: bool = True,
    vit_model_name: str = "google/vit-base-patch16-224",
    vit_use_pretrained: bool = False,
    vit_device: str = "cpu",
) -> dict[str, object]:
    width, height = get_image_size(reference_image)
    width = max(64, min(width, 256))
    height = max(64, min(height, 256))

    features = read_npy_f32_matrix(audio_features)
    landmarks = load_mouth_landmarks(mouth_landmarks)

    if not features:
        features = [[0.0, 0.0, 0.0]]
    if not landmarks:
        landmarks = [{"frame_index": 0, "points": [[0.4, 0.6], [0.46, 0.62], [0.54, 0.62], [0.6, 0.6]]}]

    vit_result = resolve_vit_conditioning(
        reference_image=reference_image,
        width=width,
        height=height,
        backend=backend,
        patch_size=vit_patch_size,
        image_size=vit_image_size,
        fallback_mock=vit_fallback_mock,
        model_name=vit_model_name,
        use_pretrained=vit_use_pretrained,
        device=vit_device,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    for i in range(frame_count):
        feat = features[i % len(features)]
        rms = float(feat[0]) if len(feat) > 0 else 0.0
        energy = _clamp(rms * 3.5, 0.0, 1.0)

        lm = landmarks[i % len(landmarks)]
        points = lm.get("points", [])
        if len(points) < 4:
            points = [[0.4, 0.6], [0.46, 0.62], [0.54, 0.62], [0.6, 0.6]]

        mouth_cx = float(points[1][0] + points[2][0]) * 0.5
        mouth_cy = float(points[1][1] + points[2][1]) * 0.5
        mouth_open = (
            abs(float(points[1][1]) - float(points[0][1]))
            + energy * 0.15 * vit_result.conditioning.mouth_gain
        )

        frame = _render_frame(
            width,
            height,
            mouth_cx,
            mouth_cy,
            mouth_open,
            energy,
            vit=vit_result.conditioning,
        )
        write_png_rgb(output_dir / f"{i:06d}.png", width, height, frame)

    return {
        "frame_count": frame_count,
        "backend_requested": backend,
        "backend_used": vit_result.backend_used,
        "vit_details": vit_result.details,
        "vit_model_name": vit_model_name,
        "vit_use_pretrained": vit_use_pretrained,
        "vit_device": vit_device,
    }
