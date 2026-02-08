from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


class CICheckScriptsTest(unittest.TestCase):
    def run_cmd(self, script: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, script],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_check_scaffold_passes(self) -> None:
        result = self.run_cmd("ci/check_scaffold.py")
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("METRIC: scaffold_valid", result.stdout)

    def test_check_eval_assets_passes(self) -> None:
        result = self.run_cmd("ci/check_eval_assets.py")
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("METRIC: eval_assets_valid", result.stdout)

    def test_check_project_skills_passes(self) -> None:
        result = self.run_cmd("ci/check_project_skills.py")
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("METRIC: project_skills_valid", result.stdout)


if __name__ == "__main__":
    unittest.main()
