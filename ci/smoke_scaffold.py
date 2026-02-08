from __future__ import annotations

import math
import struct
import subprocess
import sys
import tempfile
import wave
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x04\x00\x00\x00\xb5\x1c\x0c\x02\x00\x00\x00\x0bIDATx\xdac\xfc\xff"
    b"\x0f\x00\x02\x03\x01\x02\x9fV\x8fd\x00\x00\x00\x00IEND\xaeB`\x82"
)


def write_sine_wav(path: Path, seconds: float = 0.25, sample_rate: int = 16000) -> None:
    frames = int(seconds * sample_rate)
    payload = bytearray()
    for i in range(frames):
        value = int(0.4 * 32767.0 * math.sin((2.0 * math.pi * 440.0 * i) / sample_rate))
        payload.extend(struct.pack("<h", value))
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(bytes(payload))


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        input_audio = root / "input.wav"
        reference_image = root / "face.png"
        workspace = root / "workspace"

        write_sine_wav(input_audio)
        reference_image.write_bytes(TINY_PNG)

        cmd = [
            sys.executable,
            "pipeline/run_scaffold.py",
            "--input-audio",
            str(input_audio),
            "--reference-image",
            str(reference_image),
            "--workspace",
            str(workspace),
            "--frame-count",
            "6",
            "--fps",
            "15",
        ]
        result = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            print("ERROR: scaffold_smoke_failed")
            if result.stdout:
                print(result.stdout.rstrip())
            if result.stderr:
                print(result.stderr.rstrip())
            return 1

        required = [
            workspace / "audio_features.npy",
            workspace / "mouth_landmarks.json",
            workspace / "frames",
            workspace / "output.mp4",
            workspace / "pipeline_run.json",
            workspace / "output.mp4.meta.json",
        ]
        missing = [path for path in required if not path.exists()]
        if missing:
            print(f"ERROR: scaffold_smoke_missing count={len(missing)}")
            for path in missing:
                print(f"ERROR: missing {path}")
            return 1

        frames = sorted((workspace / "frames").glob("*.png"))
        if len(frames) != 6:
            print(f"ERROR: scaffold_smoke_frame_count expected=6 got={len(frames)}")
            return 1

        print("METRIC: scaffold_smoke_passed frame_count=6")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())

