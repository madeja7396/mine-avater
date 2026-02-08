from __future__ import annotations

import contextlib
import io
import unittest

from ci.monitor_ci import (
    MonitorOptions,
    evaluate_exit,
    parse_repo_from_remote,
    summarize_run,
)


class MonitorCITest(unittest.TestCase):
    def test_parse_repo_from_remote_https(self) -> None:
        self.assertEqual(
            parse_repo_from_remote("https://github.com/madeja7396/mine-avater.git"),
            "madeja7396/mine-avater",
        )

    def test_parse_repo_from_remote_ssh(self) -> None:
        self.assertEqual(
            parse_repo_from_remote("git@github.com:madeja7396/mine-avater.git"),
            "madeja7396/mine-avater",
        )

    def test_parse_repo_from_remote_invalid(self) -> None:
        self.assertIsNone(parse_repo_from_remote("https://example.com/repo.git"))

    def test_summarize_run(self) -> None:
        run = {
            "id": 123,
            "name": "CI",
            "status": "completed",
            "conclusion": "success",
            "event": "push",
            "head_branch": "main",
            "head_sha": "abcdef",
            "html_url": "https://github.com",
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:10:00Z",
        }
        summary = summarize_run(run)
        self.assertEqual(summary["id"], "123")
        self.assertEqual(summary["conclusion"], "success")

    def test_evaluate_exit_require_success(self) -> None:
        opts = MonitorOptions(
            repo="madeja7396/mine-avater",
            branch="main",
            workflow="CI",
            event=None,
            per_page=20,
            token=None,
            watch=False,
            interval=60,
            max_iterations=30,
            until_complete=False,
            require_success=True,
            include_jobs=False,
        )
        summary_ok = {"status": "completed", "conclusion": "success"}
        summary_fail = {"status": "completed", "conclusion": "failure"}
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(evaluate_exit(opts, summary_ok), 0)
            self.assertEqual(evaluate_exit(opts, summary_fail), 1)


if __name__ == "__main__":
    unittest.main()
