from __future__ import annotations

import json
import math
import subprocess
import struct
import sys
import tempfile
import unittest
import wave
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x04\x00\x00\x00\xb5\x1c\x0c\x02\x00\x00\x00\x0bIDATx\xdac\xfc\xff"
    b"\x0f\x00\x02\x03\x01\x02\x9fV\x8fd\x00\x00\x00\x00IEND\xaeB`\x82"
)


class PipelineScaffoldTest(unittest.TestCase):
    def run_cmd(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "pipeline/run_scaffold.py", *args],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

    def write_sine_wav(self, path: Path, seconds: float = 0.25, sample_rate: int = 16000) -> None:
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

    def write_png(self, path: Path) -> None:
        path.write_bytes(TINY_PNG)

    def test_scaffold_pipeline_generates_expected_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_audio = root / "input.wav"
            reference_image = root / "face.png"
            workspace = root / "workspace"

            self.write_sine_wav(input_audio)
            self.write_png(reference_image)

            result = self.run_cmd(
                "--input-audio",
                str(input_audio),
                "--reference-image",
                str(reference_image),
                "--workspace",
                str(workspace),
            )

            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            self.assertIn("METRIC: scaffold_pipeline_completed", result.stdout)
            self.assertTrue((workspace / "audio_features.npy").is_file())
            self.assertTrue((workspace / "mouth_landmarks.json").is_file())
            self.assertTrue((workspace / "frames").is_dir())
            self.assertTrue((workspace / "output.mp4").is_file())
            self.assertTrue((workspace / "output.mp4.meta.json").is_file())
            self.assertTrue((workspace / "pipeline_run.json").is_file())

            frames = sorted((workspace / "frames").glob("*.png"))
            self.assertEqual(len(frames), 12)
            self.assertTrue(frames[0].read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))
            self.assertGreater((workspace / "output.mp4").stat().st_size, 0)

            payload = json.loads(
                (workspace / "pipeline_run.json").read_text(encoding="utf-8")
            )
            self.assertIn("pipeline_input", payload)
            self.assertIn("intermediate_artifacts", payload)
            self.assertIn("pipeline_output", payload)


if __name__ == "__main__":
    unittest.main()
