from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


AUDIO_FEATURES_FILE = "audio_features.npy"
MOUTH_LANDMARKS_FILE = "mouth_landmarks.json"
FRAMES_DIR = "frames"
OUTPUT_VIDEO_FILE = "output.mp4"


@dataclass(frozen=True)
class PipelinePaths:
    workspace: Path

    @property
    def audio_features(self) -> Path:
        return self.workspace / AUDIO_FEATURES_FILE

    @property
    def mouth_landmarks(self) -> Path:
        return self.workspace / MOUTH_LANDMARKS_FILE

    @property
    def frames(self) -> Path:
        return self.workspace / FRAMES_DIR

    @property
    def output_video(self) -> Path:
        return self.workspace / OUTPUT_VIDEO_FILE

