"""Tests for hooks/project_root.py."""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "hooks"))

from project_root import resolve_project_root


def test_scratch_hint_finds_project_root(tmp_path, monkeypatch):
    project = tmp_path / "my-app"
    project.mkdir()
    (project / "gates.json").write_text("{}")
    scratch = project / ".scratch" / "precommit_foo"
    scratch.mkdir(parents=True)
    findings = scratch / "findings.json"
    findings.write_text("{}")

    monkeypatch.chdir(tmp_path)

    assert resolve_project_root(hint=findings) == project.resolve()


def test_git_root_used_when_not_in_scratch(tmp_path, monkeypatch):
    project = tmp_path / "repo"
    project.mkdir()
    subprocess.run(["git", "init"], cwd=project, check=True, capture_output=True)
    (project / "gates.json").write_text("{}")
    sub = project / "packages" / "api"
    sub.mkdir(parents=True)

    monkeypatch.chdir(sub)

    assert resolve_project_root(start=sub) == project.resolve()


def test_gates_json_ancestor_without_git(tmp_path, monkeypatch):
    project = tmp_path / "proj"
    nested = project / "deep" / "nested"
    nested.mkdir(parents=True)
    (project / "gates.json").write_text("{}")

    monkeypatch.chdir(nested)

    assert resolve_project_root(start=nested) == project.resolve()
