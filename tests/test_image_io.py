from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pipeline.image_io import load_rgb_image

TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x04\x00\x00\x00\xb5\x1c\x0c\x02\x00\x00\x00\x0bIDATx\xdac\xfc\xff"
    b"\x0f\x00\x02\x03\x01\x02\x9fV\x8fd\x00\x00\x00\x00IEND\xaeB`\x82"
)


class ImageIOTest(unittest.TestCase):
    def test_load_rgb_image_png_exact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            image = Path(tmp_dir) / "face.png"
            image.write_bytes(TINY_PNG)
            rgb = load_rgb_image(image, width=1, height=1)
            self.assertEqual(len(rgb), 3)

    def test_load_rgb_image_png_resize(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            image = Path(tmp_dir) / "face.png"
            image.write_bytes(TINY_PNG)
            rgb = load_rgb_image(image, width=8, height=8)
            self.assertEqual(len(rgb), 8 * 8 * 3)


if __name__ == "__main__":
    unittest.main()

