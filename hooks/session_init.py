#!/usr/bin/env python3
"""Session init hook — SessionStart hook.

Runs on SessionStart. Responsibilities:
- Initialize .session/state.json (fresh counters)
- Scan project .md files (priority ordering)
- Hook integrity check
- Clear stale .gates/
- HANDOFF.md → inject continuation context

Single entry point: main() reads stdin JSON, outputs JSON response.
"""

import json
import os
import re
import shutil
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Ensure sibling modules are importable regardless of CWD
import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parent))

from session_monitor import SessionState, save_state

# --- Configuration ---

PRIORITY_FILES = ["HANDOFF.md", "project-state.md", "CLAUDE.md", "DECISIONS.md"]
SCAN_DIRS = ["requirements", "architecture"]
EXCLUDED_ROOT_FILES = {"README.md", "HANDOFF.md", "project-state.md", "CLAUDE.md", "DECISIONS.md"}

REQUIRED_HOOKS = [
    "gate.py", "skill_passed.py", "gate_cleanup.py",
    "route_to_skill.py", "session_init.py", "session_monitor.py",
    "tdd_enforce.py",
]

SETTINGS_CHECKED_HOOKS = ["gate.py", "session_monitor.py", "skill_passed.py"]

DEFAULT_MODE = "normal"


# --- Core functions ---


def detect_mode(project_dir: Path) -> str:
    """Detect agent toolkit mode from gates.json or env var.

    Priority: AGENT_TOOLKIT_MODE env var > gates.json "mode" field > "normal".
    """
    env_mode = os.environ.get("AGENT_TOOLKIT_MODE")
    if env_mode:
        return env_mode

    gates_path = project_dir / "gates.json"
    if gates_path.is_file():
        try:
            data = json.loads(gates_path.read_text(encoding="utf-8"))
            return data.get("mode", DEFAULT_MODE)
        except (json.JSONDecodeError, OSError):
            return DEFAULT_MODE

    return DEFAULT_MODE


def scan_project_files(project_dir: Path) -> Tuple[List[str], int]:
    """Scan project for .md files with priority ordering.

    Returns (file_entries: list[str], report_count: int).
    Priority files first, then requirements/architecture, then other root .md files.
    README.md is excluded. Reports are counted but not listed.
    """
    files = []

    # Priority files
    for filename in PRIORITY_FILES:
        if (project_dir / filename).is_file():
            files.append(f"- {filename} (PRIORITY — read this first)")

    # Requirements and architecture directories
    for dirname in SCAN_DIRS:
        dir_path = project_dir / dirname
        if dir_path.is_dir():
            for md_file in sorted(dir_path.glob("*.md")):
                files.append(f"- {dirname}/{md_file.name}")

    # Count reports (don't list individually)
    report_count = 0
    reports_dir = project_dir / "reports"
    if reports_dir.is_dir():
        report_count = len(list(reports_dir.rglob("*.md")))

    # Other root .md files (not priority, not README)
    for md_file in sorted(project_dir.glob("*.md")):
        if md_file.name not in EXCLUDED_ROOT_FILES:
            files.append(f"- {md_file.name}")

    return files, report_count


def init_session_state(session_dir: Path, mode: str = "normal") -> SessionState:
    """Initialize .session/state.json with fresh counters."""
    session_dir.mkdir(parents=True, exist_ok=True)
    state = SessionState(session_start=int(time.time()), mode=mode)
    state_file = session_dir / "state.json"
    save_state(state, state_file)
    return state


def check_hook_integrity(hooks_dir: Path, settings_path: Optional[Path]) -> List[str]:
    """Check that required hooks exist, are executable, and registered.

    Returns list of warning strings.
    """
    warnings = []

    for hook_name in REQUIRED_HOOKS:
        hook_path = hooks_dir / hook_name
        if not hook_path.is_file():
            warnings.append(f"MISSING hook: {hook_name}")
        elif not hook_name.endswith(".py") and not os.access(hook_path, os.X_OK):
            warnings.append(f"NOT EXECUTABLE: {hook_name}")

    # Check settings.json registration
    if settings_path and settings_path.is_file():
        try:
            settings_text = settings_path.read_text(encoding="utf-8")
            for hook_name in SETTINGS_CHECKED_HOOKS:
                if hook_name not in settings_text:
                    warnings.append(
                        f"NOT REGISTERED in settings.json: {hook_name} (run install.sh)"
                    )
        except (json.JSONDecodeError, OSError):
            pass

    return warnings


def detect_continuation(project_dir: Path) -> Tuple[bool, str, int]:
    """Detect if this is a continuation session from HANDOFF.md.

    Returns (is_continuation: bool, goal: str, session_number: int).
    """
    handoff_path = project_dir / "HANDOFF.md"
    if not handoff_path.is_file():
        return False, "", 0

    content = handoff_path.read_text(encoding="utf-8")

    # COMPLETE marker means nothing to continue
    if "## COMPLETE" in content:
        return False, "", 0

    # Extract goal from ## Goal section
    goal = ""
    goal_match = re.search(
        r"## Goal\s*\n\s*\n(.+?)(?:\n\s*\n|\n##|\Z)",
        content,
        re.DOTALL,
    )
    if goal_match:
        goal = goal_match.group(1).strip()

    # Extract session number
    session_number = 0
    number_match = re.search(r"Number:\s*(\d+)", content)
    if number_match:
        session_number = int(number_match.group(1))

    return True, goal, session_number


def clear_stale_gates(project_dir: Path) -> List[str]:
    """Clear stale .gates/ files from previous session.

    Returns list of warning strings.
    """
    warnings = []
    gates_dir = project_dir / ".gates"
    if not gates_dir.is_dir():
        return warnings

    gate_files = list(gates_dir.iterdir())
    if gate_files:
        count = len(gate_files)
        warnings.append(
            f"STALE GATE FILES: .gates/ had {count} files from previous session (cleared)"
        )
        shutil.rmtree(gates_dir)

    return warnings


