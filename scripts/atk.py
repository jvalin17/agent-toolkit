#!/usr/bin/env python3
"""atk — foolproof CLI gates for hosts without structural hooks (Phase C).

Usage:
  python3 scripts/atk.py status [--project DIR]
  python3 scripts/atk.py commit -m "msg" [--project DIR]
  python3 scripts/atk.py push [--project DIR] [--] [git push args...]
  python3 scripts/atk.py git [--project DIR] -- <git args...>

`commit` / `push` refuse unless required .gates/*-passed flags contain READY.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

TOOLKIT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLKIT_ROOT / "hooks"))

from gate_hook import check_gate_flags, load_gate_config  # noqa: E402
from mode_resolver import resolve_mode_from_config  # noqa: E402


def _required_for(project_dir: Path, action: str) -> list:
    config = load_gate_config(project_dir)
    mode = resolve_mode_from_config(config)
    if action == "commit":
        return list(mode.commit_requires)
    return list(mode.push_requires)


def gate_ready(project_dir: Path, action: str) -> tuple:
    config = load_gate_config(project_dir)
    if config.get("_no_config"):
        return False, ["no gates.json — not a toolkit project"]
    required = _required_for(project_dir, action)
    if not required:
        return True, []
    threshold = config.get("eval_threshold", 95)
    missing = check_gate_flags(required, project_dir, threshold)
    return (len(missing) == 0), missing


def cmd_status(project_dir: Path) -> int:
    for action in ("commit", "push"):
        ok, missing = gate_ready(project_dir, action)
        print(f"{action}: {'READY' if ok else 'BLOCKED'}")
        if missing:
            print(f"  missing: {', '.join(missing)}")
    return 0


def cmd_commit(project_dir: Path, message: str, extra: list) -> int:
    ok, missing = gate_ready(project_dir, "commit")
    if not ok:
        print(
            f"atk: commit blocked — run missing skills first: {', '.join(missing)}",
            file=sys.stderr,
        )
        return 1
    args = ["git", "commit", "-m", message] + extra
    return subprocess.call(args, cwd=str(project_dir))


def cmd_push(project_dir: Path, extra: list) -> int:
    ok, missing = gate_ready(project_dir, "push")
    if not ok:
        print(
            f"atk: push blocked — run missing skills first: {', '.join(missing)}",
            file=sys.stderr,
        )
        return 1
    args = ["git", "push"] + extra
    return subprocess.call(args, cwd=str(project_dir))


def cmd_git(project_dir: Path, git_args: list) -> int:
    """Proxy git; intercept commit/push."""
    joined = " ".join(git_args)
    if "commit" in git_args:
        ok, missing = gate_ready(project_dir, "commit")
        if not ok:
            print(f"atk-git: commit blocked — {', '.join(missing)}", file=sys.stderr)
            return 1
    if "push" in git_args:
        ok, missing = gate_ready(project_dir, "push")
        if not ok:
            print(f"atk-git: push blocked — {', '.join(missing)}", file=sys.stderr)
            return 1
    return subprocess.call(["git"] + git_args, cwd=str(project_dir))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="atk")
    parser.add_argument("--project", default=".", help="Project directory")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status")

    p_commit = sub.add_parser("commit")
    p_commit.add_argument("-m", "--message", required=True)
    p_commit.add_argument("extra", nargs="*", default=[])

    p_push = sub.add_parser("push")
    p_push.add_argument("extra", nargs="*", default=[])

    p_git = sub.add_parser("git")
    p_git.add_argument("git_args", nargs=argparse.REMAINDER)

    args = parser.parse_args(argv)
    project = Path(args.project).resolve()

    if args.cmd == "status":
        return cmd_status(project)
    if args.cmd == "commit":
        return cmd_commit(project, args.message, args.extra)
    if args.cmd == "push":
        return cmd_push(project, args.extra)
    if args.cmd == "git":
        git_args = args.git_args
        if git_args and git_args[0] == "--":
            git_args = git_args[1:]
        return cmd_git(project, git_args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
