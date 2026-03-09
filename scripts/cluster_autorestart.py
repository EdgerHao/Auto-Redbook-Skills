#!/usr/bin/env python3
"""Auto-restart helper for agent-cluster tasks.

Policy:
- read task registry
- for tasks in `needs-restart` and within retry budget, relaunch tmux session
- mark task back to running
"""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TASKS = ROOT / "agent-cluster" / "tasks.json"


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, capture_output=True, check=False)


def now_ms() -> int:
    return int(time.time() * 1000)


def main() -> None:
    if not TASKS.exists():
        print(json.dumps({"restarted": [], "errors": ["tasks.json not found"]}, ensure_ascii=False))
        return

    tasks = json.loads(TASKS.read_text(encoding="utf-8"))
    restarted: list[dict[str, str]] = []
    errors: list[str] = []

    for t in tasks:
        status = t.get("status")
        retries = int(t.get("retries", 0))
        max_retries = int(t.get("max_retries", 3))
        session = t.get("tmux_session")
        worktree = t.get("worktree")
        task_id = t.get("id")

        if status != "needs-restart":
            continue
        if retries > max_retries:
            continue
        if not session or not worktree:
            errors.append(f"{task_id}: missing tmux_session/worktree")
            continue

        # Relaunch with a safe placeholder runner. Replace with your real agent command when needed.
        launch = run([
            "tmux",
            "new-session",
            "-d",
            "-s",
            session,
            "-c",
            worktree,
            "bash -lc 'echo restarted-$(date +%s) >> .agent_restarts && sleep 1200'",
        ])
        if launch.returncode != 0:
            errors.append(f"{task_id}: restart failed: {launch.stderr.strip()}")
            continue

        t["status"] = "running"
        t["updated_at"] = now_ms()
        t["last_error"] = None
        restarted.append({"id": task_id, "session": session})

    TASKS.write_text(json.dumps(tasks, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"restarted": restarted, "errors": errors}, ensure_ascii=False))


if __name__ == "__main__":
    main()
