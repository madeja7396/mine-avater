from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PreprocessConfig:
    window_ms: float = 25.0
    hop_ms: float = 10.0
    landmark_frames: int = 12


@dataclass(frozen=True)
class GeneratorConfig:
    frame_count: int = 12
    backend: str = "heuristic"
    vit_patch_size: int = 16
    vit_image_size: int = 224
    vit_fallback_mock: bool = True
    vit_model_name: str = "google/vit-base-patch16-224"
    vit_use_pretrained: bool = False
    vit_device: str = "cpu"


@dataclass(frozen=True)
class PostprocessConfig:
    fps: int = 25


@dataclass(frozen=True)
class ScaffoldConfig:
    preprocess: PreprocessConfig = field(default_factory=PreprocessConfig)
    generator: GeneratorConfig = field(default_factory=GeneratorConfig)
    postprocess: PostprocessConfig = field(default_factory=PostprocessConfig)
