#!/usr/bin/env python3
"""Rule-based agent router for cluster tasks.

Given a task type, return recommended execution agent and model.
"""

from __future__ import annotations

import argparse
import json

ROUTES = {
    "backend": {"agent": "codex", "model": "gpt-5.3-codex", "reason": "Cross-file logic and robustness"},
    "bugfix": {"agent": "codex", "model": "gpt-5.3-codex", "reason": "Edge-case and failure handling"},
    "refactor": {"agent": "codex", "model": "gpt-5.3-codex", "reason": "High-context codebase reasoning"},
    "frontend": {"agent": "claude-code", "model": "claude-opus-4.5", "reason": "Fast UI iteration"},
    "ui-design": {"agent": "gemini", "model": "gemini-2.5-pro", "reason": "Strong layout/style ideation"},
    "docs": {"agent": "claude-code", "model": "claude-opus-4.5", "reason": "Fast content polish"},
}


def route(task_type: str) -> dict[str, str]:
    key = task_type.strip().lower()
    return ROUTES.get(key, {"agent": "codex", "model": "gpt-5.3-codex", "reason": "Default safe route"})


def main() -> None:
    parser = argparse.ArgumentParser(description="Route task types to recommended agents")
    parser.add_argument("task_type", help="backend|bugfix|refactor|frontend|ui-design|docs")
    args = parser.parse_args()
    print(json.dumps(route(args.task_type), ensure_ascii=False))


if __name__ == "__main__":
    main()
