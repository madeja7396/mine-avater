from __future__ import annotations

from pathlib import Path

from pipeline.config import GeneratorConfig, PostprocessConfig, PreprocessConfig, ScaffoldConfig
from pipeline.contracts import (
    Generator,
    IntermediateArtifacts,
    PipelineInput,
    PipelineOutput,
    Postprocessor,
    Preprocessor,
)
from pipeline.engine import PipelineRunner
from pipeline.generator import generate_frames
from pipeline.interfaces import PipelinePaths
from pipeline.postprocess import finalize_output_video
from pipeline.preprocess import build_mouth_landmarks, extract_audio_features


class ScaffoldPreprocessor(Preprocessor):
    def __init__(self, config: PreprocessConfig) -> None:
        self.config = config

    def describe(self) -> dict:
        return {
            "window_ms": self.config.window_ms,
            "hop_ms": self.config.hop_ms,
            "landmark_frames": self.config.landmark_frames,
        }

    def run(self, payload: PipelineInput) -> IntermediateArtifacts:
        paths = PipelinePaths(payload.workspace)
        payload.workspace.mkdir(parents=True, exist_ok=True)

        extract_audio_features(
            payload.input_audio,
            paths.audio_features,
            window_ms=self.config.window_ms,
            hop_ms=self.config.hop_ms,
        )
        build_mouth_landmarks(
            payload.reference_image,
            paths.mouth_landmarks,
            frame_count=self.config.landmark_frames,
        )

        return IntermediateArtifacts(
            audio_features=paths.audio_features,
            mouth_landmarks=paths.mouth_landmarks,
            frames_dir=paths.frames,
        )


class ScaffoldGenerator(Generator):
    def __init__(self, config: GeneratorConfig) -> None:
        self.config = config

    def describe(self) -> dict:
        return {"frame_count": self.config.frame_count}

    def run(
        self,
        payload: PipelineInput,
        artifacts: IntermediateArtifacts,
    ) -> IntermediateArtifacts:
        generate_frames(
            reference_image=payload.reference_image,
            audio_features=artifacts.audio_features,
            mouth_landmarks=artifacts.mouth_landmarks,
            output_dir=artifacts.frames_dir,
            frame_count=self.config.frame_count,
        )
        return artifacts


class ScaffoldPostprocessor(Postprocessor):
    def __init__(self, config: PostprocessConfig) -> None:
        self.config = config

    def describe(self) -> dict:
        return {"fps": self.config.fps}

    def run(
        self,
        payload: PipelineInput,
        artifacts: IntermediateArtifacts,
    ) -> PipelineOutput:
        paths = PipelinePaths(payload.workspace)
        finalize_output_video(
            input_audio=payload.input_audio,
            frames_dir=artifacts.frames_dir,
            output_video=paths.output_video,
            fps=self.config.fps,
        )
        return PipelineOutput(output_video=paths.output_video)


def run_scaffold_pipeline(
    input_audio: Path,
    reference_image: Path,
    workspace: Path,
    config: ScaffoldConfig | None = None,
) -> PipelineOutput:
    config = config or ScaffoldConfig()
    payload = PipelineInput(
        input_audio=input_audio,
        reference_image=reference_image,
        workspace=workspace,
    )
    runner = PipelineRunner(
        preprocessor=ScaffoldPreprocessor(config.preprocess),
        generator=ScaffoldGenerator(config.generator),
        postprocessor=ScaffoldPostprocessor(config.postprocess),
    )
    return runner.run(payload, manifest_path=workspace / "pipeline_run.json")
