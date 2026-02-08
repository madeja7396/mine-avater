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


class PipelineRunner:
    def __init__(
        self,
        preprocessor: Preprocessor,
        generator: Generator,
        postprocessor: Postprocessor,
    ) -> None:
        self.preprocessor = preprocessor
        self.generator = generator
        self.postprocessor = postprocessor

    def run(self, payload: PipelineInput, manifest_path: Path | None = None) -> PipelineOutput:
        artifacts = self.preprocessor.run(payload)
        artifacts = self.generator.run(payload, artifacts)
        output = self.postprocessor.run(payload, artifacts)
        if manifest_path is not None:
            write_pipeline_manifest(
                path=manifest_path,
                payload=payload,
                artifacts=artifacts,
                output=output,
                preprocessor=self.preprocessor,
                generator=self.generator,
                postprocessor=self.postprocessor,
            )
        return output


def write_pipeline_manifest(
    path: Path,
    payload: PipelineInput,
    artifacts: IntermediateArtifacts,
    output: PipelineOutput,
    preprocessor: Preprocessor,
    generator: Generator,
    postprocessor: Postprocessor,
) -> None:
    stage_config = {
        "preprocessor": getattr(preprocessor, "describe", lambda: {})(),
        "generator": getattr(generator, "describe", lambda: {})(),
        "postprocessor": getattr(postprocessor, "describe", lambda: {})(),
    }
    path.write_text(
        json.dumps(
            {
                "pipeline_input": asdict(payload),
                "intermediate_artifacts": asdict(artifacts),
                "pipeline_output": asdict(output),
                "stages": stage_config,
            },
            ensure_ascii=True,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )

