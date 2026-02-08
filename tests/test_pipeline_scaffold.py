from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


class PipelineScaffoldTest(unittest.TestCase):
    def run_cmd(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "pipeline/run_scaffold.py", *args],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_scaffold_pipeline_generates_expected_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_audio = root / "input.wav"
            reference_image = root / "face.png"
            workspace = root / "workspace"

            input_audio.write_bytes(b"RIFF")
            reference_image.write_bytes(b"\x89PNG\r\n\x1a\n")

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
            self.assertTrue((workspace / "pipeline_run.json").is_file())

            frames = sorted((workspace / "frames").glob("*.png"))
            self.assertEqual(len(frames), 12)

            payload = json.loads(
                (workspace / "pipeline_run.json").read_text(encoding="utf-8")
            )
            self.assertIn("pipeline_input", payload)
            self.assertIn("intermediate_artifacts", payload)
            self.assertIn("pipeline_output", payload)


if __name__ == "__main__":
    unittest.main()

