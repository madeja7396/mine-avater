from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class PipelineInput:
    input_audio: Path
    reference_image: Path
    workspace: Path


@dataclass(frozen=True)
class IntermediateArtifacts:
    audio_features: Path
    mouth_landmarks: Path
    frames_dir: Path


@dataclass(frozen=True)
class PipelineOutput:
    output_video: Path


class Preprocessor(Protocol):
    def run(self, payload: PipelineInput) -> IntermediateArtifacts:
        """Extract audio features and face landmarks."""


class Generator(Protocol):
    def run(
        self,
        payload: PipelineInput,
        artifacts: IntermediateArtifacts,
    ) -> IntermediateArtifacts:
        """Generate per-frame outputs into frames_dir."""


class Postprocessor(Protocol):
    def run(
        self,
        payload: PipelineInput,
        artifacts: IntermediateArtifacts,
    ) -> PipelineOutput:
        """Mux frames and audio into a single output video."""

