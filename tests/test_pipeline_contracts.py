from __future__ import annotations

import math
import struct
import tempfile
import unittest
import wave
from pathlib import Path

from pipeline.contracts import IntermediateArtifacts, PipelineInput, PipelineOutput
from pipeline.interfaces import PipelinePaths
from pipeline.scaffold import run_scaffold_pipeline

TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x04\x00\x00\x00\xb5\x1c\x0c\x02\x00\x00\x00\x0bIDATx\xdac\xfc\xff"
    b"\x0f\x00\x02\x03\x01\x02\x9fV\x8fd\x00\x00\x00\x00IEND\xaeB`\x82"
)


class PipelineContractsTest(unittest.TestCase):
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
            self.write_sine_wav(input_audio)
            reference_image.write_bytes(TINY_PNG)

            output = run_scaffold_pipeline(
                input_audio=input_audio,
                reference_image=reference_image,
                workspace=root / "workspace",
            )
            self.assertEqual(output.output_video.name, "output.mp4")


if __name__ == "__main__":
    unittest.main()
