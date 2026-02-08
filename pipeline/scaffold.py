from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from pipeline.contracts import (
    Generator,
    IntermediateArtifacts,
    PipelineInput,
    PipelineOutput,
    Postprocessor,
    Preprocessor,
)
from pipeline.generator import generate_frames
from pipeline.interfaces import PipelinePaths
from pipeline.postprocess import finalize_output_video
from pipeline.preprocess import build_mouth_landmarks, extract_audio_features


class ScaffoldPreprocessor(Preprocessor):
    def run(self, payload: PipelineInput) -> IntermediateArtifacts:
        paths = PipelinePaths(payload.workspace)
        payload.workspace.mkdir(parents=True, exist_ok=True)

        extract_audio_features(payload.input_audio, paths.audio_features)
        build_mouth_landmarks(payload.reference_image, paths.mouth_landmarks, frame_count=12)

        return IntermediateArtifacts(
            audio_features=paths.audio_features,
            mouth_landmarks=paths.mouth_landmarks,
            frames_dir=paths.frames,
        )


class ScaffoldGenerator(Generator):
    def __init__(self, frame_count: int = 12) -> None:
        self.frame_count = frame_count

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
            frame_count=self.frame_count,
        )
        return artifacts


class ScaffoldPostprocessor(Postprocessor):
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
            fps=25,
        )
        return PipelineOutput(output_video=paths.output_video)


def run_scaffold_pipeline(
    input_audio: Path,
    reference_image: Path,
    workspace: Path,
) -> PipelineOutput:
    payload = PipelineInput(
        input_audio=input_audio,
        reference_image=reference_image,
        workspace=workspace,
    )
    preprocessor = ScaffoldPreprocessor()
    generator = ScaffoldGenerator()
    postprocessor = ScaffoldPostprocessor()

    artifacts = preprocessor.run(payload)
    artifacts = generator.run(payload, artifacts)
    output = postprocessor.run(payload, artifacts)

    manifest = workspace / "pipeline_run.json"
    manifest.write_text(
        json.dumps(
            {
                "pipeline_input": asdict(payload),
                "intermediate_artifacts": asdict(artifacts),
                "pipeline_output": asdict(output),
            },
            ensure_ascii=True,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )
    return output
