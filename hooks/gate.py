#!/usr/bin/env python3
"""gate.py — Commit/push gate enforcement (legacy .gates or signed JWT).

Replaces gate.sh. Reads hook input from stdin, checks whether git commit/push
is allowed based on .gates/ flag files and gates.json configuration.

Default enforcement is warn (exit 0) so Cursor and other agents are not
hard-blocked. Auto-escalates: first warn violation writes
.gates/enforcement-override → subsequent attempts are hard-blocked.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional


def detect_git_action(command: str) -> Optional[str]:
    """Detect whether a command contains git commit and/or push.

    Strips quoted strings first so commit messages mentioning 'git push'
    don't trigger push gates. Returns 'push' (highest priority), 'commit',
    or None.
    """
    # Strip single-quoted and double-quoted strings
    stripped = re.sub(r"'[^']*'", "", command)
    stripped = re.sub(r'"[^"]*"', "", stripped)

    # Split on && ; |
    segments = re.split(r"&&|;|\|", stripped)

    has_commit = False
    has_push = False
    for seg in segments:
        seg = seg.strip()
        if not seg:
            continue
        if re.search(r"^git\s+.*\s+commit|^git\s+commit", seg):
            has_commit = True
        if re.search(r"^git\s+.*\s+push|^git\s+push", seg):
            has_push = True

    if has_push:
        return "push"
    if has_commit:
        return "commit"
    return None


def load_gate_config(project_dir: Path) -> dict:
    """Load gates.json from project directory.

    Search order: gates.json, .claude/gates.json, hooks/gates.json.
    Returns defaults if not found.
    """
    candidates = [
        project_dir / "gates.json",
        project_dir / ".claude" / "gates.json",
        project_dir / "hooks" / "gates.json",
    ]
    for candidate in candidates:
        if candidate.is_file():
            try:
                return json.loads(candidate.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
    return {"enforcement": "warn", "gate_mode": "legacy"}


def resolve_enforcement(
    config_enforcement: str,
    project_dir: Path,
    env_override: Optional[str] = None,
) -> str:
    """Resolve enforcement level: env var > file override > config."""
    enforcement = config_enforcement

    override_file = project_dir / ".gates" / "enforcement-override"
    if override_file.is_file():
        file_val = override_file.read_text(encoding="utf-8").strip()
        if file_val:
            enforcement = file_val

    if env_override:
        enforcement = env_override

    return enforcement


def check_gate_flags(
    required: list,
    project_dir: Path,
    eval_threshold: int = 95,
) -> list:
    """Check .gates/ flag files for required skills.

    Returns list of missing/invalid skill descriptions.
    """
    gates_dir = project_dir / ".gates"
    missing = []

    for skill in required:
        flag = gates_dir / f"{skill}-passed"
        if not flag.is_file():
            missing.append(skill)
            continue

        content = flag.read_text(encoding="utf-8")

        if skill == "precommit":
            if "READY" not in content:
                missing.append(f"{skill}(no READY)")
        elif skill == "evaluate":
            if "PASSED" not in content:
                missing.append(f"{skill}(no PASSED)")
            else:
                score_match = re.search(r"(\d+)", content)
                score = int(score_match.group(1)) if score_match else 0
                if score < eval_threshold:
                    missing.append(
                        f"{skill}(score {score} below {eval_threshold})"
                    )
        elif skill in ("reviewer", "assess"):
            if "PASSED" not in content:
                missing.append(f"{skill}(no PASSED)")

    return missing


def make_hook_response(message: str) -> str:
    """Build Claude Code hook JSON response."""
    return json.dumps(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": message,
            }
        }
    )


def run_gate(
    stdin_input: str,
    project_dir: Path,
    env_enforcement: Optional[str] = None,
) -> tuple:
    """Main gate logic. Returns (exit_code, output_json).

    Args:
        stdin_input: Hook JSON from Claude Code.
        project_dir: Project root directory.
        env_enforcement: AGENT_TOOLKIT_ENFORCEMENT override.

    Returns:
        (exit_code, hook_response_json)
    """
    # Parse command from hook input
    try:
        hook_input = json.loads(stdin_input)
        command = hook_input.get("tool_input", {}).get("command", "")
    except (json.JSONDecodeError, TypeError):
        return 0, ""

    # Detect action
    action = detect_git_action(command)
    if action is None:
        return 0, ""

    # Load config
    config = load_gate_config(project_dir)
    gate_mode = config.get("gate_mode", "legacy")
    config_enforcement = config.get("enforcement", "warn")

    # Resolve enforcement
    enforcement = resolve_enforcement(
        config_enforcement, project_dir, env_enforcement
    )

    def gate_finish(msg: str) -> tuple:
        """Emit gate result based on enforcement level."""
        if enforcement == "block":
            return 2, make_hook_response(f"BLOCKED: {msg}")
        # Auto-escalate: first warn → block for rest of session
        gates_dir = project_dir / ".gates"
        gates_dir.mkdir(exist_ok=True)
        (gates_dir / "enforcement-override").write_text("block\n")
        return 0, make_hook_response(f"GATE WARNING: {msg}")

    # Signed mode
    if gate_mode == "signed":
        verify_script = project_dir / ".agent-toolkit" / "gate" / "scripts" / "verify_gate.py"
        if verify_script.is_file():
            try:
                commit_sha = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    capture_output=True, text=True, cwd=project_dir,
                ).stdout.strip()
                result = subprocess.run(
                    [
                        "python3", str(verify_script), "verify",
                        "--action", action,
                        "--commit", commit_sha,
                    ],
                    capture_output=True, text=True, cwd=project_dir,
                )
                if result.returncode != 0:
                    return gate_finish(
                        f"git {action} failed verify: {result.stdout.strip()}. "
                        f"Run precommit and evaluate; refresh gate token."
                    )
            except OSError:
                pass  # git or python3 not available — fall through to legacy
        return 0, ""

    # Legacy mode — determine required skills
    profile = config.get("profile")
    if profile and "profiles" in config:
        profiles = config["profiles"]
        profile_config = profiles.get(profile, {})
        required = profile_config.get(f"{action}_requires", [])
    else:
        required = config.get(f"{action}_requires", [])

    if not required:
        # No config or no jq equivalent — fallback: check precommit for commit
        if action == "commit":
            precommit_flag = project_dir / ".gates" / "precommit-passed"
            if not precommit_flag.is_file() or "READY" not in precommit_flag.read_text(encoding="utf-8"):
                return gate_finish(
                    "git commit requires precommit skill. "
                    "Run install.sh in project root."
                )
        return 0, ""

    # Check flags
    eval_threshold = config.get("eval_threshold", 95)
    missing = check_gate_flags(required, project_dir, eval_threshold)

    if missing:
        missing_str = " ".join(missing)
        return gate_finish(
            f"git {action} needs skills:{missing_str}. "
            f"Run precommit and evaluate when ready."
        )

    return 0, ""


def main() -> int:
    """Entry point — reads hook input from stdin."""
    stdin_input = sys.stdin.read()
    project_dir = Path.cwd()
    env_enforcement = os.environ.get("AGENT_TOOLKIT_ENFORCEMENT")

    exit_code, output = run_gate(stdin_input, project_dir, env_enforcement)
    if output:
        print(output)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
