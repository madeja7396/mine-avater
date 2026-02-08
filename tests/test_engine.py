from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from pipeline.contracts import IntermediateArtifacts, PipelineInput, PipelineOutput
from pipeline.engine import PipelineRunner


class DummyPreprocessor:
    def describe(self) -> dict:
        return {"name": "dummy-pre"}

    def run(self, payload: PipelineInput) -> IntermediateArtifacts:
        payload.workspace.mkdir(parents=True, exist_ok=True)
        audio = payload.workspace / "audio_features.npy"
        mouth = payload.workspace / "mouth_landmarks.json"
        frames = payload.workspace / "frames"
        audio.write_bytes(b"npy")
        mouth.write_text("[]", encoding="utf-8")
        frames.mkdir(exist_ok=True)
        return IntermediateArtifacts(audio_features=audio, mouth_landmarks=mouth, frames_dir=frames)


class DummyGenerator:
    def describe(self) -> dict:
        return {"name": "dummy-gen"}

    def run(self, payload: PipelineInput, artifacts: IntermediateArtifacts) -> IntermediateArtifacts:
        (artifacts.frames_dir / "000000.png").write_bytes(b"\x89PNG\r\n\x1a\n")
        return artifacts


class DummyPostprocessor:
    def describe(self) -> dict:
        return {"name": "dummy-post"}

    def run(self, payload: PipelineInput, artifacts: IntermediateArtifacts) -> PipelineOutput:
        out = payload.workspace / "output.mp4"
        out.write_bytes(b"video")
        return PipelineOutput(output_video=out)


class EngineTest(unittest.TestCase):
    def test_pipeline_runner_writes_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            payload = PipelineInput(
                input_audio=root / "in.wav",
                reference_image=root / "face.png",
                workspace=root / "workspace",
            )
            payload.input_audio.write_bytes(b"wav")
            payload.reference_image.write_bytes(b"png")

            runner = PipelineRunner(
                preprocessor=DummyPreprocessor(),
                generator=DummyGenerator(),
                postprocessor=DummyPostprocessor(),
            )
            manifest = payload.workspace / "pipeline_run.json"
            output = runner.run(payload, manifest_path=manifest)

            self.assertTrue(output.output_video.exists())
            data = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(data["stages"]["preprocessor"]["name"], "dummy-pre")
            self.assertEqual(data["stages"]["generator"]["name"], "dummy-gen")
            self.assertEqual(data["stages"]["postprocessor"]["name"], "dummy-post")


if __name__ == "__main__":
    unittest.main()

