#!/usr/bin/env python3
"""Tests for signed gate tokens (issue, verify, attest)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gate.attest import Attestation, build_attestation, write_attestation  # noqa: E402
from gate.core import (  # noqa: E402
    issue_token,
    load_gates_config,
    read_token,
    required_skills,
    verify_token,
    write_token,
)
from gate.keys import generate_signing_secret  # noqa: E402
from gate.reports import check_evaluate_report, check_precommit_report  # noqa: E402


@pytest.fixture
def gate_env(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    gate_local = tmp_path / ".gate"
    agent_dir = tmp_path / ".agent-toolkit"
    agent_dir.mkdir()
    gate_pkg = agent_dir / "gate"
    # minimal gate package copy not needed if sys.path has ROOT/gate
    (tmp_path / "gates.json").write_text(
        json.dumps(
            {
                "gate_mode": "signed",
                "profile": "standard",
                "eval_threshold": 95,
                "profiles": {
                    "standard": {
                        "commit_requires": ["precommit"],
                        "push_requires": ["precommit", "evaluate"],
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    generate_signing_secret(gate_local / "signing.key")
    return tmp_path


def _attestation_all_passed() -> dict:
    return {
        "version": 1,
        "repo": "test/repo",
        "commit_sha": "abc123",
        "ref": "refs/heads/main",
        "producer": "test",
        "results": {
            "precommit": {"passed": True},
            "evaluate": {"passed": True, "overall_score": 96, "threshold": 95},
            "reviewer": {"passed": True},
            "assess": {"passed": True},
        },
    }


def test_issue_and_verify_push_token(gate_env: Path):
    att = _attestation_all_passed()
    config = load_gates_config(gate_env)
    token = issue_token(att, config, "push", gate_env)
    write_token(gate_env / ".gate/gate-token.jwt", token)
    ok, msg = verify_token(
        read_token(gate_env / ".gate/gate-token.jwt"),
        gate_env,
        "push",
        commit_sha="abc123",
    )
    assert ok, msg


def test_commit_succeeds_with_push_superset_token(gate_env: Path):
    att = _attestation_all_passed()
    config = load_gates_config(gate_env)
    token = issue_token(att, config, "push", gate_env)
    ok, msg = verify_token(token, gate_env, "commit", commit_sha="abc123")
    assert ok, msg


def test_rejects_low_eval_score(gate_env: Path):
    att = _attestation_all_passed()
    att["results"]["evaluate"]["overall_score"] = 80
    config = load_gates_config(gate_env)
    with pytest.raises(ValueError, match="cannot issue"):
        issue_token(att, config, "push", gate_env)


def test_rejects_wrong_commit_sha(gate_env: Path):
    att = _attestation_all_passed()
    config = load_gates_config(gate_env)
    token = issue_token(att, config, "push", gate_env)
    ok, msg = verify_token(token, gate_env, "push", commit_sha="different")
    assert not ok
    assert "mismatch" in msg


def test_rejects_tampered_token(gate_env: Path):
    att = _attestation_all_passed()
    config = load_gates_config(gate_env)
    token = issue_token(att, config, "push", gate_env)
    tampered = token[:-2] + "xx"
    ok, msg = verify_token(tampered, gate_env, "push", commit_sha="abc123")
    assert not ok


def test_required_skills_standard_profile(gate_env: Path):
    config = load_gates_config(gate_env)
    assert required_skills(config, "commit") == ["precommit"]
    assert required_skills(config, "push") == ["precommit", "evaluate"]


def test_report_precommit_requires_ready(tmp_path: Path):
    report = tmp_path / "reports/precommit/pc_x.md"
    report.parent.mkdir(parents=True)
    report.write_text("BLOCKED\n", encoding="utf-8")
    r = check_precommit_report(tmp_path, report)
    assert r["passed"] is False
    report.write_text("[x] READY TO COMMIT\n", encoding="utf-8")
    r2 = check_precommit_report(tmp_path, report)
    assert r2["passed"] is True
    assert "report_sha256" in r2


def test_report_evaluate_threshold(tmp_path: Path):
    report = tmp_path / "reports/evaluate/eval_x.md"
    report.parent.mkdir(parents=True)
    report.write_text("# Score: 80% (C)\n", encoding="utf-8")
    r = check_evaluate_report(tmp_path, report, 95)
    assert r["passed"] is False
    assert r["overall_score"] == 80
    report.write_text("# Score: 96% (A)\n", encoding="utf-8")
    r2 = check_evaluate_report(tmp_path, report, 95)
    assert r2["passed"] is True


def test_attest_requires_reports(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "gates.json").write_text(
        json.dumps({"gate_mode": "signed", "profile": "standard", "eval_threshold": 95}),
        encoding="utf-8",
    )
    att = build_attestation(tmp_path, load_gates_config(tmp_path))
    assert att.results["precommit"]["passed"] is False
    assert "missing" in att.results["precommit"]["detail"]


def test_attest_with_fixture_reports(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    fixtures = ROOT / "tests/fixtures/gate-reports"
    for skill in ("precommit", "evaluate", "reviewer", "assess"):
        (tmp_path / "reports" / skill).mkdir(parents=True, exist_ok=True)
    import shutil

    shutil.copy(fixtures / "pc_toolkit_ci.md", tmp_path / "reports/precommit/")
    shutil.copy(fixtures / "eval_toolkit_ci.md", tmp_path / "reports/evaluate/")
    shutil.copy(fixtures / "review_toolkit_ci.md", tmp_path / "reports/reviewer/")
    shutil.copy(fixtures / "assess_toolkit_ci.md", tmp_path / "reports/assess/")
    (tmp_path / "gates.json").write_text(
        json.dumps({"profile": "standard", "eval_threshold": 95}),
        encoding="utf-8",
    )
    att = build_attestation(tmp_path, load_gates_config(tmp_path))
    assert att.results["evaluate"]["passed"] is True
    assert att.results["evaluate"]["overall_score"] == 96


def test_bootstrap_and_signed_roundtrip(tmp_path: Path):
    import shutil

    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
    bootstrap = ROOT / "scripts/bootstrap-project-gates.sh"
    proc = subprocess.run(
        ["bash", str(bootstrap), str(ROOT), str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert (tmp_path / ".agent-toolkit/gate/scripts/verify_gate.py").is_file()
    assert (tmp_path / ".gate/signing.key").is_file()
    # Template defaults to legacy; this test exercises signed JWT roundtrip
    gates_path = tmp_path / "gates.json"
    gates = json.loads(gates_path.read_text(encoding="utf-8"))
    gates["gate_mode"] = "signed"
    gates_path.write_text(json.dumps(gates, indent=2) + "\n", encoding="utf-8")
    fixtures = ROOT / "tests/fixtures/gate-reports"
    for skill in ("precommit", "evaluate"):
        (tmp_path / "reports" / skill).mkdir(parents=True, exist_ok=True)
    shutil.copy(fixtures / "pc_toolkit_ci.md", tmp_path / "reports/precommit/")
    shutil.copy(fixtures / "eval_toolkit_ci.md", tmp_path / "reports/evaluate/")
    att = build_attestation(tmp_path, load_gates_config(tmp_path))
    write_attestation(tmp_path / ".gate/attestation.json", att)
    config = load_gates_config(tmp_path)
    token = issue_token(att.to_dict(), config, "push", tmp_path)
    ok, msg = verify_token(token, tmp_path, "push", commit_sha=att.commit_sha)
    assert ok, msg


def test_attest_on_toolkit_repo_with_seeded_reports(monkeypatch):
    """Smoke: build_attestation on toolkit with seeded reports (hooks tested separately)."""
    monkeypatch.setenv("AGENT_TOOLKIT_ATTEST_SKIP_HOOK_TESTS", "1")
    monkeypatch.setenv("AGENT_TOOLKIT_ATTEST_SKIP_GATE_TESTS", "1")
    seed = ROOT / "scripts/seed-gate-reports.sh"
    subprocess.run(["bash", str(seed)], cwd=ROOT, check=True)
    att = build_attestation(ROOT, load_gates_config(ROOT))
    assert att.results["precommit"].get("report_sha256")
    assert att.results["evaluate"]["passed"] is True


def test_cli_issue_verify_roundtrip(gate_env: Path, monkeypatch):
    monkeypatch.chdir(gate_env)
    att_path = gate_env / ".gate/attestation.json"
    att_path.parent.mkdir(parents=True, exist_ok=True)
    att_path.write_text(json.dumps(_attestation_all_passed()), encoding="utf-8")

    issue = ROOT / "gate/scripts/issue_token.py"
    verify = ROOT / "gate/scripts/verify_gate.py"
    import os

    env = {**os.environ, "AGENT_TOOLKIT_GATE_SECRET_FILE": str(gate_env / ".gate/signing.key")}
    proc = subprocess.run(
        [sys.executable, str(issue), "--action", "push", "--project-root", str(gate_env)],
        capture_output=True,
        text=True,
        env=env,
    )
    assert proc.returncode == 0, proc.stderr

    proc2 = subprocess.run(
        [
            sys.executable,
            str(verify),
            "verify",
            "--action",
            "push",
            "--commit",
            "abc123",
            "--project-root",
            str(gate_env),
        ],
        capture_output=True,
        text=True,
    )
    assert proc2.returncode == 0, proc2.stderr
