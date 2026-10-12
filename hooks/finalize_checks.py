"""Shared checks and I/O for the finalize gates (precommit, evaluate, reviewer, assess).

Stamp verification, review-depth, spot checks, mechanical re-run, session
audits, report paths and gate flags. Pure helpers — no gate decides here.
"""

from __future__ import annotations

import json
import random
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from gate.attest import (  # noqa: E402
    CheckResult,
    detect_and_run_lint,
    detect_and_run_tests,
)

# hosts/<id>.json "stamp_mode": "hook_skill_passed" means the host's Skill hook
# writes stamps itself (Claude Code). A "cli" stamp there was written through
# the MCP/CLI tool by the agent — a forgery. On "cli_stamp" hosts (Cursor,
# Gemini, Codex, Grok, Windsurf, default) the CLI stamp is the only mechanism.
HOOK_STAMP_MODE = "hook_skill_passed"

DEPTH_CHECK_MODES = {"safe", "standard"}

SPOT_CHECK_PATTERNS = [
    (re.compile(r"except\s*:\s*\n\s*(pass|\.\.\.)\s*$", re.MULTILINE),
     "swallowed exception — bare except:pass hides errors"),
    (re.compile(r"except\s+\w.*:\s*\n\s*#\s*(TODO|FIXME|HACK)", re.MULTILINE | re.IGNORECASE),
     "TODO/FIXME in error handling path — error may not be handled"),
    (re.compile(r"""(password|secret|api_key|token)\s*=\s*["'][^"']{8,}["']""", re.IGNORECASE),
     "possible hardcoded secret — use environment variable instead"),
]
SPOT_CHECK_PROBABILITY = 0.2  # 20% chance per finalize
SPOT_CHECK_SAMPLE_SIZE = 3

REPORT_PREFIX = {
    "precommit": "pc",
    "evaluate": "eval",
    "reviewer": "review",
    "assess": "assess",
}

GIT_TIMEOUT_SECONDS = 10


# --- Stamps -----------------------------------------------------------------


def _host_stamps_via_hook() -> bool:
    from host_config import resolve_host

    return resolve_host().get("stamp_mode") == HOOK_STAMP_MODE


