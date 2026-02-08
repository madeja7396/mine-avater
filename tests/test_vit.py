from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pipeline.vit import compute_mock_vit_conditioning, resolve_vit_conditioning

TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x04\x00\x00\x00\xb5\x1c\x0c\x02\x00\x00\x00\x0bIDATx\xdac\xfc\xff"
    b"\x0f\x00\x02\x03\x01\x02\x9fV\x8fd\x00\x00\x00\x00IEND\xaeB`\x82"
)


class VitTest(unittest.TestCase):
    def test_mock_vit_conditioning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            image = Path(tmp_dir) / "face.png"
            image.write_bytes(TINY_PNG)
            result = compute_mock_vit_conditioning(image, width=128, height=128, patch_size=16)
            self.assertEqual(result.backend_used, "vit-mock")
            self.assertTrue(0.5 <= result.conditioning.mouth_gain <= 1.5)
            self.assertEqual(result.details["reference_count"], 1.0)

    def test_mock_vit_conditioning_multi_view(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            image = Path(tmp_dir) / "face.png"
            side = Path(tmp_dir) / "side.png"
            image.write_bytes(TINY_PNG)
            side.write_bytes(TINY_PNG)
            result = compute_mock_vit_conditioning(
                image,
                width=128,
                height=128,
                patch_size=16,
                reference_images=[side],
            )
            self.assertEqual(result.backend_used, "vit-mock")
            self.assertEqual(result.details["reference_count"], 2.0)

    def test_resolve_heuristic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            image = Path(tmp_dir) / "face.png"
            image.write_bytes(TINY_PNG)
            result = resolve_vit_conditioning(
                reference_image=image,
                width=128,
                height=128,
                backend="heuristic",
                patch_size=16,
                image_size=224,
                fallback_mock=True,
                model_name="google/vit-base-patch16-224",
                use_pretrained=False,
                device="cpu",
            )
            self.assertEqual(result.backend_used, "heuristic")

    def test_unknown_backend_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            image = Path(tmp_dir) / "face.png"
            image.write_bytes(TINY_PNG)
            with self.assertRaises(ValueError):
                resolve_vit_conditioning(
                    reference_image=image,
                    width=128,
                    height=128,
                    backend="unknown",
                    patch_size=16,
                    image_size=224,
                    fallback_mock=True,
                    model_name="google/vit-base-patch16-224",
                    use_pretrained=False,
                    device="cpu",
                )


if __name__ == "__main__":
    unittest.main()
