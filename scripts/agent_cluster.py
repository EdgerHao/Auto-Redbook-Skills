#!/usr/bin/env python3
"""Lightweight agent cluster orchestration for git worktree + tmux based coding agents.

This script implements a deterministic control loop:
- task registry stored in JSON
- objective status checks (tmux alive, git branch, PR existence)
- bounded retries for failed tasks
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = ROOT / "agent-cluster"
TASKS_FILE = STATE_DIR / "tasks.json"


@dataclass
class Task:
    id: str
    repo: str
    worktree: str
    branch: str
    agent: str
    model: str
    description: str
    tmux_session: str
    status: str
    retries: int
    max_retries: int
    notify_on_complete: bool
    started_at: int
    updated_at: int
    pr_url: str | None = None
    last_error: str | None = None


def now_ms() -> int:
    return int(time.time() * 1000)


def _run(cmd: list[str], cwd: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False)


def ensure_state() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    if not TASKS_FILE.exists():
        TASKS_FILE.write_text("[]\n", encoding="utf-8")


def load_tasks() -> list[Task]:
    ensure_state()
    raw = json.loads(TASKS_FILE.read_text(encoding="utf-8"))
    return [Task(**item) for item in raw]


def save_tasks(tasks: list[Task]) -> None:
    TASKS_FILE.write_text(json.dumps([asdict(t) for t in tasks], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def get_task(tasks: list[Task], task_id: str) -> Task:
    for task in tasks:
        if task.id == task_id:
            return task
    raise SystemExit(f"Task not found: {task_id}")


def check_tmux(session: str) -> bool:
    res = _run(["tmux", "has-session", "-t", session])
    return res.returncode == 0


def find_pr_url(worktree: str) -> str | None:
    # gh may be unavailable; treat as optional status signal.
    res = _run(["gh", "pr", "view", "--json", "url", "-q", ".url"], cwd=worktree)
    if res.returncode == 0:
        out = res.stdout.strip()
        return out or None
    return None


def add_task(args: argparse.Namespace) -> None:
    tasks = load_tasks()
    if any(t.id == args.id for t in tasks):
        raise SystemExit(f"Task id already exists: {args.id}")

    worktree = str((Path(args.worktree_root) / args.id).resolve())
    branch = args.branch or f"feat/{args.id}"

    wt = _run(["git", "worktree", "add", worktree, "-b", branch, args.base], cwd=args.repo)
    if wt.returncode != 0:
        raise SystemExit(f"git worktree add failed:\n{wt.stderr}")

    task = Task(
        id=args.id,
        repo=str(Path(args.repo).resolve()),
        worktree=worktree,
        branch=branch,
        agent=args.agent,
        model=args.model,
        description=args.description,
        tmux_session=args.tmux_session,
        status="running",
        retries=0,
        max_retries=args.max_retries,
        notify_on_complete=not args.no_notify,
        started_at=now_ms(),
        updated_at=now_ms(),
    )
    tasks.append(task)
    save_tasks(tasks)
    print(json.dumps(asdict(task), ensure_ascii=False, indent=2))


def list_tasks(_: argparse.Namespace) -> None:
    tasks = load_tasks()
    out: list[dict[str, Any]] = []
    for t in tasks:
        out.append(
            {
                "id": t.id,
                "status": t.status,
                "agent": t.agent,
                "model": t.model,
                "worktree": t.worktree,
                "branch": t.branch,
                "pr_url": t.pr_url,
                "retries": f"{t.retries}/{t.max_retries}",
                "updated": datetime.fromtimestamp(t.updated_at / 1000, tz=timezone.utc).isoformat(),
            }
        )
    print(json.dumps(out, ensure_ascii=False, indent=2))


def monitor(args: argparse.Namespace) -> None:
    tasks = load_tasks()
    changed = False
    for task in tasks:
        if task.status in {"done", "failed"}:
            continue

        alive = check_tmux(task.tmux_session)
        pr_url = find_pr_url(task.worktree)
        task.pr_url = pr_url or task.pr_url

        if alive:
            task.status = "running"
            task.last_error = None
        else:
            # If tmux ended and PR exists, task is considered done.
            if task.pr_url:
                task.status = "done"
            else:
                task.retries += 1
                if task.retries > task.max_retries:
                    task.status = "failed"
                    task.last_error = "agent session ended without PR"
                else:
                    task.status = "needs-restart"
                    task.last_error = "agent session ended"

        task.updated_at = now_ms()
        changed = True

    if changed:
        save_tasks(tasks)

    if args.json:
        print(json.dumps([asdict(t) for t in tasks], ensure_ascii=False, indent=2))
    else:
        for t in tasks:
            print(f"{t.id:28} {t.status:14} pr={t.pr_url or '-'} retries={t.retries}/{t.max_retries}")


def mark(args: argparse.Namespace) -> None:
    tasks = load_tasks()
    task = get_task(tasks, args.id)
    task.status = args.status
    task.updated_at = now_ms()
    save_tasks(tasks)
    print(f"{task.id} -> {task.status}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Agent cluster controller")
    sub = p.add_subparsers(dest="command", required=True)

    add = sub.add_parser("add", help="Create a task and git worktree")
    add.add_argument("--id", required=True)
    add.add_argument("--repo", default=str(ROOT))
    add.add_argument("--worktree-root", default=str((ROOT.parent / "worktrees").resolve()))
    add.add_argument("--base", default="origin/main")
    add.add_argument("--branch")
    add.add_argument("--agent", default="codex")
    add.add_argument("--model", default="gpt-5.3-codex")
    add.add_argument("--description", required=True)
    add.add_argument("--tmux-session", required=True)
    add.add_argument("--max-retries", type=int, default=3)
    add.add_argument("--no-notify", action="store_true")
    add.set_defaults(func=add_task)

    ls = sub.add_parser("list", help="List task registry")
    ls.set_defaults(func=list_tasks)

    mon = sub.add_parser("monitor", help="Run deterministic status checks")
    mon.add_argument("--json", action="store_true")
    mon.set_defaults(func=monitor)

    mk = sub.add_parser("mark", help="Manually mark task status")
    mk.add_argument("--id", required=True)
    mk.add_argument("--status", required=True, choices=["running", "needs-restart", "done", "failed", "paused"])
    mk.set_defaults(func=mark)

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
