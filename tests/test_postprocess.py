from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pipeline.postprocess import finalize_output_video, write_placeholder_output


class PostprocessTest(unittest.TestCase):
    def test_write_placeholder_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "output.mp4"
            payload = {"mode": "placeholder", "k": "v"}
            write_placeholder_output(path, payload)
            loaded = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(loaded["mode"], "placeholder")
            self.assertEqual(loaded["k"], "v")

    def test_finalize_output_video_placeholder_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            audio = root / "input.wav"
            frames_dir = root / "frames"
            output = root / "output.mp4"
            audio.write_bytes(b"dummy")
            frames_dir.mkdir()

            with patch("pipeline.postprocess.mux_frames_with_audio", return_value=False):
                mode = finalize_output_video(audio, frames_dir, output, fps=25)

            self.assertEqual(mode, "placeholder")
            self.assertTrue(output.exists())
            self.assertTrue((root / "output.mp4.meta.json").exists())

    def test_finalize_output_video_ffmpeg_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            audio = root / "input.wav"
            frames_dir = root / "frames"
            output = root / "output.mp4"
            audio.write_bytes(b"dummy")
            frames_dir.mkdir()
            output.write_bytes(b"ftyp")

            with patch("pipeline.postprocess.mux_frames_with_audio", return_value=True):
                mode = finalize_output_video(audio, frames_dir, output, fps=25)

            self.assertEqual(mode, "ffmpeg")
            meta = json.loads((root / "output.mp4.meta.json").read_text(encoding="utf-8"))
            self.assertEqual(meta["mode"], "ffmpeg")


if __name__ == "__main__":
    unittest.main()

