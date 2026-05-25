#!/usr/bin/env python3
"""Tests for gate_cleanup.py — selective gate flag cleanup after git commit/push."""

import json
from pathlib import Path

import pytest

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "hooks"))

from gate_cleanup import run_gate_cleanup  # noqa: E402


@pytest.fixture
def project(tmp_path):
    """Create a project dir with .gates/ and .gate/ populated."""
    gates_dir = tmp_path / ".gates"
    gates_dir.mkdir()
    (gates_dir / "precommit-passed").write_text("READY")
    (gates_dir / "evaluate-passed").write_text("PASSED 98")
    (gates_dir / "reviewer-passed").write_text("PASSED reviewer")
    (gates_dir / "assess-passed").write_text("PASSED assess")
    (gates_dir / "enforcement-override").write_text("block")

    gate_dir = tmp_path / ".gate"
    gate_dir.mkdir()
    (gate_dir / "gate-token.jwt").write_text("token")
    (gate_dir / "attestation.json").write_text("{}")

    return tmp_path


def make_input(command: str) -> str:
    return json.dumps({"tool_input": {"command": command}})


class TestCommitCleanup:
    def test_commit_removes_precommit_only(self, project):
        exit_code, _ = run_gate_cleanup(make_input("git commit -m 'feat'"), project)
        assert exit_code == 0
        assert not (project / ".gates" / "precommit-passed").exists()
        assert (project / ".gates" / "evaluate-passed").is_file()
        assert (project / ".gates" / "reviewer-passed").is_file()
        assert (project / ".gates" / "assess-passed").is_file()
        assert (project / ".gates" / "enforcement-override").is_file()

    def test_commit_clears_signed_gate_files(self, project):
        run_gate_cleanup(make_input("git commit -m 'feat'"), project)
        assert not (project / ".gate" / "gate-token.jwt").exists()
        assert not (project / ".gate" / "attestation.json").exists()

    def test_git_commit_amend(self, project):
        run_gate_cleanup(make_input("git commit --amend"), project)
        assert not (project / ".gates" / "precommit-passed").exists()
        assert (project / ".gates" / "evaluate-passed").is_file()

    def test_git_commit_with_flags(self, project):
        run_gate_cleanup(make_input("git commit -a -m 'fix'"), project)
        assert not (project / ".gates" / "precommit-passed").exists()
        assert (project / ".gates" / "evaluate-passed").is_file()


class TestPushCleanup:
    def test_push_removes_push_scoped_flags_only(self, project):
        run_gate_cleanup(make_input("git push origin main"), project)
        assert (project / ".gates" / "precommit-passed").is_file()
        assert not (project / ".gates" / "evaluate-passed").exists()
        assert not (project / ".gates" / "reviewer-passed").exists()
        assert not (project / ".gates" / "assess-passed").exists()

    def test_push_clears_signed_gate_files(self, project):
        run_gate_cleanup(make_input("git push origin main"), project)
        assert not (project / ".gate" / "gate-token.jwt").exists()


class TestCombinedCommitPushCleanup:
    def test_commit_and_push_clears_both_scopes(self, project):
        run_gate_cleanup(
            make_input('git commit -m "ship" && git push origin main'),
            project,
        )
        assert not (project / ".gates" / "precommit-passed").exists()
        assert not (project / ".gates" / "evaluate-passed").exists()
        assert not (project / ".gates" / "reviewer-passed").exists()


class TestNonGitCommandsIgnored:
    def test_git_status_does_not_clean(self, project):
        run_gate_cleanup(make_input("git status"), project)
        assert (project / ".gates" / "precommit-passed").is_file()
        assert (project / ".gates" / "evaluate-passed").is_file()

    def test_ls_does_not_clean(self, project):
        run_gate_cleanup(make_input("ls -la"), project)
        assert (project / ".gates" / "precommit-passed").is_file()

    def test_echo_git_commit_does_not_clean(self, project):
        run_gate_cleanup(make_input("echo 'git commit'"), project)
        assert (project / ".gates" / "precommit-passed").is_file()


class TestEdgeCases:
    def test_empty_input(self, project):
        exit_code, output = run_gate_cleanup("", project)
        assert exit_code == 0
        assert (project / ".gates" / "precommit-passed").is_file()

    def test_invalid_json(self, project):
        exit_code, output = run_gate_cleanup("not json", project)
        assert exit_code == 0
        assert (project / ".gates" / "precommit-passed").is_file()

    def test_missing_command_field(self, project):
        exit_code, _ = run_gate_cleanup(json.dumps({"tool_input": {}}), project)
        assert exit_code == 0
        assert (project / ".gates" / "precommit-passed").is_file()

    def test_no_gates_dir_exists(self, tmp_path):
        exit_code, _ = run_gate_cleanup(make_input("git commit -m 'init'"), tmp_path)
        assert exit_code == 0

    def test_gate_dir_kept_if_other_files(self, project):
        (project / ".gate" / "other.txt").write_text("keep")
        run_gate_cleanup(make_input("git commit -m 'feat'"), project)
        assert not (project / ".gate" / "gate-token.jwt").exists()
        assert (project / ".gate" / "other.txt").exists()
