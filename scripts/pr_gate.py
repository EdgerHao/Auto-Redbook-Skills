#!/usr/bin/env python3
"""Simple PR gate checker.

Checks objective merge readiness signals and outputs PASS/BLOCK + reasons.
Designed for deterministic, low-token monitoring loops.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from typing import Any


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, capture_output=True, check=False)


def gh_json(args: list[str], repo: str | None = None) -> Any | None:
    cmd = ["gh"]
    if repo:
        cmd.extend(["-R", repo])
    cmd.extend(args)
    res = run(cmd)
    if res.returncode != 0:
        return None
    try:
        return json.loads(res.stdout)
    except json.JSONDecodeError:
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Check PR merge gate")
    parser.add_argument("pr", help="PR number or URL")
    parser.add_argument("--repo", help="owner/repo, e.g. EdgerHao/Auto-Redbook-Skills")
    args = parser.parse_args()

    data = gh_json(["pr", "view", args.pr, "--json", "url,state,isDraft,reviewDecision,statusCheckRollup,title"], repo=args.repo)
    if not data:
        print(json.dumps({"result": "BLOCK", "reasons": ["gh pr view failed"]}, ensure_ascii=False))
        raise SystemExit(1)

    reasons: list[str] = []

    if data.get("state") != "OPEN":
        reasons.append("PR is not OPEN")
    if data.get("isDraft"):
        reasons.append("PR is draft")

    decision = data.get("reviewDecision")
    if decision not in {"APPROVED", None, ""}:
        reasons.append(f"Review decision: {decision}")

    checks = data.get("statusCheckRollup") or []
    failed = [c for c in checks if (c.get("conclusion") not in {"SUCCESS", "SKIPPED", None})]
    pending = [c for c in checks if c.get("status") in {"IN_PROGRESS", "QUEUED", "PENDING"}]
    if failed:
        reasons.append(f"Failed checks: {len(failed)}")
    if pending:
        reasons.append(f"Pending checks: {len(pending)}")

    result = "PASS" if not reasons else "BLOCK"
    print(
        json.dumps(
            {
                "result": result,
                "url": data.get("url"),
                "title": data.get("title"),
                "reasons": reasons,
            },
            ensure_ascii=False,
        )
    )

    if result == "BLOCK":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
