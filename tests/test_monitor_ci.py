from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
import zipfile
from pathlib import Path

from ci.monitor_ci import (
    MonitorOptions,
    collect_failed_jobs,
    decode_log_payload,
    evaluate_exit,
    load_token_from_env_file,
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
            triage_on_failure=False,
            triage_script="skills/avatar-ci-guardian/scripts/triage_ci_log.py",
            triage_logs_dir="logs/ci_monitor",
            triage_max_jobs=10,
        )
        summary_ok = {"status": "completed", "conclusion": "success"}
        summary_fail = {"status": "completed", "conclusion": "failure"}
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(evaluate_exit(opts, summary_ok), 0)
            self.assertEqual(evaluate_exit(opts, summary_fail), 1)

    def test_collect_failed_jobs(self) -> None:
        jobs = [
            {"name": "a", "status": "completed", "conclusion": "success"},
            {"name": "b", "status": "completed", "conclusion": "failure"},
            {"name": "c", "status": "in_progress", "conclusion": None},
            {"name": "d", "status": "completed", "conclusion": "cancelled"},
        ]
        failed = collect_failed_jobs(jobs)
        self.assertEqual(len(failed), 2)
        self.assertEqual(failed[0]["name"], "b")
        self.assertEqual(failed[1]["name"], "d")

    def test_decode_log_payload_zip(self) -> None:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("job/1.txt", "ERROR: sample")
        text = decode_log_payload(buf.getvalue())
        self.assertIn("ERROR: sample", text)

    def test_load_token_from_env_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            p = Path(tmp_dir) / ".env.lock"
            p.write_text("GITHUB_TOKEN=abc123\nOTHER=value\n", encoding="utf-8")
            token = load_token_from_env_file(str(p), "GITHUB_TOKEN")
            self.assertEqual(token, "abc123")

    def test_load_token_from_env_file_export_and_comment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            p = Path(tmp_dir) / ".env.lock"
            p.write_text(
                "export GITHUB_TOKEN=abc123 # personal access token\n",
                encoding="utf-8",
            )
            token = load_token_from_env_file(str(p), "GITHUB_TOKEN")
            self.assertEqual(token, "abc123")


if __name__ == "__main__":
    unittest.main()
