"""gates.json discovery and loading — stdlib only.

Single source of truth for *where* gates.json lives and *how* it is read.
Used by hooks (gate_hook, mode_resolver callers), signed-gate scripts
(gate/core.py) and CI (scripts/ci-generate-reports.py). Keep this module
free of third-party imports so hooks can load it without PyJWT installed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

# Search order, relative to the project root.
GATES_CANDIDATES = ("gates.json", ".claude/gates.json", "hooks/gates.json")


class GatesConfigError(ValueError):
    """gates.json exists but cannot be used — gates must fail closed."""


def find_gates_config(project_root: Path) -> Optional[Path]:
    """Return the first existing gates.json candidate, or None."""
    for relative in GATES_CANDIDATES:
        candidate = Path(project_root) / relative
        if candidate.is_file():
            return candidate
    return None


def load_gates_config(project_root: Path) -> Optional[dict[str, Any]]:
    """Load gates.json. Returns None when no file exists.

    Raises GatesConfigError when the file exists but is empty, not JSON, or
    not a JSON object. Callers must treat that as a blocking condition, never
    as "use defaults" — a corrupt policy file must not silently weaken gates.
    """
    path = find_gates_config(project_root)
    if path is None:
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise GatesConfigError(f"{path}: cannot read ({exc})") from exc
    if not text.strip():
        raise GatesConfigError(f"{path}: file is empty")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise GatesConfigError(f"{path}: invalid JSON at line {exc.lineno}: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise GatesConfigError(f"{path}: top level must be a JSON object")
    return data
