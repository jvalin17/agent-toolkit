"""Auto-handoff — hook-written HANDOFF.md for agent-independent continuation.

Called by session_monitor when hard stop triggers. The hook writes
the handoff directly so the agent cannot prevent, delay, or fake it.
When continue_mode is on, also schedules a background restart.
"""

import os
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
    """Write HANDOFF.md from hook — agent-independent handoff.

    Args:
        handoff_path: Path to write HANDOFF.md
        state: SessionState (duck-typed — needs exchanges, tool_calls,
               cumulative_output_bytes, compactions, last_tool_sequence)
        stop_reason: Human-readable reason for the stop
        previous_handoff: Content of existing HANDOFF.md (empty string if none)
        git_log: Output of git log --oneline
    """
    goal, session_number = parse_handoff_header(previous_handoff)
    next_session = session_number + 1

    # Build last tool sequence summary
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


def find_claude_pid() -> int:
    """Walk up the process tree to find the claude process PID.

    Hooks run as: claude → bash → python3 (this process).
    os.getppid() gives bash, which dies when the hook exits.
    We need the actual claude PID so the restarter waits for it.
    Returns 0 if not found.
    """
    try:
        pid = os.getppid()  # start from our parent
        for _ in range(10):  # walk up max 10 levels
            result = subprocess.run(
                ["ps", "-p", str(pid), "-o", "ppid=,comm="],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode != 0:
                break
            parts = result.stdout.strip().split(None, 1)
            if len(parts) < 2:
                break
            ppid, comm = int(parts[0]), parts[1]
            if "claude" in comm.lower():
                return pid  # this PID is the claude process
            if ppid <= 1:
                break
            pid = ppid
    except (OSError, ValueError, subprocess.TimeoutExpired):
        pass
    return 0


def build_restarter_code(
    wait_pid: int,
    session_dir: str,
    project_dir: str,
    claude_bin: str,
) -> str:
    """Build the Python source for the background restarter process.

    Separated from schedule_restart for testability.
    """
    return f"""
import os, shutil, subprocess, sys, time
# Wait for the claude process to exit
wait_pid = {wait_pid}
for _ in range(600):
    try:
        os.kill(wait_pid, 0)
        time.sleep(1)
    except OSError:
        break
# Brief pause to let Claude fully shut down
time.sleep(2)
# Clean session state
session_dir = {session_dir!r}
if os.path.isdir(session_dir):
    shutil.rmtree(session_dir, ignore_errors=True)
# Relaunch
prompt = "Read HANDOFF.md and continue from where the previous session left off."
cmd = [{claude_bin!r}, "-p", prompt, "--output-format", "json", "--dangerously-skip-permissions"]
env = {{**os.environ, "AGENT_TOOLKIT_CONTINUE": "true"}}
subprocess.run(cmd, cwd={project_dir!r}, env=env)
"""


def schedule_restart(project_dir: Path) -> None:
    """Spawn a detached background process that restarts claude after this session exits.

    Finds the actual claude process (not the bash intermediary), then spawns
    a restarter that waits for it to exit, cleans .session/, and relaunches.
    """
    claude_bin = shutil.which("claude")
    if not claude_bin:
        sys.stderr.write("auto_handoff: claude not on PATH, cannot schedule restart\n")
        return

    claude_pid = find_claude_pid()
    if claude_pid == 0:
        sys.stderr.write("auto_handoff: could not find claude process in tree\n")
        return

    restarter_code = build_restarter_code(
        wait_pid=claude_pid,
        session_dir=str(project_dir / ".session"),
        project_dir=str(project_dir),
        claude_bin=claude_bin,
    )
    try:
        subprocess.Popen(
            [sys.executable, "-c", restarter_code],
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError as exc:
        sys.stderr.write(f"auto_handoff: failed to schedule restart: {{exc}}\n")


def trigger_auto_handoff(state, stop_reason: str) -> None:
    """Trigger hook-written handoff. Called when hard stop fires.

    Reads existing HANDOFF.md, gets git log, writes the new handoff,
    and schedules a background restart if continue_mode is on.
    """
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
        schedule_restart(Path.cwd())
