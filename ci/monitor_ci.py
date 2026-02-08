from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


API_BASE = "https://api.github.com"


@dataclass(frozen=True)
class MonitorOptions:
    repo: str
    branch: str
    workflow: str | None
    event: str | None
    per_page: int
    token: str | None
    watch: bool
    interval: int
    max_iterations: int
    until_complete: bool
    require_success: bool
    include_jobs: bool


def detect_repo_from_origin() -> str | None:
    result = subprocess.run(
        ["git", "config", "--get", "remote.origin.url"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return parse_repo_from_remote(result.stdout.strip())


def parse_repo_from_remote(remote: str) -> str | None:
    if not remote:
        return None
    remote = remote.strip()
    if remote.startswith("git@github.com:"):
        path = remote.split(":", 1)[1]
    elif remote.startswith("https://github.com/") or remote.startswith("http://github.com/"):
        path = urllib.parse.urlparse(remote).path.lstrip("/")
    else:
        return None
    if path.endswith(".git"):
        path = path[:-4]
    parts = [p for p in path.split("/") if p]
    if len(parts) < 2:
        return None
    return f"{parts[0]}/{parts[1]}"


def github_get_json(url: str, token: str | None) -> dict[str, Any]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "mine-avater-ci-monitor",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API error status={exc.code} body={body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"GitHub API connection error: {exc}") from exc


def fetch_workflow_runs(opts: MonitorOptions) -> list[dict[str, Any]]:
    query = {
        "branch": opts.branch,
        "per_page": str(opts.per_page),
    }
    if opts.event:
        query["event"] = opts.event
    url = f"{API_BASE}/repos/{opts.repo}/actions/runs?{urllib.parse.urlencode(query)}"
    payload = github_get_json(url, token=opts.token)
    runs = payload.get("workflow_runs", [])
    if not isinstance(runs, list):
        return []
    if opts.workflow:
        workflow_name = opts.workflow.lower()
        runs = [r for r in runs if str(r.get("name", "")).lower() == workflow_name]
    return runs


def fetch_run_jobs(opts: MonitorOptions, run_id: int) -> list[dict[str, Any]]:
    url = f"{API_BASE}/repos/{opts.repo}/actions/runs/{run_id}/jobs?per_page=100"
    payload = github_get_json(url, token=opts.token)
    jobs = payload.get("jobs", [])
    if isinstance(jobs, list):
        return jobs
    return []


def summarize_run(run: dict[str, Any]) -> dict[str, str]:
    return {
        "id": str(run.get("id", "")),
        "name": str(run.get("name", "")),
        "status": str(run.get("status", "")),
        "conclusion": str(run.get("conclusion", "")),
        "event": str(run.get("event", "")),
        "branch": str(run.get("head_branch", "")),
        "sha": str(run.get("head_sha", "")),
        "url": str(run.get("html_url", "")),
        "created_at": str(run.get("created_at", "")),
        "updated_at": str(run.get("updated_at", "")),
    }


def print_run_summary(summary: dict[str, str]) -> None:
    print(
        "METRIC: ci_latest "
        f"id={summary['id']} "
        f"name={summary['name']} "
        f"status={summary['status']} "
        f"conclusion={summary['conclusion']} "
        f"branch={summary['branch']} "
        f"event={summary['event']}"
    )
    print(f"METRIC: ci_latest_url {summary['url']}")
    print(f"METRIC: ci_latest_sha {summary['sha']}")
    print(f"METRIC: ci_latest_updated_at {summary['updated_at']}")


def print_jobs(jobs: list[dict[str, Any]]) -> None:
    if not jobs:
        print("WARN: ci_jobs_empty")
        return
    for job in jobs:
        print(
            "METRIC: ci_job "
            f"name={job.get('name','')} "
            f"status={job.get('status','')} "
            f"conclusion={job.get('conclusion','')}"
        )


def evaluate_exit(opts: MonitorOptions, summary: dict[str, str]) -> int:
    if not opts.require_success:
        return 0
    status = summary.get("status", "")
    conclusion = summary.get("conclusion", "")
    if status != "completed":
        print(f"ERROR: ci_not_completed status={status}")
        return 1
    if conclusion != "success":
        print(f"ERROR: ci_not_success conclusion={conclusion}")
        return 1
    return 0


def run_once(opts: MonitorOptions) -> int:
    try:
        runs = fetch_workflow_runs(opts)
    except RuntimeError as exc:
        print(f"ERROR: ci_monitor_fetch_failed {exc}")
        if "status=404" in str(exc) and not opts.token:
            print("WARN: set GITHUB_TOKEN if the repository is private")
        return 2
    if not runs:
        print("ERROR: ci_runs_not_found")
        return 1
    latest = runs[0]
    summary = summarize_run(latest)
    print_run_summary(summary)
    if opts.include_jobs:
        try:
            jobs = fetch_run_jobs(opts, int(summary["id"]))
        except RuntimeError as exc:
            print(f"WARN: ci_jobs_fetch_failed {exc}")
            jobs = []
        print_jobs(jobs)
    return evaluate_exit(opts, summary)


def run_watch(opts: MonitorOptions) -> int:
    iterations = 0
    while True:
        iterations += 1
        print(f"METRIC: ci_watch_iteration={iterations}")
        try:
            runs = fetch_workflow_runs(opts)
        except RuntimeError as exc:
            print(f"ERROR: ci_monitor_fetch_failed {exc}")
            if "status=404" in str(exc) and not opts.token:
                print("WARN: set GITHUB_TOKEN if the repository is private")
            return 2
        if not runs:
            print("ERROR: ci_runs_not_found")
            return 1
        latest = runs[0]
        summary = summarize_run(latest)
        print_run_summary(summary)
        if opts.include_jobs:
            try:
                jobs = fetch_run_jobs(opts, int(summary["id"]))
            except RuntimeError as exc:
                print(f"WARN: ci_jobs_fetch_failed {exc}")
                jobs = []
            print_jobs(jobs)

        status = summary["status"]
        done = (not opts.until_complete) or (status == "completed")
        if done:
            return evaluate_exit(opts, summary)
        if opts.max_iterations > 0 and iterations >= opts.max_iterations:
            print(f"ERROR: ci_watch_timeout iterations={iterations}")
            return 1
        time.sleep(opts.interval)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Monitor GitHub Actions CI runs.")
    parser.add_argument("--repo", default=None, help="owner/repo (auto-detect from origin if omitted)")
    parser.add_argument("--branch", default="main")
    parser.add_argument("--workflow", default="CI")
    parser.add_argument("--event", default=None)
    parser.add_argument("--per-page", type=int, default=20)
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--interval", type=int, default=60)
    parser.add_argument("--max-iterations", type=int, default=30)
    parser.add_argument("--until-complete", action="store_true")
    parser.add_argument("--require-success", action="store_true")
    parser.add_argument("--include-jobs", action="store_true")
    parser.add_argument("--token-env", default="GITHUB_TOKEN")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    repo = args.repo or detect_repo_from_origin()
    if not repo:
        print("ERROR: repo_not_found; pass --repo owner/repo")
        return 1

    token = os.environ.get(args.token_env)
    opts = MonitorOptions(
        repo=repo,
        branch=args.branch,
        workflow=args.workflow,
        event=args.event,
        per_page=max(1, args.per_page),
        token=token,
        watch=args.watch,
        interval=max(1, args.interval),
        max_iterations=max(0, args.max_iterations),
        until_complete=args.until_complete,
        require_success=args.require_success,
        include_jobs=args.include_jobs,
    )

    if opts.watch:
        return run_watch(opts)
    return run_once(opts)


if __name__ == "__main__":
    raise SystemExit(main())
