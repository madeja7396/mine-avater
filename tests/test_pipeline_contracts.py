from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pipeline.contracts import IntermediateArtifacts, PipelineInput, PipelineOutput
from pipeline.interfaces import PipelinePaths
from pipeline.scaffold import run_scaffold_pipeline


class PipelineContractsTest(unittest.TestCase):
    def test_pipeline_paths_match_contract_names(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            paths = PipelinePaths(workspace=root)
            self.assertEqual(paths.audio_features.name, "audio_features.npy")
            self.assertEqual(paths.mouth_landmarks.name, "mouth_landmarks.json")
            self.assertEqual(paths.frames.name, "frames")
            self.assertEqual(paths.output_video.name, "output.mp4")

    def test_contract_dataclasses_hold_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            payload = PipelineInput(
                input_audio=root / "input.wav",
                reference_image=root / "face.png",
                workspace=root,
            )
            artifacts = IntermediateArtifacts(
                audio_features=root / "audio_features.npy",
                mouth_landmarks=root / "mouth_landmarks.json",
                frames_dir=root / "frames",
            )
            output = PipelineOutput(output_video=root / "output.mp4")

            self.assertTrue(str(payload.input_audio).endswith("input.wav"))
            self.assertTrue(str(artifacts.frames_dir).endswith("frames"))
            self.assertTrue(str(output.output_video).endswith("output.mp4"))

    def test_run_scaffold_pipeline_returns_output_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_audio = root / "input.wav"
            reference_image = root / "face.png"
            input_audio.write_bytes(b"RIFF")
            reference_image.write_bytes(b"\x89PNG\r\n\x1a\n")

            output = run_scaffold_pipeline(
                input_audio=input_audio,
                reference_image=reference_image,
                workspace=root / "workspace",
            )
            self.assertEqual(output.output_video.name, "output.mp4")


if __name__ == "__main__":
    unittest.main()
