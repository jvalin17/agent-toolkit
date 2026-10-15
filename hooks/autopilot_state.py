"""State of a running /autopilot pipeline — shared by hooks and CLI gates.

/autopilot keeps its progress in ``.scratch/autopilot/state.json`` so a new
session, a compaction, or a distracted agent lands back on the current step
instead of starting over or drifting into ad-hoc edits. The file is agent
written by design (it lives under .scratch, which is never a protected path):
it can only make the gates stricter, never looser.

While the pipeline is active, pushing additionally requires a fresh
``precommit`` flag, on every host (Claude hook and ``scripts/atk.py``).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional, Tuple

STATE_RELATIVE = Path(".scratch") / "autopilot" / "state.json"
ACTIVE_STATUSES = frozenset({"running", "paused"})
PUSH_EXTRA_SKILL = "precommit"


def state_path(project_dir: Path) -> Path:
    return Path(project_dir) / STATE_RELATIVE


def read_state(project_dir: Path) -> Optional[dict]:
    """The parsed state file, or None when absent, malformed, or not a pipeline."""
    path = state_path(project_dir)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or not isinstance(data.get("steps"), list) or not data["steps"]:
        return None
    return data


def is_active(project_dir: Path) -> bool:
    state = read_state(project_dir)
    return bool(state) and state.get("status") in ACTIVE_STATUSES


def current_step(state: dict) -> Tuple[int, int, str]:
    """(1-based index, total, name) of the first step that is not done or skipped."""
    steps = state["steps"]
    for index, step in enumerate(steps, start=1):
        if isinstance(step, dict) and step.get("status") not in ("done", "skipped"):
            return index, len(steps), str(step.get("name", "?"))
    return len(steps), len(steps), str(steps[-1].get("name", "?")) if isinstance(steps[-1], dict) else "?"


def resume_context(state: dict) -> str:
    index, total, name = current_step(state)
    reason = state.get("reason")
    paused = f" Paused because: {reason}." if state.get("status") == "paused" and reason else ""
    return (
        f"AUTOPILOT ACTIVE — task: {state.get('task', '?')} (step {index}/{total}: {name}).{paused}\n"
        f"Continue the /autopilot pipeline from this step; do not edit code outside it and do not "
        f"skip to a later step. When the step is done, mark it in {STATE_RELATIVE} and move on. "
        f"If the user is changing the task, update the state file first."
    )


def push_requires(base: List[str], project_dir: Path) -> List[str]:
    """Push requirements for this project: the mode's list plus precommit while autopilot runs."""
    required = list(base)
    if is_active(project_dir) and PUSH_EXTRA_SKILL not in required:
        required.append(PUSH_EXTRA_SKILL)
    return required
