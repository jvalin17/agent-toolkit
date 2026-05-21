#!/usr/bin/env python3
"""Tests for tdd_enforce.py — TDD reminder before file edits."""

import json
from pathlib import Path

import pytest
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "hooks"))

from tdd_enforce import run_tdd_enforce  # noqa: E402


def make_input(file_path: str) -> str:
    return json.dumps({"tool_input": {"file_path": file_path}})


def parse_context(output: str) -> str:
    data = json.loads(output)
    return data["hookSpecificOutput"]["additionalContext"]


class TestSkipsNonCodeFiles:
    @pytest.mark.parametrize("filename", [
        "README.md", "config.json", "deploy.yml", "setup.yaml",
        "pyproject.toml", "app.cfg", "settings.ini", ".env",
        "data.txt", "items.csv", "package-lock.lock", "logo.svg",
        "photo.png", "image.jpg",
    ])
    def test_non_code_files_ignored(self, tmp_path, filename):
        exit_code, output = run_tdd_enforce(make_input(str(tmp_path / filename)), tmp_path)
        assert exit_code == 0
        assert output == ""


class TestSkipsTestFiles:
    @pytest.mark.parametrize("filename", [
        "test_gate.py", "gate_test.py", "gate.test.js", "gate.spec.ts",
        "GateTest.java", "GateSpec.rb",
    ])
    def test_test_files_ignored(self, tmp_path, filename):
        exit_code, output = run_tdd_enforce(make_input(str(tmp_path / filename)), tmp_path)
        assert exit_code == 0
        assert output == ""

    @pytest.mark.parametrize("dirpart", [
        "tests", "__tests__", "spec", "test",
    ])
    def test_test_directories_ignored(self, tmp_path, dirpart):
        path = tmp_path / dirpart / "helper.py"
        exit_code, output = run_tdd_enforce(make_input(str(path)), tmp_path)
        assert exit_code == 0
        assert output == ""


class TestSkipsConfigFiles:
    @pytest.mark.parametrize("filename", [
        "webpack.config.js", "Makefile", "Dockerfile",
        "docker-compose.yml", "setup.py", "install.sh",
    ])
    def test_config_files_ignored(self, tmp_path, filename):
        exit_code, output = run_tdd_enforce(make_input(str(tmp_path / filename)), tmp_path)
        assert exit_code == 0
        assert output == ""


class TestTDDReminder:
    def test_source_file_without_test_gets_reminder(self, tmp_path):
        exit_code, output = run_tdd_enforce(make_input(str(tmp_path / "gate.py")), tmp_path)
        assert exit_code == 0
        context = parse_context(output)
        assert "TDD CHECK" in context
        assert "gate.py" in context

    def test_source_file_with_test_no_reminder(self, tmp_path):
        # Create corresponding test file
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_gate.py").write_text("# test")
        exit_code, output = run_tdd_enforce(make_input(str(tmp_path / "gate.py")), tmp_path)
        assert exit_code == 0
        assert output == ""

    def test_finds_test_in_same_dir(self, tmp_path):
        (tmp_path / "test_utils.py").write_text("# test")
        exit_code, output = run_tdd_enforce(make_input(str(tmp_path / "utils.py")), tmp_path)
        assert exit_code == 0
        assert output == ""

    def test_finds_test_in_parent_tests_dir(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        tests = tmp_path / "tests"
        tests.mkdir()
        (tests / "test_app.py").write_text("# test")
        exit_code, output = run_tdd_enforce(make_input(str(src / "app.py")), tmp_path)
        assert exit_code == 0
        assert output == ""

    def test_finds_jest_style_test(self, tmp_path):
        (tmp_path / "utils.test.js").write_text("// test")
        exit_code, output = run_tdd_enforce(make_input(str(tmp_path / "utils.js")), tmp_path)
        assert exit_code == 0
        assert output == ""

    def test_js_source_without_test(self, tmp_path):
        exit_code, output = run_tdd_enforce(make_input(str(tmp_path / "app.js")), tmp_path)
        context = parse_context(output)
        assert "TDD CHECK" in context


class TestEdgeCases:
    def test_empty_input(self, tmp_path):
        exit_code, output = run_tdd_enforce("", tmp_path)
        assert exit_code == 0
        assert output == ""

    def test_invalid_json(self, tmp_path):
        exit_code, output = run_tdd_enforce("bad", tmp_path)
        assert exit_code == 0
        assert output == ""

    def test_missing_file_path(self, tmp_path):
        exit_code, output = run_tdd_enforce(json.dumps({"tool_input": {}}), tmp_path)
        assert exit_code == 0
        assert output == ""
