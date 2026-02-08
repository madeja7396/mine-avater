from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

WATERMARK_POLICY_VERSION = "v1"


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def mux_frames_with_audio(
    input_audio: Path,
    frames_dir: Path,
    output_video: Path,
    fps: int = 25,
) -> bool:
    if not ffmpeg_available():
        return False

    pattern = frames_dir / "%06d.png"
    command = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-framerate",
        str(fps),
        "-i",
        str(pattern),
        "-i",
        str(input_audio),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-shortest",
        str(output_video),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    return result.returncode == 0 and output_video.exists()


def write_placeholder_output(output_video: Path, payload: dict) -> None:
    output_video.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


def build_watermark_payload(
    input_audio: Path,
    frames_dir: Path,
    output_video: Path,
    fps: int,
    watermark_label: str,
    mode: str,
) -> dict[str, str | int]:
    fingerprint = hashlib.sha256(
        (
            f"{input_audio}|{frames_dir}|{output_video}|{fps}|"
            f"{watermark_label}|{WATERMARK_POLICY_VERSION}"
        ).encode("utf-8")
    ).hexdigest()[:16]
    return {
        "policy_version": WATERMARK_POLICY_VERSION,
        "watermark_policy_version": WATERMARK_POLICY_VERSION,
        "watermark_id": f"wm-{fingerprint}",
        "watermark_label": watermark_label,
        "watermark_mode": mode,
        "input_audio": str(input_audio),
        "frames_dir": str(frames_dir),
        "output_video": str(output_video),
        "fps": fps,
    }


def write_watermark_manifest(output_video: Path, payload: dict[str, str | int]) -> Path:
    watermark_path = output_video.with_suffix(output_video.suffix + ".watermark.json")
    watermark_path.write_text(
        json.dumps(payload, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    return watermark_path


def finalize_output_video(
    input_audio: Path,
    frames_dir: Path,
    output_video: Path,
    fps: int = 25,
    watermark_enabled: bool = True,
    watermark_label: str = "MINE-AVATER/RESEARCH-ONLY",
) -> str:
    success = mux_frames_with_audio(input_audio=input_audio, frames_dir=frames_dir, output_video=output_video, fps=fps)
    if success:
        mode = "ffmpeg"
    else:
        mode = "placeholder"
        write_placeholder_output(
            output_video,
            {
                "mode": mode,
                "input_audio": str(input_audio),
                "frames_dir": str(frames_dir),
                "reason": "ffmpeg unavailable or mux failed",
            },
        )

    watermark_manifest: str | None = None
    watermark_id: str | None = None
    if watermark_enabled:
        payload = build_watermark_payload(
            input_audio=input_audio,
            frames_dir=frames_dir,
            output_video=output_video,
            fps=fps,
            watermark_label=watermark_label,
            mode="manifest",
        )
        watermark_id = str(payload["watermark_id"])
        watermark_manifest = str(write_watermark_manifest(output_video, payload))

    meta_path = output_video.with_suffix(output_video.suffix + ".meta.json")
    meta_path.write_text(
        json.dumps(
            {
                "mode": mode,
                "input_audio": str(input_audio),
                "frames_dir": str(frames_dir),
                "output_video": str(output_video),
                "fps": fps,
                "watermark_enabled": watermark_enabled,
                "watermark_label": watermark_label,
                "watermark_policy_version": WATERMARK_POLICY_VERSION,
                "watermark_id": watermark_id,
                "watermark_manifest": watermark_manifest,
            },
            ensure_ascii=True,
            indent=2,
        ),
        encoding="utf-8",
    )
    return mode
