from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


class TaskLockTest(unittest.TestCase):
    def run_cmd(self, *args: str, task_dir: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "harness/task_lock.py", *args, "--dir", str(task_dir)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_acquire_and_release(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            task_dir = Path(tmp_dir)
            acquired = self.run_cmd(
                "acquire", "mouth_roi_stabilize", "agent-01", task_dir=task_dir
            )
            self.assertEqual(acquired.returncode, 0, msg=acquired.stdout + acquired.stderr)

            second = self.run_cmd(
                "acquire", "mouth_roi_stabilize", "agent-02", task_dir=task_dir
            )
            self.assertNotEqual(second.returncode, 0)
            self.assertIn("ERROR: lock_exists", second.stdout)

            wrong_release = self.run_cmd(
                "release", "mouth_roi_stabilize", "agent-02", task_dir=task_dir
            )
            self.assertNotEqual(wrong_release.returncode, 0)
            self.assertIn("ERROR: lock_owner_mismatch", wrong_release.stdout)

            released = self.run_cmd(
                "release", "mouth_roi_stabilize", "agent-01", task_dir=task_dir
            )
            self.assertEqual(released.returncode, 0, msg=released.stdout + released.stderr)

    def test_reap_expired_lock(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            task_dir = Path(tmp_dir)
            acquired = self.run_cmd(
                "acquire",
                "post_denoise",
                "agent-03",
                "--ttl-minutes",
                "0",
                task_dir=task_dir,
            )
            self.assertEqual(acquired.returncode, 0, msg=acquired.stdout + acquired.stderr)

            reaped = self.run_cmd("reap", task_dir=task_dir)
            self.assertEqual(reaped.returncode, 0, msg=reaped.stdout + reaped.stderr)
            self.assertIn("METRIC: lock_reap removed=1", reaped.stdout)


if __name__ == "__main__":
    unittest.main()