def _read_stamp(stamp_file: Path) -> dict | None:
    """Parse a stamp file. Returns None when it is not the hook's JSON format."""
    try:
        data = json.loads(stamp_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _check_skill_stamp(project_dir: Path, skill: str) -> list[str]:
    """Verify a genuine skill stamp exists in .gates/stamps/. Returns issues list.

    A stamp counts only if it is the JSON the hook writes, names this skill,
    and — on hosts where the Skill hook writes stamps — was not written via
    the CLI/MCP ``stamp_skill`` tool.
    """
    stamp_file = project_dir / ".gates" / "stamps" / skill
    if not stamp_file.is_file():
        return [
            f"{skill} stamp missing — skill was not invoked via the Skill tool. "
            f"Run /{skill} before submitting findings."
        ]

    data = _read_stamp(stamp_file)
    if data is None:
        return [
            f"{skill} stamp unreadable — not the format written by the Skill hook. "
            f"Run /{skill} via the Skill tool; do not write stamps by hand."
        ]

    stamped_skill = str(data.get("skill", ""))
    if stamped_skill.rsplit(":", 1)[-1] != skill:
        return [
            f"{skill} stamp names a different skill ('{stamped_skill}') — "
            f"stamps cannot be copied between skills. Run /{skill}."
        ]

    if data.get("source") == "cli" and _host_stamps_via_hook():
        return [
            f"{skill} stamp was written via the cli/MCP stamp_skill tool, "
            "which is not accepted on Claude Code — the Skill hook writes stamps there. "
            f"Run /{skill} via the Skill tool."
        ]
    return []


def _check_stamps(project_dir: Path, findings: dict) -> list[str]:
    """Verify skill stamps match agent claims. Returns issues list.

    Catches three attack vectors:
    1. Agent claims reviewer_called but never invoked /reviewer
    2. Agent deleted execution-plan.json to bypass plan compliance
    3. Agent submitted findings without invoking the skill
    """
    issues: list[str] = []

    reviewer_gate = findings.get("reviewer_gate", {})
    if reviewer_gate.get("reviewer_called"):
        for issue in _check_skill_stamp(project_dir, "reviewer"):
            issues.append(f"{issue} (agent claimed reviewer_called: true)")

    impl_stamp = project_dir / ".gates" / "stamps" / "implementation"
    exec_plan = project_dir / ".scratch" / "execution-plan.json"
    if impl_stamp.is_file() and not exec_plan.is_file():
        issues.append(
            "execution plan missing — /implementation was invoked (stamp exists) "
            "but .scratch/execution-plan.json was deleted. This bypasses plan compliance."
        )

    return issues


# --- Review depth + spot checks ---------------------------------------------


def _check_review_depth(
    session_audit: dict,
    mode_name: str,
    reviewer_stamp: bool = False,
) -> list[str]:
    """Verify review depth meets the minimum bar. Safe/standard modes only."""
    if mode_name not in DEPTH_CHECK_MODES:
        return []
    if not session_audit.get("available"):
        return []

    issues: list[str] = []
    if reviewer_stamp and session_audit.get("role_agents_spawned", 0) == 0:
        issues.append(
            "shallow review — reviewer was invoked but no role review agents "
            "were spawned. The skill requires per-role agents for code review."
        )
    return issues


def _spot_check_files(file_paths: list[str]) -> list[str]:
    """Scan files for obvious anti-patterns. Returns warning strings."""
    warnings: list[str] = []
    for file_path in file_paths:
        try:
            content = Path(file_path).read_text(errors="ignore")
        except OSError:
            continue
        filename = Path(file_path).name
        for pattern, message in SPOT_CHECK_PATTERNS:
            if pattern.search(content):
                warnings.append(f"spot check: {filename} — {message}")
    return warnings


def _maybe_spot_check(
    changed_files: list[str],
    mode_name: str,
    force: bool = False,
) -> list[str]:
    """Run spot checks on a sample of changed files. Safe/standard modes only.

    SPOT_CHECK_PROBABILITY chance unless force=True (for testing).
    """
    if mode_name not in DEPTH_CHECK_MODES or not changed_files:
        return []
    if not force and random.random() > SPOT_CHECK_PROBABILITY:
        return []
    sample = random.sample(changed_files, min(SPOT_CHECK_SAMPLE_SIZE, len(changed_files)))
    return _spot_check_files(sample)


# --- Mechanical re-run, audits, git -----------------------------------------


def _run_mechanical(project_dir: Path, config: dict) -> tuple[CheckResult, CheckResult]:
    test = detect_and_run_tests(project_dir, config)
    lint = detect_and_run_lint(project_dir, config)
    return test, lint


def _check_session_audit() -> dict:
    """Mechanical check: read session JSONL for skill/role usage (warnings only)."""
    try:
        from compliance import get_session_skill_usage
        usage = get_session_skill_usage()
        if not usage.get("available"):
            return {"available": False}

        warnings = []
        if usage.get("skill_count", 0) == 0:
            warnings.append("No skills invoked this session — consider using /implementation, /debug_tool, or /architecture")
        if usage.get("agents_without_model", 0) > 0:
            count = usage["agents_without_model"]
            warnings.append(f"{count} agent(s) spawned without model parameter — consider setting model for cost efficiency")

        return {
            "available": True,
            "skills_invoked": usage.get("skills", []),
            "skill_count": usage.get("skill_count", 0),
            "agents_without_model": usage.get("agents_without_model", 0),
            "warnings": warnings,
        }
    except Exception as exc:
        sys.stderr.write(f"finalize_report: session skill audit unavailable: {exc}\n")
        return {"available": False}


def _get_session_action_audit() -> dict:
    """Run the mechanical session audit from the current session JSONL."""
    try:
        from compliance import audit_session_actions
        from hooks.session_log import find_latest_session_log

        log_path = find_latest_session_log()
        if not log_path:
            return {"available": False}
        return audit_session_actions(log_path)
    except Exception as exc:
        sys.stderr.write(f"finalize_report: session action audit unavailable: {exc}\n")
        return {"available": False}


def _git_output(project_dir: Path, args: list[str]) -> str:
    """Run a git command in project_dir; empty string on any failure."""
    try:
        proc = subprocess.run(
            ["git", *args], capture_output=True, text=True,
            cwd=project_dir, timeout=GIT_TIMEOUT_SECONDS,
        )
    except Exception as exc:
        sys.stderr.write(f"finalize_report: git {' '.join(args)} failed: {exc}\n")
        return ""
    return proc.stdout if proc.returncode == 0 else ""


# --- Report + gate output ---------------------------------------------------


def _report_path(project_dir: Path, skill: str, slug: str, report_id: str) -> Path:
    target_dir = project_dir / "reports" / skill
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir / f"{REPORT_PREFIX[skill]}_{slug}_{report_id}.md"


def _write_gate_flag(project_dir: Path, skill: str, *, score: int | None = None) -> Path:
    """Write the HMAC-signed pass flag (gate/flags.py). Only finalize calls this."""
    from gate.flags import write_flag

    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if skill == "precommit":
        content = f"READY {date}"
    elif skill == "evaluate":
        content = f"PASSED {score}% evaluate {date}"
    else:
        content = f"PASSED {skill} {date}"
    return write_flag(project_dir, skill, content)


def _emit_response(payload: dict, ok: bool) -> int:
    sys.stdout.write(json.dumps(payload, indent=2) + "\n")
    return 0 if ok else 1


def mechanical_reasons(test: CheckResult, lint: CheckResult) -> list[str]:
    """Blocking reasons from the hook's own test/lint re-run."""
    reasons: list[str] = []
    if not test.passed:
        reasons.append(f"test re-run failed: {test.name}")
    if not lint.passed:
        reasons.append(f"lint re-run failed: {lint.name}")
    return reasons
