"""Auto-handoff — hook-written HANDOFF.md and session restart.

Called by session_monitor when context pressure is high and continue_mode
is on. Writes HANDOFF.md and launches a new claude session in the background.
"""

import re
import shutil
import subprocess
import sys
from pathlib import Path


def parse_handoff_header(handoff_text: str) -> tuple:
    """Extract goal and session number from existing HANDOFF.md content.

    Returns (goal: str, session_number: int).
    Defaults to ("", 1) when parsing fails.
    """
    goal = ""
    session_number = 1

    if not handoff_text:
        return goal, session_number

    # Extract goal: text between "## Goal" and next "##"
    goal_match = re.search(
        r"## Goal\s*\n\s*\n(.*?)(?=\n## |\Z)", handoff_text, re.DOTALL
    )
    if goal_match:
        goal = goal_match.group(1).strip()

    # Extract session number: "Number: N"
    number_match = re.search(r"Number:\s*(\d+)", handoff_text)
    if number_match:
        session_number = int(number_match.group(1))

    return goal, session_number


def write_auto_handoff(
    handoff_path: Path,
    state,
    stop_reason: str,
    previous_handoff: str,
    git_log: str,
) -> None:
    """Write HANDOFF.md from hook — agent-independent handoff."""
    goal, session_number = parse_handoff_header(previous_handoff)
    next_session = session_number + 1

    tool_summary = ""
    if state.last_tool_sequence:
        tool_lines = []
        for entry in state.last_tool_sequence[-5:]:
            tool = entry.get("tool", "?")
            detail = entry.get("file_path", "") or entry.get("command", "")
            if detail:
                tool_lines.append(f"  - {tool}: {detail}")
            else:
                tool_lines.append(f"  - {tool}")
        tool_summary = "\n".join(tool_lines)

    content = f"""# HANDOFF

## Goal

{goal if goal else "(no goal set — check project-state.md)"}

## Session

Number: {next_session}
Previous sessions: {session_number}

## Stop Reason

{stop_reason}

This handoff was written automatically by the session_monitor hook.
The agent did not write this file.

## Session Stats

- Exchanges: {state.exchanges}
- Tool calls: {state.tool_calls}
- Output bytes: {state.cumulative_output_bytes:,}
- Compactions: {state.compactions}

## Recent Commits

{git_log if git_log else "(no commits this session)"}

## Last Tool Sequence

{tool_summary if tool_summary else "(none recorded)"}

## Resume Command

Read project-state.md and this file. Continue from where the previous session stopped.
"""
    handoff_path.write_text(content, encoding="utf-8")


def get_git_log(max_entries: int = 10) -> str:
    """Get recent git log as oneline format. Returns empty string on failure."""
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", f"-{max_entries}"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return ""


def launch_new_session(project_dir: Path) -> bool:
    """Launch a new claude session in the background.

    Spawns `claude -p` as a detached process. The new session reads
    HANDOFF.md and continues. No PID-watching — just fire and forget.
    Returns True if launched, False if claude not found.
    """
    claude_bin = shutil.which("claude")
    if not claude_bin:
        sys.stderr.write("auto_handoff: claude not on PATH, cannot launch new session\n")
        return False

    prompt = "Read HANDOFF.md and continue from where the previous session left off."
    cmd = [
        claude_bin, "-p", prompt,
        "--output-format", "json",
        "--dangerously-skip-permissions",
    ]

    try:
        subprocess.Popen(
            cmd,
            cwd=str(project_dir),
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except OSError as exc:
        sys.stderr.write(f"auto_handoff: failed to launch session: {exc}\n")
        return False


def trigger_auto_handoff(state, stop_reason: str) -> None:
    """Write HANDOFF.md and launch a new session if continue_mode is on."""
    handoff_path = Path("HANDOFF.md")
    previous_handoff = ""
    if handoff_path.exists():
        try:
            previous_handoff = handoff_path.read_text(encoding="utf-8")
        except OSError:
            pass

    git_log = get_git_log()

    write_auto_handoff(
        handoff_path=handoff_path,
        state=state,
        stop_reason=stop_reason,
        previous_handoff=previous_handoff,
        git_log=git_log,
    )

    if getattr(state, "continue_mode", False):
        launch_new_session(Path.cwd())
