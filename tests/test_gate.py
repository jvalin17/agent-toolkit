#!/usr/bin/env python3
"""Tests for signed gate tokens (issue, verify, attest).

Requires PyJWT + cryptography — skipped automatically when unavailable
(e.g. architecture mismatch on cffi).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

jwt = pytest.importorskip("jwt", reason="PyJWT (+ cryptography) not available")

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
                        "push_requires": ["evaluate"],
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
    assert required_skills(config, "push") == ["evaluate"]


def test_required_skills_builtin_profile():
    """No profiles block in gates.json — the built-in table applies."""
    config = {"gate_mode": "signed", "profile": "paranoid"}
    assert required_skills(config, "commit") == ["precommit", "evaluate"]
    assert required_skills(config, "push") == ["evaluate", "reviewer", "assess"]


def test_required_skills_file_profiles_override_builtin():
    config = {
        "gate_mode": "signed",
        "profile": "standard",
        "profiles": {"standard": {"commit_requires": ["precommit", "reviewer"], "push_requires": []}},
    }
    assert required_skills(config, "commit") == ["precommit", "reviewer"]
    assert required_skills(config, "push") == []


def test_required_skills_falls_back_to_mode():
    """Signed mode without a profile honours the legacy `mode` field."""
    config = {"gate_mode": "signed", "mode": "safe"}
    assert required_skills(config, "commit") == ["precommit"]
    assert required_skills(config, "push") == ["reviewer"]
    assert required_skills({"gate_mode": "signed", "mode": "minimal"}, "commit") == []


def test_mode_requires_uses_mode_resolver():
    from gate.core import _mode_requires

    assert _mode_requires({"mode": "safe"}, "commit") == ["precommit"]
    assert _mode_requires({"mode": "safe"}, "push") == ["reviewer"]
    assert _mode_requires({"mode": "minimal"}, "push") == []


def test_mode_requires_env_override(monkeypatch):
    from gate.core import _mode_requires

    monkeypatch.setenv("AGENT_TOOLKIT_MODE", "safe")
    assert _mode_requires({"mode": "minimal"}, "push") == ["reviewer"]


def test_explicit_profile_wins_over_mode():
    config = {"gate_mode": "signed", "profile": "strict", "mode": "minimal"}
    assert required_skills(config, "commit") == ["precommit", "evaluate"]


def test_required_skills_defaults_to_standard_without_profile_or_mode():
    assert required_skills({"gate_mode": "signed"}, "push") == ["evaluate"]


def test_resolve_profile_records_mode_when_no_profile():
    from gate.core import resolve_profile

    assert resolve_profile({"profile": "strict"}) == "strict"
    assert resolve_profile({"mode": "safe"}) == "mode:safe"
    assert resolve_profile({}) == "standard"


def test_key_outside_worktree_and_min_length(tmp_path, monkeypatch):
    """The signing key lives under HOME, never in the repo the agent works in."""
    import stat
    from gate.keys import MIN_SECRET_CHARS, default_key_path, generate_signing_secret, load_signing_secret

    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.delenv("AGENT_TOOLKIT_GATE_SECRET", raising=False)
    monkeypatch.delenv("AGENT_TOOLKIT_GATE_PRIVATE_KEY", raising=False)
    project = tmp_path / "billing-app"
    project.mkdir()

    key_path = generate_signing_secret(project_root=project)
    assert key_path == default_key_path(project)
    assert str(key_path).startswith(str(tmp_path / "home"))
    assert not str(key_path).startswith(str(project))
    assert stat.S_IMODE(key_path.stat().st_mode) == 0o600
    assert load_signing_secret(project) == key_path.read_text().strip()

    key_path.write_text("short\n")
    with pytest.raises(ValueError, match=str(MIN_SECRET_CHARS)):
        load_signing_secret(project)


def test_legacy_project_key_still_accepted(gate_env: Path):
    from gate.keys import load_signing_secret

    assert len(load_signing_secret(gate_env)) >= 32


def test_rejects_wrong_aud_action_ref(gate_env: Path):
    def git(*args):
        subprocess.run(["git", *args], cwd=gate_env, check=True, capture_output=True)

    git("init", "-q")
    git("remote", "add", "origin", "https://github.com/acme/billing.git")
    config = load_gates_config(gate_env)

    good = _attestation_all_passed()
    good["repo"] = "acme/billing"
    good["ref"] = subprocess.run(
        ["git", "symbolic-ref", "-q", "HEAD"], cwd=gate_env, capture_output=True, text=True
    ).stdout.strip()
    token = issue_token(good, config, "push", gate_env)
    assert verify_token(token, gate_env, "push", commit_sha="abc123")[0] is True

    other_repo = dict(good, repo="evil/other")
    ok, msg = verify_token(issue_token(other_repo, config, "push", gate_env), gate_env, "push", commit_sha="abc123")
    assert ok is False and "aud" in msg

    ok, msg = verify_token(token, gate_env, "commit", commit_sha="abc123")
    assert ok is False and "action" in msg

    other_ref = dict(good, ref="refs/heads/release-2026-10")
    ok, msg = verify_token(issue_token(other_ref, config, "push", gate_env), gate_env, "push", commit_sha="abc123")
    assert ok is False and "ref" in msg


def test_push_token_does_not_satisfy_commit(gate_env: Path):
    """Push-scoped tokens no longer duplicate precommit (commit-only gate)."""
    att = _attestation_all_passed()
    config = load_gates_config(gate_env)
    token = issue_token(att, config, "push", gate_env)
    ok, msg = verify_token(token, gate_env, "commit", commit_sha="abc123")
    assert not ok
    assert "action" in msg  # a token is bound to the action it was issued for


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


def test_legacy_mode_still_verifies_jwt_when_token_present(gate_env: Path, monkeypatch):
    """CI issues gate-token.jwt; verify must not require .gates/ when a JWT is supplied."""
    (gate_env / "gates.json").write_text(
        json.dumps(
            {
                "gate_mode": "legacy",
                "profile": "standard",
                "eval_threshold": 95,
                "profiles": {
                    "standard": {
                        "commit_requires": ["precommit"],
                        "push_requires": ["evaluate"],
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    att = _attestation_all_passed()
    config = load_gates_config(gate_env)
    token = issue_token(att, config, "push", gate_env)
    ok, msg = verify_token(token, gate_env, "push", commit_sha="abc123")
    assert ok, msg
    assert not (gate_env / ".gates/precommit-passed").exists()


def test_legacy_mode_without_jwt_checks_flags(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "gates.json").write_text(
        json.dumps({"gate_mode": "legacy", "commit_requires": ["precommit"]}),
        encoding="utf-8",
    )
    ok, msg = verify_token("", tmp_path, "commit")
    assert not ok
    assert "legacy gates missing" in msg


def test_generate_signing_secret_meta_beside_key(tmp_path: Path, monkeypatch):
    """Meta file must live next to signing.key, not cwd-relative .gate/."""
    other_cwd = tmp_path / "other"
    other_cwd.mkdir()
    monkeypatch.chdir(other_cwd)
    key = tmp_path / "project" / ".gate" / "signing.key"
    generate_signing_secret(key)
    assert key.is_file()
    meta = key.parent / "signing.meta.json"
    assert meta.is_file()
    assert json.loads(meta.read_text(encoding="utf-8"))["alg"] == "HS256"


def test_bootstrap_and_signed_roundtrip(tmp_path: Path, monkeypatch):
    import os
    import shutil
    from gate.keys import default_key_path

    # Keys live under HOME, outside the repo — point HOME at a sandbox.
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    project = tmp_path / "project"
    project.mkdir()

    subprocess.run(["git", "init"], cwd=project, capture_output=True, check=True)
    bootstrap = ROOT / "scripts/bootstrap-project-gates.sh"
    proc = subprocess.run(
        ["bash", str(bootstrap), str(ROOT), str(project)],
        capture_output=True,
        text=True,
        env={**os.environ, "HOME": str(home)},
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert (project / ".agent-toolkit/gate/scripts/verify_gate.py").is_file()
    assert not (project / ".gate/signing.key").exists()  # never written inside the repo
    assert default_key_path(project).is_file()
    assert str(default_key_path(project)).startswith(str(home))
    tmp_path = project
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


def _env_without_gate_secrets() -> dict:
    """Subprocess env with no gate secret vars. PYTHONPATH keeps PyJWT importable
    when the test overrides HOME (a user-site install lives under HOME)."""
    import os

    import jwt

    env = {k: v for k, v in os.environ.items() if not k.startswith("AGENT_TOOLKIT_GATE_")}
    jwt_site = str(Path(jwt.__file__).resolve().parents[1])
    env["PYTHONPATH"] = os.pathsep.join(p for p in (jwt_site, env.get("PYTHONPATH", "")) if p)
    return env


def test_cli_issue_token_finds_home_key_without_env(tmp_path: Path, monkeypatch):
    """CI regression (run 38346123357): bootstrap puts the key under HOME, and
    issue_token.py must find it there with no env var and no legacy .gate/ key."""
    home = tmp_path / "runner-home"
    project = tmp_path / "billing-app"
    project.mkdir()
    monkeypatch.setenv("HOME", str(home))
    (project / "gates.json").write_text(
        json.dumps({"gate_mode": "signed", "profile": "standard", "eval_threshold": 95,
                    "profiles": {"standard": {"push_requires": ["evaluate"]}}}),
        encoding="utf-8",
    )
    key_path = generate_signing_secret(project_root=project)
    assert str(key_path).startswith(str(home))
    att_path = project / ".gate" / "attestation.json"
    att_path.parent.mkdir(parents=True)
    att_path.write_text(json.dumps(_attestation_all_passed()), encoding="utf-8")

    env = {**_env_without_gate_secrets(), "HOME": str(home)}
    proc = subprocess.run(
        [sys.executable, str(ROOT / "gate/scripts/issue_token.py"),
         "--action", "push", "--project-root", str(project)],
        capture_output=True, text=True, env=env, cwd=project,
    )
    assert proc.returncode == 0, proc.stderr
    assert (project / ".gate" / "gate-token.jwt").is_file()
    assert not (project / ".gate" / "signing.key").exists(), "secret must not be written into the worktree"

    proc2 = subprocess.run(
        [sys.executable, str(ROOT / "gate/scripts/verify_gate.py"), "verify",
         "--action", "push", "--commit", "abc123", "--project-root", str(project)],
        capture_output=True, text=True, env=env, cwd=project,
    )
    assert proc2.returncode == 0, proc2.stderr


def test_cli_issue_token_reports_missing_key_clearly(tmp_path: Path, monkeypatch):
    home = tmp_path / "runner-home"
    project = tmp_path / "billing-app"
    (project / ".gate").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    (project / "gates.json").write_text(json.dumps({"gate_mode": "signed"}), encoding="utf-8")
    (project / ".gate" / "attestation.json").write_text(
        json.dumps(_attestation_all_passed()), encoding="utf-8",
    )
    env = {**_env_without_gate_secrets(), "HOME": str(home)}
    proc = subprocess.run(
        [sys.executable, str(ROOT / "gate/scripts/issue_token.py"),
         "--action", "push", "--project-root", str(project)],
        capture_output=True, text=True, env=env, cwd=project,
    )
    assert proc.returncode == 1
    assert "AGENT_TOOLKIT_GATE_SECRET" in proc.stderr
    assert "setup-signed-gates.sh" in proc.stderr

