"""Shared session JSONL discovery.

Finds the latest Claude Code session log for the current project.
Used by compliance.py and finalize_report.py instead of duplicated logic.
"""

from pathlib import Path
from typing import Optional


def find_latest_session_log() -> Optional[Path]:
    """Find the latest .jsonl session log for the current working directory.

    Looks in ~/.claude/projects/ for a directory whose name exactly matches
    the cwd slug (path with / replaced by -).

    Returns the most-recently-modified .jsonl file, or None.
    """
    claude_projects = Path.home() / ".claude" / "projects"
    if not claude_projects.is_dir():
        return None

    cwd_slug = str(Path.cwd()).replace("/", "-").lstrip("-")
    project_dir = None
    for d in claude_projects.iterdir():
        if d.name == cwd_slug or d.name == f"-{cwd_slug}":
            project_dir = d
            break

    if not project_dir:
        return None

    logs = sorted(project_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime)
    if not logs:
        return None

    return logs[-1]
