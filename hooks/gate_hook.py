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

sys.path.insert(0, str(Path(__file__).resolve().parent))

from git_command import detect_git_action, detect_git_actions  # noqa: E402,F401 — re-exported

_TOOLKIT_ROOT = Path(__file__).resolve().parents[1]
if str(_TOOLKIT_ROOT) not in sys.path:
    sys.path.insert(0, str(_TOOLKIT_ROOT))

from gate.flags import verify_flag  # noqa: E402

# Actions are checked in this order so a "commit && push" line reports the
# commit gate first (it is the one that must pass first).
ACTION_ORDER = ("commit", "push")

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


def _toolkit_project_marker(project_dir: Path) -> Optional[str]:
    """Why this looks like a toolkit project even though gates.json is absent.

    Returns a human-readable reason, or None for a plain repository. A deleted
    policy file must not silently turn every gate off (fail closed).
    """
    if (project_dir / ".agent-toolkit").is_dir():
        return ".agent-toolkit/ exists"
    try:
        probe = subprocess.run(
            ["git", "cat-file", "-e", "HEAD:gates.json"],
            cwd=project_dir, capture_output=True, text=True, timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if probe.returncode == 0:
        return "gates.json is tracked in HEAD (deleted from the working tree)"
    return None


# Keys where an environment override may only STRENGTHEN enforcement. A repo's
# .claude/settings.json "env" block or a shell rc can set AGENT_TOOLKIT_* for
# every future session; those must not be able to switch protection off.
STRENGTHEN_ONLY_BOOLS = {"gate_protect", "report_protect"}
STRENGTHEN_ONLY_MIN_INTS = {"eval_threshold"}
SKILL_ENFORCE_RANK = {"off": 0, "remind": 1, "block": 2}


def _coerce_env(env_val: str, default):
    if isinstance(default, bool):
        return env_val.lower() in ("true", "1", "yes")
    if isinstance(default, int):
        try:
            return int(env_val)
        except ValueError:
            return env_val
    return env_val


def _weakens(key: str, env_value, file_value) -> bool:
    if key in STRENGTHEN_ONLY_BOOLS:
        return bool(file_value) and not bool(env_value)
    if key in STRENGTHEN_ONLY_MIN_INTS:
        try:
            return int(env_value) < int(file_value)
        except (TypeError, ValueError):
            return True
    if key == "skill_enforce":
        return SKILL_ENFORCE_RANK.get(str(env_value), -1) < SKILL_ENFORCE_RANK.get(str(file_value), 1)
    return False


def get_config_value(config: dict, key: str, default=None):
    """Get config value with AGENT_TOOLKIT_* env var override.

    Env var name: AGENT_TOOLKIT_{KEY_UPPER} (e.g. tdd → AGENT_TOOLKIT_TDD).
    Type coercion: bool if default is bool, int if default is int, else string.
    For protection keys the override is honoured only when it is at least as
    strict as the file value (see STRENGTHEN_ONLY_*).
    """
    file_value = config.get(key, default)
    env_val = os.environ.get(f"AGENT_TOOLKIT_{key.upper()}")
    if env_val is None:
        return file_value
    env_value = _coerce_env(env_val, default)
    if _weakens(key, env_value, file_value):
        sys.stderr.write(
            f"gate_hook: ignoring AGENT_TOOLKIT_{key.upper()}={env_val!r} — it would weaken "
            f"{key} below the gates.json value\n"
        )
        return file_value
    return env_value


def check_gate_flags(
    required: list,
    project_dir: Path,
    eval_threshold: int = 95,
) -> list:
    """Check .gates/ flag files for required skills.

    A flag counts only when its HMAC signature verifies (gate/flags.py), so a
    hand-written READY file is reported as unverified, not as passed.
    Returns list of missing/invalid skill descriptions.
    """
    missing = []

    for skill in required:
        ok, content, reason = verify_flag(project_dir, skill)
        if not ok:
            missing.append(skill if reason == "missing" else f"{skill}(unverified: {reason})")
            continue

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
    """Run signed JWT verification. Returns error message, or None if OK.

    The verifier is always the toolkit's own copy. The project copy under
    .agent-toolkit/ is repository-controlled, so an agent (or a hostile clone)
    could edit it to exit 0.
    """
    verify_script = _TOOLKIT_ROOT / "gate" / "scripts" / "verify_gate.py"
    if not verify_script.is_file():
        return (
            f"signed mode: verifier missing at {verify_script} — the toolkit install "
            "is incomplete; reinstall agent-toolkit"
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
                sys.executable,
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
) -> tuple:
    """Main gate logic. Returns (exit_code, output_json)."""
    agent = _parse_hook_agent(stdin_input)
    command = _parse_hook_command(stdin_input)
    if command is None:
        return 0, ""

    actions = [a for a in ACTION_ORDER if a in detect_git_actions(command)]
    if not actions:
        return 0, ""

    config = load_gate_config(project_dir)
    gate_finish = _make_gate_finish("block", project_dir, agent=agent)
    if config.get("_no_config"):
        marker = _toolkit_project_marker(project_dir)
        if marker is None:
            return 0, ""  # No gates.json and no toolkit footprint — not a toolkit project
        return gate_finish(
            f"gates.json is missing but {marker} — the policy file was deleted or never "
            f"restored. Gates fail closed: restore gates.json before git {' and '.join(actions)}."
        )
    gate_mode = config.get("gate_mode", "legacy")

    if config.get("_config_error"):
        return gate_finish(
            f"gates.json is unreadable — {config['_config_error']}. "
            f"Gates fail closed: fix the file before git {' and '.join(actions)}."
        )

    # A single command line may both commit and push: every action must pass.
    for action in actions:
        if gate_mode == "signed":
            verify_error = _verify_signed_gate(project_dir, action)
            if verify_error:
                return gate_finish(verify_error)
            continue
        exit_code, output = _run_legacy_gate(project_dir, config, action, gate_finish)
        if output:
            return exit_code, output
    return 0, ""


def main() -> int:
    """Entry point — reads hook input from stdin."""
    stdin_input = sys.stdin.read()
    project_dir = Path.cwd()

    exit_code, output = run_gate(stdin_input, project_dir)
    if output:
        print(output)
    return exit_code


if __name__ == "__main__":
    from hook_io import run_guarded

    sys.exit(run_guarded(main, "gate_hook"))
