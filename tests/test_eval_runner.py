from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


class EvalRunnerTest(unittest.TestCase):
    def run_cmd(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "ci/eval_runner.py", *args],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_fast_mode_passes(self) -> None:
        result = self.run_cmd("--mode", "fast")
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("METRIC: mode=fast passed", result.stdout)

    def test_failure_case_returns_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            payload = {
                "thresholds": {
                    "lipsync_mae_max": 0.12,
                    "mouth_breakage_rate_max": 0.05,
                    "temporal_jump_max": 0.08,
                    "psnr_min": 30.0,
                    "ssim_min": 0.93,
                    "oom_rate_max": 0.01,
                    "failure_rate_max": 0.02,
                    "throughput_fps_min": 12.0,
                },
                "aggregate": {
                    "oom_rate": 0.0,
                    "failure_rate": 0.0,
                    "throughput_fps": 20.0,
                },
                "samples": [
                    {
                        "id": "bad_001",
                        "lipsync_mae": 0.5,
                        "mouth_breakage_rate": 0.01,
                        "temporal_jump": 0.01,
                        "psnr": 40.0,
                        "ssim": 0.99,
                    }
                ],
            }
            file_path = Path(tmp_dir) / "bad.json"
            file_path.write_text(json.dumps(payload), encoding="utf-8")

            result = self.run_cmd("--mode", "fast", "--file", str(file_path))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("ERROR: mode=fast failed", result.stdout)

    def test_threshold_mismatch_returns_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            payload = {
                "thresholds": {
                    "lipsync_mae_max": 0.99,
                    "mouth_breakage_rate_max": 0.05,
                    "temporal_jump_max": 0.08,
                    "psnr_min": 30.0,
                    "ssim_min": 0.93,
                    "oom_rate_max": 0.01,
                    "failure_rate_max": 0.02,
                    "throughput_fps_min": 12.0,
                },
                "aggregate": {
                    "oom_rate": 0.0,
                    "failure_rate": 0.0,
                    "throughput_fps": 20.0,
                },
                "samples": [
                    {
                        "id": "sample_001",
                        "lipsync_mae": 0.08,
                        "mouth_breakage_rate": 0.01,
                        "temporal_jump": 0.01,
                        "psnr": 40.0,
                        "ssim": 0.99,
                    }
                ],
            }
            file_path = Path(tmp_dir) / "bad_thresholds.json"
            file_path.write_text(json.dumps(payload), encoding="utf-8")

            result = self.run_cmd("--mode", "fast", "--file", str(file_path))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("ERROR: thresholds mismatch", result.stdout)


if __name__ == "__main__":
    unittest.main()
