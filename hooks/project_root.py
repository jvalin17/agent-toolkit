"""Resolve git project root — independent of shell cwd."""

from __future__ import annotations

import subprocess
from pathlib import Path


def resolve_project_root(
    start: Path | None = None,
    hint: Path | None = None,
) -> Path:
    """Return the project root for gates.json / tests / reports.

    Resolution order:
    1. Parent of ``.scratch/`` in *hint* (e.g. findings.json path)
    2. ``git rev-parse --show-toplevel`` from *start*
    3. Nearest ancestor of *start* containing ``gates.json``
    4. *start* or ``Path.cwd()``
    """
    if hint is not None:
        from_scratch = _root_from_scratch(hint)
        if from_scratch is not None:
            return from_scratch

    base = (start or Path.cwd()).resolve()

    git_root = _git_toplevel(base)
    if git_root is not None:
        return git_root

    gates_root = _find_gates_json_ancestor(base)
    if gates_root is not None:
        return gates_root

    return base


def _root_from_scratch(path: Path) -> Path | None:
    resolved = path.resolve()
    parts = resolved.parts
    if ".scratch" not in parts:
        return None
    idx = parts.index(".scratch")
    if idx == 0:
        return None
    return Path(*parts[:idx])


def _git_toplevel(start: Path) -> Path | None:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=start,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    root = proc.stdout.strip()
    if not root:
        return None
    return Path(root).resolve()


def _find_gates_json_ancestor(start: Path) -> Path | None:
    current = start
    for _ in range(25):
        if (current / "gates.json").is_file():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    return None
