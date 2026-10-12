#!/usr/bin/env python3
"""gate_hook.py — Commit/push gate enforcement (legacy .gates or signed JWT).

Reads hook input from stdin, checks whether git commit/push is allowed based
on .gates/ flag files and gates.json configuration.

Enforcement is always **block** — there is no advisory mode. Which skills a
commit or push requires comes from the `mode` field (see mode_resolver.py).
A gates.json that exists but cannot be parsed blocks every git action until
it is fixed (fail closed).
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


_TOOLKIT_ROOT = Path(__file__).resolve().parents[1]

# Config used when gates.json exists but cannot be read. Safe mode requires
# every gate, so nothing passes until the file is fixed (fail closed).
_CORRUPT_CONFIG_FALLBACK = {"gate_mode": "legacy", "mode": "safe"}


def load_gate_config(project_dir: Path) -> dict:
    """Load gates.json from project directory (search order in gate.config).

    No file → defaults with ``_no_config`` (not a toolkit-managed project).
    Corrupt file → safe-mode config with ``_config_error`` so every consumer
    fails closed instead of silently falling back to weaker defaults.
    """
    if str(_TOOLKIT_ROOT) not in sys.path:
        sys.path.insert(0, str(_TOOLKIT_ROOT))
    from gate.config import GatesConfigError, load_gates_config

    try:
        config = load_gates_config(project_dir)
    except GatesConfigError as exc:
        sys.stderr.write(f"gate_hook: {exc}\n")
        return {**_CORRUPT_CONFIG_FALLBACK, "_config_error": str(exc)}
    if config is None:
        return {"enforcement": "block", "gate_mode": "legacy", "_no_config": True}
    return config


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
    from hook_io import context_json

    return context_json(message)


def make_block_response(reason: str, agent: str = "claude-code") -> str:
    """Build host-aware hook JSON that blocks the tool."""
    from hook_io import make_block_json

    return make_block_json(reason, agent=agent)


def _parse_hook_command(stdin_input: str) -> Optional[str]:
    """Extract git command from any host hook JSON. Returns None if absent."""
    from hook_io import parse_hook_stdin

    _agent, canonical = parse_hook_stdin(stdin_input)
    command = canonical.get("command") or ""
    if not command:
        return None
    return command


def _parse_hook_agent(stdin_input: str) -> str:
    from hook_io import parse_hook_stdin

    agent, _canonical = parse_hook_stdin(stdin_input)
    return agent


def _make_gate_finish(
    enforcement: str,
    project_dir: Path,
    agent: str = "claude-code",
) -> Callable[[str], tuple]:
    """Return a callback that blocks the git action."""

    def gate_finish(msg: str) -> tuple:
        return 0, make_block_response(msg, agent=agent)

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


# Skills that modify code — if their stamp is newer than precommit, block
_CODE_CHANGE_STAMPS = {
    "implementation", "build", "debug_tool", "fix", "refactor", "setup",
}

STAMP_CHECK_MODES = {"default", "standard", "safe"}


def _check_stale_precommit(project_dir: Path, config: dict) -> Optional[str]:
    """Block if a code-change skill ran after the last precommit.

    Returns error message if stale, None if OK.
    Only enforced in default/standard/safe modes.
    """
    from mode_resolver import resolve_mode_from_config
    mode = resolve_mode_from_config(config)
    if mode.name not in STAMP_CHECK_MODES:
        return None

    stamps_dir = project_dir / ".gates" / "stamps"
    if not stamps_dir.is_dir():
        return None

    precommit_stamp = stamps_dir / "precommit"
    if not precommit_stamp.is_file():
        return None  # No precommit stamp — flag check handles this

    try:
        precommit_data = json.loads(precommit_stamp.read_text())
        precommit_ts = precommit_data.get("timestamp", "")
    except (json.JSONDecodeError, OSError):
        return None

    # Check if any code-change stamp is newer
    for stamp_file in stamps_dir.iterdir():
        if stamp_file.name in _CODE_CHANGE_STAMPS and stamp_file.is_file():
            try:
                data = json.loads(stamp_file.read_text())
                if data.get("timestamp", "") > precommit_ts:
                    return (
                        f"stale precommit — /{stamp_file.name} ran after /precommit. "
                        "Re-run /precommit before committing."
                    )
            except (json.JSONDecodeError, OSError):
                continue

    return None


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

    # Stamp ordering check — code-change skill after precommit = stale
    if action == "commit":
        stale_msg = _check_stale_precommit(project_dir, config)
        if stale_msg:
            return gate_finish(stale_msg)

    return 0, ""


def run_gate(
    stdin_input: str,
    project_dir: Path,
    env_enforcement: Optional[str] = None,
) -> tuple:
    """Main gate logic. Returns (exit_code, output_json)."""
    agent = _parse_hook_agent(stdin_input)
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
    gate_finish = _make_gate_finish("block", project_dir, agent=agent)

    if config.get("_config_error"):
        return gate_finish(
            f"gates.json is unreadable — {config['_config_error']}. "
            f"Gates fail closed: fix the file before git {action}."
        )

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
