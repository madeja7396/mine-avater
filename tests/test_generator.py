from __future__ import annotations

import math
import struct
import tempfile
import unittest
import wave
from pathlib import Path

from pipeline.generator import generate_frames, generate_frames_with_backend
from pipeline.preprocess import build_mouth_landmarks, extract_audio_features

TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x04\x00\x00\x00\xb5\x1c\x0c\x02\x00\x00\x00\x0bIDATx\xdac\xfc\xff"
    b"\x0f\x00\x02\x03\x01\x02\x9fV\x8fd\x00\x00\x00\x00IEND\xaeB`\x82"
)


def read_png_size(path: Path) -> tuple[int, int]:
    raw = path.read_bytes()
    if not raw.startswith(b"\x89PNG\r\n\x1a\n"):
        raise AssertionError("invalid png signature")
    if raw[12:16] != b"IHDR":
        raise AssertionError("missing IHDR")
    width = int.from_bytes(raw[16:20], "big")
    height = int.from_bytes(raw[20:24], "big")
    return width, height


class GeneratorTest(unittest.TestCase):
    def write_sine_wav(self, path: Path, seconds: float = 0.25, sample_rate: int = 16000) -> None:
        frames = int(seconds * sample_rate)
        payload = bytearray()
        for i in range(frames):
            value = int(0.4 * 32767.0 * math.sin((2.0 * math.pi * 330.0 * i) / sample_rate))
            payload.extend(struct.pack("<h", value))
        with wave.open(str(path), "wb") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(sample_rate)
            handle.writeframes(bytes(payload))

    def test_generate_frames_writes_png_sequence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            reference_image = root / "face.png"
            input_audio = root / "input.wav"
            audio_features = root / "audio_features.npy"
            mouth_landmarks = root / "mouth_landmarks.json"
            frames_dir = root / "frames"

            reference_image.write_bytes(TINY_PNG)
            self.write_sine_wav(input_audio)
            extract_audio_features(input_audio, audio_features)
            build_mouth_landmarks(reference_image, mouth_landmarks, frame_count=6)

            count = generate_frames(
                reference_image=reference_image,
                audio_features=audio_features,
                mouth_landmarks=mouth_landmarks,
                output_dir=frames_dir,
                frame_count=6,
            )

            self.assertEqual(count, 6)
            files = sorted(frames_dir.glob("*.png"))
            self.assertEqual(len(files), 6)
            width, height = read_png_size(files[0])
            self.assertGreaterEqual(width, 64)
            self.assertGreaterEqual(height, 64)
            self.assertTrue(files[0].stat().st_size > 100)

    def test_generate_frames_vit_mock_backend(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            reference_image = root / "face.png"
            input_audio = root / "input.wav"
            audio_features = root / "audio_features.npy"
            mouth_landmarks = root / "mouth_landmarks.json"
            frames_dir = root / "frames"

            reference_image.write_bytes(TINY_PNG)
            self.write_sine_wav(input_audio)
            extract_audio_features(input_audio, audio_features)
            build_mouth_landmarks(reference_image, mouth_landmarks, frame_count=4)

            result = generate_frames_with_backend(
                reference_image=reference_image,
                audio_features=audio_features,
                mouth_landmarks=mouth_landmarks,
                output_dir=frames_dir,
                frame_count=4,
                backend="vit-mock",
            )

            self.assertEqual(result["frame_count"], 4)
            self.assertEqual(result["backend_requested"], "vit-mock")
            self.assertEqual(result["backend_used"], "vit-mock")
            self.assertEqual(len(sorted(frames_dir.glob("*.png"))), 4)


if __name__ == "__main__":
    unittest.main()
