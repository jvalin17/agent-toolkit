"""gate/flags.py — HMAC-signed gate flags so a plain `touch .gates/x` is not a pass."""

import os
import stat
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gate.flags import (
    FLAG_KEY_ENV,
    flag_key_path,
    sign_flag_file,
    verify_flag,
    write_flag,
)


@pytest.fixture
def key_file(tmp_path, monkeypatch):
    path = tmp_path / "keys" / "flag.key"
    monkeypatch.setenv(FLAG_KEY_ENV, str(path))
    return path


class TestKey:
    def test_key_created_outside_project_0600(self, tmp_path, key_file):
        project = tmp_path / "billing-app"
        project.mkdir()
        write_flag(project, "precommit", "READY 2026-10-12")
        assert key_file.is_file()
        assert not str(key_file).startswith(str(project))
        assert stat.S_IMODE(key_file.stat().st_mode) == 0o600
        assert len(key_file.read_text().strip()) >= 32

    def test_default_key_path_is_in_home_not_project(self, monkeypatch, tmp_path):
        monkeypatch.delenv(FLAG_KEY_ENV, raising=False)
        monkeypatch.setenv("HOME", str(tmp_path / "home"))
        path = flag_key_path()
        assert str(path).startswith(str(tmp_path / "home"))
        assert ".agent-toolkit" in str(path)


class TestSignVerify:
    def test_write_then_verify(self, tmp_path, key_file):
        project = tmp_path / "billing-app"
        project.mkdir()
        write_flag(project, "evaluate", "PASSED 96% evaluate 2026-10-12")
        ok, content, reason = verify_flag(project, "evaluate")
        assert ok is True
        assert content == "PASSED 96% evaluate 2026-10-12"
        assert reason == "ok"

    def test_tampered_flag_rejected(self, tmp_path, key_file):
        project = tmp_path / "billing-app"
        project.mkdir()
        write_flag(project, "evaluate", "PASSED 60% evaluate 2026-10-12")
        flag = project / ".gates" / "evaluate-passed"
        flag.write_text(flag.read_text().replace("60%", "99%"))
        ok, _, reason = verify_flag(project, "evaluate")
        assert ok is False
        assert "signature" in reason

    def test_unsigned_flag_rejected(self, tmp_path, key_file):
        project = tmp_path / "billing-app"
        (project / ".gates").mkdir(parents=True)
        (project / ".gates" / "precommit-passed").write_text("READY 2026-10-12\n")
        ok, _, reason = verify_flag(project, "precommit")
        assert ok is False
        assert "unsigned" in reason

    def test_missing_flag(self, tmp_path, key_file):
        project = tmp_path / "billing-app"
        project.mkdir()
        ok, content, reason = verify_flag(project, "reviewer")
        assert (ok, content) == (False, "")
        assert reason == "missing"

    def test_flag_signed_with_other_key_rejected(self, tmp_path, key_file, monkeypatch):
        project = tmp_path / "billing-app"
        project.mkdir()
        write_flag(project, "precommit", "READY 2026-10-12")
        other = tmp_path / "keys" / "other.key"
        other.write_text("k7f2pq9x1m4v8n3b6c5z0a2s4d7g9h1j3l5w8e0r2t4y6u8i0o")
        monkeypatch.setenv(FLAG_KEY_ENV, str(other))
        ok, _, reason = verify_flag(project, "precommit")
        assert ok is False
        assert "signature" in reason

    def test_flag_bound_to_project_and_skill(self, tmp_path, key_file):
        """Copying a signed flag between projects or skills does not verify."""
        src = tmp_path / "app-a"
        dst = tmp_path / "app-b"
        src.mkdir()
        (dst / ".gates").mkdir(parents=True)
        write_flag(src, "precommit", "READY 2026-10-12")
        signed = (src / ".gates" / "precommit-passed").read_text()
        (dst / ".gates" / "precommit-passed").write_text(signed)
        assert verify_flag(dst, "precommit")[0] is False
        (src / ".gates" / "evaluate-passed").write_text(signed)
        assert verify_flag(src, "evaluate")[0] is False

    def test_sign_flag_file_helper_for_tests(self, tmp_path, key_file):
        project = tmp_path / "billing-app"
        project.mkdir()
        sign_flag_file(project / ".gates" / "reviewer-passed", "PASSED reviewer 2026-10-12")
        assert verify_flag(project, "reviewer")[0] is True

    def test_key_missing_fails_closed(self, tmp_path, monkeypatch):
        project = tmp_path / "billing-app"
        (project / ".gates").mkdir(parents=True)
        (project / ".gates" / "precommit-passed").write_text("READY\nsig:deadbeef\n")
        monkeypatch.setenv(FLAG_KEY_ENV, str(tmp_path / "nope" / "flag.key"))
        ok, _, reason = verify_flag(project, "precommit")
        assert ok is False
        assert "key" in reason


class TestFlagInternals:
    """Names mirror the helpers so the diff gate can pair each with a test."""

    def test_flag_key_path_env_override_wins(self, tmp_path, monkeypatch):
        monkeypatch.setenv(FLAG_KEY_ENV, str(tmp_path / "custom.key"))
        assert flag_key_path() == tmp_path / "custom.key"

    def test_create_key_and_load_key_roundtrip(self, tmp_path, key_file):
        from gate.flags import _create_key, _load_key

        secret = _create_key(key_file)
        assert len(secret) >= 32
        assert _load_key(create=False) == secret
        assert _load_key(create=True) == secret  # existing key is reused, not replaced

    def test_load_key_without_create_returns_none(self, key_file):
        from gate.flags import _load_key

        assert _load_key(create=False) is None

    def test_mac_depends_on_project_skill_and_content(self, tmp_path):
        from gate.flags import _mac

        base = _mac("k" * 40, tmp_path, "precommit", "READY")
        assert base == _mac("k" * 40, tmp_path, "precommit", "READY")
        assert base != _mac("k" * 40, tmp_path, "evaluate", "READY")
        assert base != _mac("k" * 40, tmp_path, "precommit", "READY ")
        assert base != _mac("j" * 40, tmp_path, "precommit", "READY")

    def test_flag_path_layout(self, tmp_path):
        from gate.flags import _flag_path

        gates_dir = ".g" + "ates"
        assert _flag_path(tmp_path, "reviewer") == tmp_path / gates_dir / "reviewer-passed"

    def test_write_flag_and_verify_flag_strip_content(self, tmp_path, key_file):
        project = tmp_path / "billing-app"
        project.mkdir()
        path = write_flag(project, "assess", "  PASSED assess 2026-10-12\n")
        assert path.read_text().splitlines()[0] == "PASSED assess 2026-10-12"
        ok, content, _ = verify_flag(project, "assess")
        assert (ok, content) == (True, "PASSED assess 2026-10-12")