def build_context(
    files: List[str],
    report_count: int,
    warnings: List[str],
    continuation: Optional[Dict[str, object]],
    mode: Optional[str] = None,
) -> str:
    """Build the full context string for SessionStart.

    Args:
        files: List of file entry strings from scan_project_files
        report_count: Number of report .md files
        warnings: List of integrity warning strings
        continuation: Dict with 'goal' and 'session_number', or None
        mode: Agent toolkit mode ("normal", "strict", or None for default)
    """
    parts = ["AGENT TOOLKIT ACTIVE — You must follow skill workflows for all tasks."]

    # Strict mode banner
    if mode == "strict":
        parts.append("")
        parts.append(
            "STRICT MODE ACTIVE — G-IMPL-7 enforced, "
            "periodic integrity checks enabled, "
            "/evaluate required before commit."
        )

    # Continuation context (prominent, before file list)
    if continuation:
        session_num = continuation.get("session_number", 0)
        goal_text = continuation.get("goal", "")
        parts.append("")
        cont_msg = f"CONTINUATION SESSION: This is session {session_num} of an auto-continuation run."
        if goal_text:
            cont_msg += f"\nGOAL: {goal_text}"
        cont_msg += "\nRead HANDOFF.md FIRST and continue from where the previous session left off."
        parts.append(cont_msg)

    parts.append("")
    parts.append("SESSION START: Read project context before doing anything.")
    parts.append("")
    parts.append("PROJECT FILES TO READ FIRST:")

    if files:
        for entry in files:
            parts.append(entry)
        if report_count > 0:
            parts.append(
                f"- reports/ directory has {report_count} report(s) "
                f"— read only if relevant to current task"
            )
        parts.append("")
        parts.append(
            "READ THESE FILES NOW before responding to the user. "
            "They contain decisions, feature status, warnings, and context you need. "
            "The user cannot remember all details — these files ARE the memory."
        )
    else:
        parts.append("No project .md files found. This may be a new project or first session.")

    parts.append("")
    parts.append("""MANDATORY RULES:
1. NEVER edit code without following a skill workflow. Read the skill .md file first.
2. For bug fixes: follow /debug (hypothesis-driven, test-first)
3. For new features: follow /implementation (plan, TDD, slabs)
4. For refactors: follow /implementation in refactor mode
5. ALWAYS write a failing test BEFORE fixing or implementing
6. ALWAYS run /precommit before git commit (harness hook blocks without it)
7. Keep responses SHORT. Ask ONE question at a time. Don't dump information.
8. After implementing a feature, update project-state.md — strikethrough completed features
9. Every decision needs evidence. Cite file:line, requirement, or research.

RESPONSE STYLE:
- Ask focused questions, one at a time
- Don't explain what you're going to do — just do it
- Show evidence (file:line) for every claim
- If unsure, ask. Don't assume.

AVAILABLE SKILLS: /requirements /architecture /implementation /debug /verify /precommit /evaluate /reviewer /assess /explore /setup /status /updater

SESSION MONITOR ACTIVE: This session is tracked. Cumulative output bytes and context compaction are the active limits. Warning at 500KB output, hard stop at 700KB or first compaction — you get 10 tool calls to write HANDOFF.md and commit, then all non-handoff operations are blocked. Exchange count is tracked for diagnostics only.

G-SESSION-1: You must NEVER read, write, edit, or delete files in the .session/ directory. Session state is managed exclusively by hooks. Any attempt to modify .session/ will be blocked.""")

    # Integrity warnings
    if warnings:
        parts.append("")
        parts.append("HARNESS INTEGRITY WARNINGS:")
        for warning in warnings:
            parts.append(f"  - {warning}")
        parts.append(
            "Run install.sh to fix missing hooks. Do NOT proceed with work until hooks are verified."
        )

    return "\n".join(parts)


# --- Helpers for testability ---


def get_project_dir() -> Path:
    """Get the current working directory as project dir."""
    return Path.cwd()


def get_settings_path() -> Optional[Path]:
    """Get the settings.json path."""
    settings = Path.home() / ".claude" / "settings.json"
    return settings if settings.is_file() else None


# --- Main entry point ---


def main() -> int:
    """Read SessionStart event from stdin, output JSON context response."""
    raw_input = sys.stdin.read()
    try:
        event = json.loads(raw_input)
    except (json.JSONDecodeError, TypeError):
        event = {}

    project_dir = get_project_dir()
    hooks_dir = project_dir / "hooks"
    settings_path = get_settings_path()
    session_dir = project_dir / ".session"

    # 1. Detect mode (needed for session state init)
    mode = detect_mode(project_dir)

    # 2. Initialize session state with mode
    init_session_state(session_dir, mode=mode)

    # 3. Clear stale gates
    gate_warnings = clear_stale_gates(project_dir)

    # 4. Hook integrity check
    integrity_warnings = check_hook_integrity(hooks_dir, settings_path)
    all_warnings = gate_warnings + integrity_warnings

    # 5. Scan project files
    files, report_count = scan_project_files(project_dir)

    # 6. Detect continuation
    continuation = None
    is_continuation, goal, session_number = detect_continuation(project_dir)
    if is_continuation:
        continuation = {"goal": goal, "session_number": session_number}

    # 7. Build context
    context = build_context(files, report_count, all_warnings, continuation, mode=mode)

    # 8. Output JSON
    output = json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": context,
        }
    })
    sys.stdout.write(output)
    sys.stdout.flush()

    return 0


if __name__ == "__main__":
    sys.exit(main())
