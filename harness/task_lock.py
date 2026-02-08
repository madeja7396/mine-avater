from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class LockFiles:
    lock: Path
    meta: Path


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_timestamp(raw: str) -> datetime:
    parsed = datetime.fromisoformat(raw)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def build_lock_files(task_dir: Path, task: str) -> LockFiles:
    return LockFiles(
        lock=task_dir / f"{task}.lock",
        meta=task_dir / f"{task}.lock.meta",
    )


def load_meta(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def is_expired(meta: dict[str, Any], now: datetime | None = None) -> bool:
    now = now or utc_now()
    try:
        timestamp = parse_timestamp(str(meta.get("timestamp", "")))
        ttl_minutes = int(meta.get("ttl_minutes", 0))
    except (TypeError, ValueError):
        return False
    expires_at = timestamp + timedelta(minutes=ttl_minutes)
    return now >= expires_at


def remove_lock_files(files: LockFiles) -> None:
    if files.lock.exists():
        files.lock.unlink()
    if files.meta.exists():
        files.meta.unlink()


def acquire(args: argparse.Namespace) -> int:
    task_dir = Path(args.dir)
    task_dir.mkdir(parents=True, exist_ok=True)
    files = build_lock_files(task_dir, args.task)

    for _ in range(2):
        try:
            fd = os.open(files.lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
        except FileExistsError:
            meta = load_meta(files.meta)
            if meta and is_expired(meta):
                remove_lock_files(files)
                continue
            owner = meta.get("owner", "unknown") if meta else "unknown"
            print(f"ERROR: lock_exists task={args.task} owner={owner}")
            return 1

        now = utc_now().isoformat()
        files.meta.write_text(
            json.dumps(
                {
                    "task": args.task,
                    "owner": args.owner,
                    "timestamp": now,
                    "ttl_minutes": args.ttl_minutes,
                },
                ensure_ascii=True,
                indent=2,
            ),
            encoding="utf-8",
        )
        print(
            f"METRIC: lock_acquired task={args.task} owner={args.owner} "
            f"ttl_minutes={args.ttl_minutes}"
        )
        return 0

    print(f"ERROR: lock_acquire_failed task={args.task}")
    return 1


def release(args: argparse.Namespace) -> int:
    task_dir = Path(args.dir)
    files = build_lock_files(task_dir, args.task)
    meta = load_meta(files.meta) or {}
    lock_owner = str(meta.get("owner", "unknown"))

    if not files.lock.exists():
        print(f"WARN: lock_not_found task={args.task}")
        return 0

    if not args.force and lock_owner not in ("unknown", args.owner):
        print(
            f"ERROR: lock_owner_mismatch task={args.task} "
            f"owner={lock_owner} requested_by={args.owner}"
        )
        return 1

    remove_lock_files(files)
    print(f"METRIC: lock_released task={args.task} owner={args.owner}")
    return 0


def status(args: argparse.Namespace) -> int:
    task_dir = Path(args.dir)
    files = build_lock_files(task_dir, args.task)
    meta = load_meta(files.meta) or {}

    if not files.lock.exists():
        print(f"METRIC: lock_free task={args.task}")
        return 0

    owner = meta.get("owner", "unknown")
    timestamp = meta.get("timestamp", "unknown")
    ttl_minutes = meta.get("ttl_minutes", "unknown")
    expired = is_expired(meta) if meta else False
    print(
        f"METRIC: lock_held task={args.task} owner={owner} "
        f"timestamp={timestamp} ttl_minutes={ttl_minutes} expired={str(expired).lower()}"
    )
    return 0


def reap(args: argparse.Namespace) -> int:
    task_dir = Path(args.dir)
    task_dir.mkdir(parents=True, exist_ok=True)
    now = utc_now()
    removed = 0

    for meta_path in task_dir.glob("*.lock.meta"):
        meta = load_meta(meta_path)
        if not meta:
            continue
        if not is_expired(meta, now=now):
            continue

        task_name = meta_path.name[:-10]
        files = build_lock_files(task_dir, task_name)
        remove_lock_files(files)
        removed += 1

    print(f"METRIC: lock_reap removed={removed}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Task lock helper.")
    sub = parser.add_subparsers(dest="command", required=True)

    base = argparse.ArgumentParser(add_help=False)
    base.add_argument("--dir", default="current_tasks")

    p_acquire = sub.add_parser("acquire", parents=[base])
    p_acquire.add_argument("task")
    p_acquire.add_argument("owner")
    p_acquire.add_argument("--ttl-minutes", type=int, default=120)
    p_acquire.set_defaults(func=acquire)

    p_release = sub.add_parser("release", parents=[base])
    p_release.add_argument("task")
    p_release.add_argument("owner")
    p_release.add_argument("--force", action="store_true")
    p_release.set_defaults(func=release)

    p_status = sub.add_parser("status", parents=[base])
    p_status.add_argument("task")
    p_status.set_defaults(func=status)

    p_reap = sub.add_parser("reap", parents=[base])
    p_reap.set_defaults(func=reap)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
