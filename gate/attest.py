"""Run mechanical checks and produce attestation.json (CI-owned facts)."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str = ""


@dataclass
class Attestation:
    version: int
    repo: str
    commit_sha: str
    ref: str
    producer: str
    results: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "repo": self.repo,
            "commit_sha": self.commit_sha,
            "ref": self.ref,
            "producer": self.producer,
            "results": self.results,
        }


def git_head_sha(cwd: Path) -> str:
    out = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if out.returncode != 0:
        return "unknown"
    return out.stdout.strip()


def git_ref(cwd: Path) -> str:
    out = subprocess.run(
        ["git", "symbolic-ref", "-q", "HEAD"],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if out.returncode == 0:
        return out.stdout.strip()
    out = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    return out.stdout.strip() if out.returncode == 0 else "unknown"


def git_repo_slug(cwd: Path) -> str:
    out = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if out.returncode != 0:
        return "local/unknown"
    url = out.stdout.strip()
    m = re.search(r"github\.com[:/]([^/]+/[^/.]+)", url)
    if m:
        return m.group(1).removesuffix(".git")
    return url


def run_command(cmd: list[str], cwd: Path, timeout: int = 600) -> CheckResult:
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        ok = proc.returncode == 0
        detail = (proc.stderr or proc.stdout or "").strip()[:500]
        return CheckResult(name=" ".join(cmd), passed=ok, detail=detail)
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        return CheckResult(name=" ".join(cmd), passed=False, detail=str(exc))


def detect_and_run_tests(cwd: Path, config: dict) -> CheckResult:
    custom = config.get("test_command")
    if custom:
        return run_command(custom if isinstance(custom, list) else custom.split(), cwd)

    if (cwd / "pytest.ini").exists() or (cwd / "pyproject.toml").exists() or list(cwd.glob("**/test_*.py")):
        if (cwd / "pyproject.toml").exists() or (cwd / "requirements.txt").exists():
            return run_command([sys.executable, "-m", "pytest", "-q"], cwd)
    if (cwd / "package.json").exists():
        return run_command(["npm", "test", "--if-present"], cwd)
    return CheckResult(name="tests", passed=True, detail="no test runner detected — skipped")


def detect_and_run_lint(cwd: Path, config: dict) -> CheckResult:
    custom = config.get("lint_command")
    if custom:
        return run_command(custom if isinstance(custom, list) else custom.split(), cwd)

    if (cwd / "pyproject.toml").exists() or (cwd / "ruff.toml").exists():
        return run_command([sys.executable, "-m", "ruff", "check", "."], cwd)
    if (cwd / "package.json").exists():
        return run_command(["npm", "run", "lint", "--if-present"], cwd)
    return CheckResult(name="lint", passed=True, detail="no linter configured — skipped")


def run_toolkit_hook_tests(cwd: Path) -> CheckResult | None:
    script = cwd / "tests" / "test-hooks.sh"
    if script.is_file():
        return run_command(["bash", str(script)], cwd)
    return None


def run_toolkit_gate_tests(cwd: Path) -> CheckResult | None:
    script = cwd / "tests" / "test_gate.py"
    if script.is_file():
        return run_command([sys.executable, "-m", "pytest", str(script), "-q"], cwd)
    return None


def mechanical_evaluate_score(checks: list[CheckResult]) -> int:
    if not checks:
        return 0
    passed = sum(1 for c in checks if c.passed)
    return int(round(100 * passed / len(checks)))


def build_attestation(
    project_root: Path,
    config: dict,
    producer: str = "agent-toolkit-gate",
) -> Attestation:
    cwd = project_root.resolve()
    test = detect_and_run_tests(cwd, config)
    lint = detect_and_run_lint(cwd, config)
    extra: list[CheckResult] = []
    hook_tests = run_toolkit_hook_tests(cwd)
    if hook_tests:
        extra.append(hook_tests)
    gate_tests = run_toolkit_gate_tests(cwd)
    if gate_tests:
        extra.append(gate_tests)

    precommit_checks = [test, lint] + extra
    precommit_passed = all(c.passed for c in precommit_checks)

    eval_checks = list(precommit_checks)
    score = mechanical_evaluate_score(eval_checks)
    threshold = int(config.get("eval_threshold", 95))
    evaluate_passed = precommit_passed and score >= threshold

    results: dict[str, Any] = {
        "precommit": {
            "passed": precommit_passed,
            "checks": [
                {"name": c.name, "passed": c.passed, "detail": c.detail}
                for c in precommit_checks
            ],
        },
        "evaluate": {
            "passed": evaluate_passed,
            "overall_score": score,
            "threshold": threshold,
            "source": "mechanical_v1",
        },
        "reviewer": {
            "passed": precommit_passed and lint.passed,
            "source": "mechanical_v1",
        },
        "assess": {
            "passed": precommit_passed,
            "source": "mechanical_v1",
        },
    }

    return Attestation(
        version=1,
        repo=git_repo_slug(cwd),
        commit_sha=git_head_sha(cwd),
        ref=git_ref(cwd),
        producer=producer,
        results=results,
    )


def write_attestation(path: Path, attestation: Attestation) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(attestation.to_dict(), indent=2) + "\n", encoding="utf-8")


def load_attestation(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
