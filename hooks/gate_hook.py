#!/usr/bin/env python3
"""gate_hook.py — Commit/push gate enforcement (legacy .gates or signed JWT).

Reads hook input from stdin, checks whether git commit/push is allowed based
on .gates/ flag files and gates.json configuration.

Default enforcement is **block** (matches `templates/gates.json`). Set
`enforcement: warn` in gates.json for advisory-only mode. In warn mode,
auto-escalates: first violation writes `.gates/enforcement-override` →
subsequent attempts are hard-blocked.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Callable, Optional


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
    return {"enforcement": "block", "gate_mode": "legacy", "_no_config": True}


def get_config_value(config: dict, key: str, default=None):
    """Get config value with AGENT_TOOLKIT_* env var override.

    Env var name: AGENT_TOOLKIT_{KEY_UPPER} (e.g. tdd → AGENT_TOOLKIT_TDD).
    Type coercion: bool if default is bool, int if default is int, else string.
    """
    env_key = f"AGENT_TOOLKIT_{key.upper()}"
    env_val = os.environ.get(env_key)
    if env_val is not None:
        if isinstance(default, bool):
            return env_val.lower() in ("true", "1", "yes")
        if isinstance(default, int):
            try:
                return int(env_val)
            except ValueError:
                pass
        return env_val
    return config.get(key, default)


def resolve_enforcement(
    config_enforcement: str,
    project_dir: Path,
    env_override: Optional[str] = None,
) -> str:
    """Resolve enforcement level. Always 'block' in new mode system.

    Kept for backward compatibility with signed mode and tests.
    """
    return "block"


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
    """Build Claude Code hook JSON response (context injection, non-blocking)."""
    return json.dumps(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": message,
            }
        }
    )


def make_block_response(reason: str) -> str:
    """Build Claude Code hook JSON response that blocks the tool."""
    return json.dumps({"decision": "block", "reason": reason})


def _parse_hook_command(stdin_input: str) -> Optional[str]:
    """Extract git command from hook JSON. Returns None if not a git hook event."""
    try:
        hook_input = json.loads(stdin_input)
        command = hook_input.get("tool_input", {}).get("command", "")
    except (json.JSONDecodeError, TypeError):
        return None
    if not command:
        return None
    return command


def _make_gate_finish(
    enforcement: str,
    project_dir: Path,
) -> Callable[[str], tuple]:
    """Return a callback that blocks the git action."""

    def gate_finish(msg: str) -> tuple:
        return 0, make_block_response(msg)

    return gate_finish


def _verify_signed_gate(project_dir: Path, action: str) -> Optional[str]:
    """Run signed JWT verification. Returns error message, or None if OK."""
    verify_script = (
        project_dir / ".agent-toolkit" / "gate" / "scripts" / "verify_gate.py"
    )
    if not verify_script.is_file():
        return (
            "signed mode: verify_gate.py not found — run install/bootstrap "
            "to create .agent-toolkit/gate/"
        )

    try:
        commit_proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=project_dir,
        )
        if commit_proc.returncode != 0:
            detail = (commit_proc.stderr or commit_proc.stdout or "").strip()
            return f"signed mode: git rev-parse HEAD failed: {detail or 'unknown error'}"

        commit_sha = commit_proc.stdout.strip()
        result = subprocess.run(
            [
                "python3",
                str(verify_script),
                "verify",
                "--action",
                action,
                "--commit",
                commit_sha,
            ],
            capture_output=True,
            text=True,
            cwd=project_dir,
        )
        if result.returncode != 0:
            detail = (result.stdout or result.stderr or "").strip()
            return (
                f"git {action} failed verify: {detail}. "
                "Run precommit and evaluate; refresh gate token."
            )
        return None
    except OSError as exc:
        sys.stderr.write(
            f"gate_hook: signed verify unavailable ({exc}); blocking git {action}\n"
        )
        return (
            f"signed mode: verification unavailable ({exc}). "
            "Ensure git and python3 are on PATH, or switch to legacy mode."
        )


def _required_skills_for_action(config: dict, action: str) -> list:
    """Resolve required skills for commit or push from mode."""
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).resolve().parent))
    from mode_resolver import resolve_mode_from_config

    mode = resolve_mode_from_config(config)
    if action == "commit":
        return list(mode.commit_requires)
    if action == "push":
        return list(mode.push_requires)
    return []


def _run_legacy_gate(
    project_dir: Path,
    config: dict,
    action: str,
    gate_finish: Callable[[str], tuple],
) -> tuple:
    """Legacy .gates/ flag enforcement."""
    required = _required_skills_for_action(config, action)

    if not required:
        return 0, ""

    eval_threshold = config.get("eval_threshold", 95)
    missing = check_gate_flags(required, project_dir, eval_threshold)

    if missing:
        missing_str = " ".join(missing)
        return gate_finish(
            f"git {action} needs skills:{missing_str} — run them first."
        )

    return 0, ""


def run_gate(
    stdin_input: str,
    project_dir: Path,
    env_enforcement: Optional[str] = None,
) -> tuple:
    """Main gate logic. Returns (exit_code, output_json)."""
    command = _parse_hook_command(stdin_input)
    if command is None:
        return 0, ""

    action = detect_git_action(command)
    if action is None:
        return 0, ""

    config = load_gate_config(project_dir)
    if config.get("_no_config"):
        return 0, ""  # No gates.json — not a toolkit-managed project
    gate_mode = config.get("gate_mode", "legacy")
    gate_finish = _make_gate_finish("block", project_dir)

    if gate_mode == "signed":
        verify_error = _verify_signed_gate(project_dir, action)
        if verify_error:
            return gate_finish(verify_error)
        return 0, ""

    return _run_legacy_gate(project_dir, config, action, gate_finish)


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
