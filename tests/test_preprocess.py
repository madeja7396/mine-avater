from __future__ import annotations

import json
import math
import re
import struct
import tempfile
import unittest
import wave
from pathlib import Path

from pipeline.preprocess import build_mouth_landmarks, extract_audio_features, get_image_size

TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x04\x00\x00\x00\xb5\x1c\x0c\x02\x00\x00\x00\x0bIDATx\xdac\xfc\xff"
    b"\x0f\x00\x02\x03\x01\x02\x9fV\x8fd\x00\x00\x00\x00IEND\xaeB`\x82"
)


def parse_npy_shape(path: Path) -> tuple[int, int]:
    raw = path.read_bytes()
    if not raw.startswith(b"\x93NUMPY"):
        raise AssertionError("not npy")
    header_len = int.from_bytes(raw[8:10], "little")
    header = raw[10 : 10 + header_len].decode("latin1")
    match = re.search(r"'shape': \((\d+), (\d+)\)", header)
    if not match:
        raise AssertionError("shape not found")
    return int(match.group(1)), int(match.group(2))


class PreprocessTest(unittest.TestCase):
    def write_sine_wav(self, path: Path, seconds: float = 0.3, sample_rate: int = 16000) -> None:
        frames = int(seconds * sample_rate)
        payload = bytearray()
        for i in range(frames):
            value = int(0.4 * 32767.0 * math.sin((2.0 * math.pi * 440.0 * i) / sample_rate))
            payload.extend(struct.pack("<h", value))
        with wave.open(str(path), "wb") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(sample_rate)
            handle.writeframes(bytes(payload))

    def test_extract_audio_features_writes_npy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_audio = root / "input.wav"
            output_npy = root / "audio_features.npy"
            self.write_sine_wav(input_audio)

            rows = extract_audio_features(input_audio, output_npy)
            self.assertTrue(output_npy.is_file())
            shape = parse_npy_shape(output_npy)
            self.assertEqual(shape[1], 3)
            self.assertGreater(rows, 0)
            self.assertEqual(rows, shape[0])

    def test_build_mouth_landmarks_writes_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            image = root / "face.png"
            output_json = root / "mouth_landmarks.json"
            image.write_bytes(TINY_PNG)

            count = build_mouth_landmarks(image, output_json, frame_count=8)
            self.assertEqual(count, 8)
            payload = json.loads(output_json.read_text(encoding="utf-8"))
            self.assertEqual(len(payload), 8)
            self.assertEqual(payload[0]["frame_index"], 0)
            self.assertEqual(len(payload[0]["points"]), 4)

    def test_get_image_size_png(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "face.png"
            path.write_bytes(TINY_PNG)
            size = get_image_size(path)
            self.assertEqual(size, (1, 1))


if __name__ == "__main__":
    unittest.main()

