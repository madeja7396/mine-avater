from __future__ import annotations

import base64
import json
import struct
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
from pipeline.interfaces import PipelinePaths


_TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/w8AAgMBAp9Wj2QAAAAASUVORK5CYII="
)


def _write_npy_f32_matrix(path: Path, rows: int, cols: int) -> None:
    values = [float(i) / 10.0 for i in range(rows * cols)]
    header_dict = f"{{'descr': '<f4', 'fortran_order': False, 'shape': ({rows}, {cols}), }}"
    header = header_dict.encode("latin1")

    preamble_len = 10
    pad = (16 - ((preamble_len + len(header) + 1) % 16)) % 16
    header_padded = header + (b" " * pad) + b"\n"

    raw = bytearray()
    raw.extend(b"\x93NUMPY")
    raw.extend(bytes([1, 0]))
    raw.extend(struct.pack("<H", len(header_padded)))
    raw.extend(header_padded)
    raw.extend(struct.pack("<" + ("f" * len(values)), *values))
    path.write_bytes(bytes(raw))


class ScaffoldPreprocessor(Preprocessor):
    def run(self, payload: PipelineInput) -> IntermediateArtifacts:
        paths = PipelinePaths(payload.workspace)
        payload.workspace.mkdir(parents=True, exist_ok=True)

        _write_npy_f32_matrix(paths.audio_features, rows=8, cols=16)

        landmarks = []
        for frame_index in range(12):
            landmarks.append(
                {
                    "frame_index": frame_index,
                    "points": [
                        [0.40, 0.55],
                        [0.46, 0.60],
                        [0.54, 0.60],
                        [0.60, 0.55],
                    ],
                }
            )
        paths.mouth_landmarks.write_text(
            json.dumps(landmarks, ensure_ascii=True, indent=2), encoding="utf-8"
        )

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
        artifacts.frames_dir.mkdir(parents=True, exist_ok=True)
        for i in range(self.frame_count):
            frame_path = artifacts.frames_dir / f"{i:06d}.png"
            frame_path.write_bytes(_TINY_PNG)
        return artifacts


class ScaffoldPostprocessor(Postprocessor):
    def run(
        self,
        payload: PipelineInput,
        artifacts: IntermediateArtifacts,
    ) -> PipelineOutput:
        paths = PipelinePaths(payload.workspace)
        # 実実装前は mux を模したプレースホルダを出力する。
        payload_data = {
            "input_audio": str(payload.input_audio),
            "reference_image": str(payload.reference_image),
            "audio_features": str(artifacts.audio_features),
            "mouth_landmarks": str(artifacts.mouth_landmarks),
            "frames_dir": str(artifacts.frames_dir),
        }
        paths.output_video.write_text(
            json.dumps(payload_data, ensure_ascii=True, indent=2),
            encoding="utf-8",
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

