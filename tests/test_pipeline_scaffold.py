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
            self.assertIn("stages", payload)
            self.assertEqual(payload["stages"]["generator"]["backend_requested"], "heuristic")
            self.assertEqual(payload["stages"]["generator"]["backend_used"], "heuristic")

    def test_scaffold_pipeline_respects_frame_count_and_fps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_audio = root / "input.wav"
            reference_image = root / "face.png"
            reference_dir = root / "refs"
            workspace = root / "workspace"

            self.write_sine_wav(input_audio)
            self.write_png(reference_image)
            reference_dir.mkdir(parents=True, exist_ok=True)
            self.write_png(reference_dir / "a.png")
            self.write_png(reference_dir / "b.png")

            result = self.run_cmd(
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
                "--window-ms",
                "20",
                "--hop-ms",
                "8",
                "--generator-backend",
                "vit-mock",
                "--vit-reference-dir",
                str(reference_dir),
                "--vit-reference-limit",
                "1",
                "--vit-enable-3d-conditioning",
                "--vit-3d-conditioning-weight",
                "0.6",
                "--temporal-spatial-loss-weight",
                "0.5",
                "--temporal-smooth-factor",
                "0.4",
            )

            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            frames = sorted((workspace / "frames").glob("*.png"))
            self.assertEqual(len(frames), 6)

            manifest = json.loads((workspace / "pipeline_run.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["stages"]["generator"]["frame_count"], 6)
            self.assertEqual(manifest["stages"]["postprocessor"]["fps"], 15)
            self.assertEqual(manifest["stages"]["preprocessor"]["window_ms"], 20.0)
            self.assertEqual(manifest["stages"]["preprocessor"]["hop_ms"], 8.0)
            self.assertEqual(manifest["stages"]["generator"]["backend_requested"], "vit-mock")
            self.assertIn("vit-mock", manifest["stages"]["generator"]["backend_used"])
            self.assertEqual(manifest["stages"]["generator"]["vit_reference_count"], 2)
            self.assertEqual(manifest["stages"]["generator"]["vit_enable_3d_conditioning"], True)
            self.assertEqual(manifest["stages"]["generator"]["vit_3d_conditioning_weight"], 0.6)
            self.assertEqual(manifest["stages"]["generator"]["temporal_spatial_loss_weight"], 0.5)
            self.assertEqual(manifest["stages"]["generator"]["temporal_smooth_factor"], 0.4)

            meta = json.loads((workspace / "output.mp4.meta.json").read_text(encoding="utf-8"))
            self.assertEqual(meta["fps"], 15)

    def test_scaffold_pipeline_rejects_invalid_vit_3d_weight(self) -> None:
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
                "--vit-enable-3d-conditioning",
                "--vit-3d-conditioning-weight",
                "1.5",
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("ERROR: invalid_vit_3d_conditioning_weight", result.stdout)

    def test_scaffold_pipeline_rejects_invalid_temporal_loss_weight(self) -> None:
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
                "--temporal-spatial-loss-weight",
                "1.2",
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("ERROR: invalid_temporal_spatial_loss_weight", result.stdout)

    def test_scaffold_pipeline_rejects_invalid_temporal_smooth_factor(self) -> None:
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
                "--temporal-smooth-factor",
                "-0.1",
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("ERROR: invalid_temporal_smooth_factor", result.stdout)

    def test_scaffold_pipeline_rejects_invalid_vit_grid(self) -> None:
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
                "--generator-backend",
                "vit-hf",
                "--vit-image-size",
                "230",
                "--vit-patch-size",
                "16",
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("ERROR: invalid_vit_grid", result.stdout)

    def test_scaffold_pipeline_rejects_missing_vit_reference_dir(self) -> None:
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
                "--generator-backend",
                "vit-mock",
                "--vit-reference-dir",
                str(root / "missing"),
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("ERROR: vit_reference_dir_not_found", result.stdout)


if __name__ == "__main__":
    unittest.main()
