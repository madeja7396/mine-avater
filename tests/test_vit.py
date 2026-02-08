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

    def test_resolve_heuristic_with_spatial_params(self) -> None:
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
                spatial_params={"yaw": 0.8, "pitch": -0.5, "depth": 0.6},
                spatial_weight=1.0,
            )
            self.assertEqual(result.backend_used, "heuristic")
            self.assertEqual(result.details["spatial_3d_applied"], "true")
            self.assertGreater(result.conditioning.face_shift_x, 0.0)
            self.assertLess(result.conditioning.face_shift_y, 0.0)
            self.assertGreater(result.conditioning.mouth_gain, 1.0)
            self.assertGreater(result.conditioning.tone_shift, 0.0)

    def test_resolve_heuristic_with_phase4_controls(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            image = Path(tmp_dir) / "face.png"
            image.write_bytes(TINY_PNG)
            base = resolve_vit_conditioning(
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
                spatial_params={"yaw": 0.8, "pitch": -0.5, "depth": 0.6},
                spatial_weight=1.0,
            )
            tuned = resolve_vit_conditioning(
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
                spatial_params={"yaw": 0.8, "pitch": -0.5, "depth": 0.6},
                spatial_weight=1.0,
                enable_reference_augmentation=True,
                augmentation_copies=3,
                augmentation_strength=0.4,
                overfit_guard_strength=0.5,
            )
            self.assertEqual(tuned.details["phase4_aug_applied"], "true")
            self.assertEqual(tuned.details["phase4_aug_copies"], 3.0)
            self.assertEqual(tuned.details["phase4_overfit_guard_strength"], 0.5)
            self.assertGreaterEqual(float(tuned.details["phase4_aug_virtual_rows"]), 3.0)
            self.assertLess(abs(tuned.conditioning.face_shift_x), abs(base.conditioning.face_shift_x))
            self.assertLess(abs(tuned.conditioning.tone_shift), abs(base.conditioning.tone_shift))


if __name__ == "__main__":
    unittest.main()
