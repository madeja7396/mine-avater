from __future__ import annotations

import json
import math
import struct
import wave
from pathlib import Path


def write_npy_f32_matrix(path: Path, matrix: list[list[float]]) -> None:
    rows = len(matrix)
    cols = len(matrix[0]) if rows else 0
    values = [value for row in matrix for value in row]
    header_dict = f"{{'descr': '<f4', 'fortran_order': False, 'shape': ({rows}, {cols}), }}"
    header = header_dict.encode("latin1")

    preamble_len = 10
    pad = (16 - ((preamble_len + len(header) + 1) % 16)) % 16
    header_padded = header + (b" " * pad) + b"\n"

    raw = bytearray()
    raw.extend(b"\x93NUMPY")
    raw.extend(bytes([1, 0]))
    raw.extend(struct.pack("<H", len(header_padded)))
    raw.extend(header_padded)
    if values:
        raw.extend(struct.pack("<" + ("f" * len(values)), *values))
    path.write_bytes(bytes(raw))


def _decode_pcm_frames(raw: bytes, channels: int, sample_width: int) -> list[float]:
    if sample_width == 1:
        unpacked = struct.unpack("<" + ("B" * len(raw)), raw)
        mono = [(value - 128) / 128.0 for value in unpacked]
    elif sample_width == 2:
        unpacked = struct.unpack("<" + ("h" * (len(raw) // 2)), raw)
        mono = [value / 32768.0 for value in unpacked]
    elif sample_width == 4:
        unpacked = struct.unpack("<" + ("i" * (len(raw) // 4)), raw)
        mono = [value / 2147483648.0 for value in unpacked]
    else:
        raise ValueError(f"Unsupported WAV sample width: {sample_width}")

    if channels == 1:
        return mono

    frames: list[float] = []
    for idx in range(0, len(mono), channels):
        chunk = mono[idx : idx + channels]
        if not chunk:
            continue
        frames.append(sum(chunk) / float(len(chunk)))
    return frames


def read_wav_mono(path: Path) -> tuple[int, list[float]]:
    with wave.open(str(path), "rb") as handle:
        channels = handle.getnchannels()
        sample_width = handle.getsampwidth()
        sample_rate = handle.getframerate()
        raw = handle.readframes(handle.getnframes())
    return sample_rate, _decode_pcm_frames(raw, channels=channels, sample_width=sample_width)


def extract_audio_features(
    input_audio: Path,
    output_npy: Path,
    window_ms: float = 25.0,
    hop_ms: float = 10.0,
) -> int:
    sample_rate, samples = read_wav_mono(input_audio)
    if not samples:
        matrix = [[0.0, 0.0, 0.0]]
        write_npy_f32_matrix(output_npy, matrix)
        return 1

    window = max(1, int(sample_rate * (window_ms / 1000.0)))
    hop = max(1, int(sample_rate * (hop_ms / 1000.0)))
    if len(samples) < window:
        starts = [0]
    else:
        starts = list(range(0, len(samples) - window + 1, hop))
        if not starts:
            starts = [0]

    matrix: list[list[float]] = []
    for start in starts:
        frame = samples[start : start + window]
        n = len(frame)
        if n == 0:
            continue
        rms = math.sqrt(sum(value * value for value in frame) / n)
        mean_abs = sum(abs(value) for value in frame) / n
        zero_crossings = 0
        for i in range(1, n):
            if (frame[i - 1] >= 0 and frame[i] < 0) or (frame[i - 1] < 0 and frame[i] >= 0):
                zero_crossings += 1
        zcr = zero_crossings / max(1, n - 1)
        matrix.append([rms, zcr, mean_abs])

    if not matrix:
        matrix = [[0.0, 0.0, 0.0]]
    write_npy_f32_matrix(output_npy, matrix)
    return len(matrix)


def get_image_size(path: Path) -> tuple[int, int]:
    raw = path.read_bytes()
    if raw.startswith(b"\x89PNG\r\n\x1a\n") and len(raw) >= 24:
        width = int.from_bytes(raw[16:20], "big")
        height = int.from_bytes(raw[20:24], "big")
        return width, height

    if raw.startswith(b"\xff\xd8"):
        i = 2
        while i + 9 < len(raw):
            if raw[i] != 0xFF:
                i += 1
                continue
            marker = raw[i + 1]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3):
                block_len = int.from_bytes(raw[i + 2 : i + 4], "big")
                if block_len < 7:
                    break
                height = int.from_bytes(raw[i + 5 : i + 7], "big")
                width = int.from_bytes(raw[i + 7 : i + 9], "big")
                return width, height
            block_len = int.from_bytes(raw[i + 2 : i + 4], "big")
            if block_len <= 0:
                break
            i += 2 + block_len

    raise ValueError(f"Unsupported image format for size detection: {path}")


def build_mouth_landmarks(
    reference_image: Path,
    output_json: Path,
    frame_count: int = 12,
) -> int:
    width, height = get_image_size(reference_image)
    _ = (width, height)

    landmarks = []
    for frame_index in range(frame_count):
        open_ratio = 0.015 + 0.01 * (0.5 + 0.5 * math.sin((2.0 * math.pi * frame_index) / frame_count))
        landmarks.append(
            {
                "frame_index": frame_index,
                "points": [
                    [0.40, 0.58],
                    [0.46, 0.62 + open_ratio],
                    [0.54, 0.62 + open_ratio],
                    [0.60, 0.58],
                ],
            }
        )

    output_json.write_text(json.dumps(landmarks, ensure_ascii=True, indent=2), encoding="utf-8")
    return frame_count

