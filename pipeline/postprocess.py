from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


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


def finalize_output_video(
    input_audio: Path,
    frames_dir: Path,
    output_video: Path,
    fps: int = 25,
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

    meta_path = output_video.with_suffix(output_video.suffix + ".meta.json")
    meta_path.write_text(
        json.dumps(
            {
                "mode": mode,
                "input_audio": str(input_audio),
                "frames_dir": str(frames_dir),
                "output_video": str(output_video),
                "fps": fps,
            },
            ensure_ascii=True,
            indent=2,
        ),
        encoding="utf-8",
    )
    return mode

