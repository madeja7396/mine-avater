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
from pipeline.generator import generate_frames_with_backend
from pipeline.interfaces import PipelinePaths
from pipeline.postprocess import finalize_output_video
from pipeline.preprocess import build_mouth_landmarks, extract_audio_features


def _list_reference_images(reference_dir: str | None, limit: int) -> list[Path]:
    if not reference_dir:
        return []
    root = Path(reference_dir)
    if not root.is_dir():
        return []
    allow = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}
    images = [p for p in sorted(root.iterdir()) if p.is_file() and p.suffix.lower() in allow]
    if limit > 0:
        images = images[:limit]
    return images


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
        self._backend_used = "not-run"
        self._reference_image_count = 1

    def describe(self) -> dict:
        return {
            "frame_count": self.config.frame_count,
            "backend_requested": self.config.backend,
            "backend_used": self._backend_used,
            "vit_reference_dir": self.config.vit_reference_dir,
            "vit_reference_limit": self.config.vit_reference_limit,
            "vit_reference_count": self._reference_image_count,
            "vit_patch_size": self.config.vit_patch_size,
            "vit_image_size": self.config.vit_image_size,
            "vit_model_name": self.config.vit_model_name,
            "vit_use_pretrained": self.config.vit_use_pretrained,
            "vit_device": self.config.vit_device,
            "vit_enable_3d_conditioning": self.config.vit_enable_3d_conditioning,
            "vit_3d_conditioning_weight": self.config.vit_3d_conditioning_weight,
            "temporal_spatial_loss_weight": self.config.temporal_spatial_loss_weight,
            "temporal_smooth_factor": self.config.temporal_smooth_factor,
        }

    def run(
        self,
        payload: PipelineInput,
        artifacts: IntermediateArtifacts,
    ) -> IntermediateArtifacts:
        extra_images = _list_reference_images(
            reference_dir=self.config.vit_reference_dir,
            limit=self.config.vit_reference_limit,
        )
        result = generate_frames_with_backend(
            reference_image=payload.reference_image,
            audio_features=artifacts.audio_features,
            mouth_landmarks=artifacts.mouth_landmarks,
            output_dir=artifacts.frames_dir,
            frame_count=self.config.frame_count,
            backend=self.config.backend,
            vit_reference_images=extra_images,
            vit_patch_size=self.config.vit_patch_size,
            vit_image_size=self.config.vit_image_size,
            vit_fallback_mock=self.config.vit_fallback_mock,
            vit_model_name=self.config.vit_model_name,
            vit_use_pretrained=self.config.vit_use_pretrained,
            vit_device=self.config.vit_device,
            vit_enable_3d_conditioning=self.config.vit_enable_3d_conditioning,
            vit_3d_conditioning_weight=self.config.vit_3d_conditioning_weight,
            temporal_spatial_loss_weight=self.config.temporal_spatial_loss_weight,
            temporal_smooth_factor=self.config.temporal_smooth_factor,
        )
        self._backend_used = str(result.get("backend_used", "unknown"))
        details = result.get("vit_details")
        if isinstance(details, dict):
            count = details.get("reference_count")
            if isinstance(count, (int, float)):
                self._reference_image_count = int(count)
            else:
                self._reference_image_count = 1 + len(extra_images)
        else:
            self._reference_image_count = 1 + len(extra_images)
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
