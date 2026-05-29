"""Tests for hooks/mechanical_scorer.py — hook-owned code quality scoring."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "hooks"))

from mechanical_scorer import (
    check_code_quality,
    check_security,
    check_test_quality,
    check_efficiency,
    score_codebase,
)


@pytest.fixture
def sample_project(tmp_path):
    """Create a minimal project with known characteristics."""
    # Source file — clean
    src = tmp_path / "app.py"
    src.write_text(
        "def greet(name: str) -> str:\n"
        "    return f'Hello, {name}'\n"
    )

    # Source file — has a long function (35 lines)
    long_src = tmp_path / "long.py"
    long_src.write_text(
        "def long_function():\n"
        + "".join(f"    x{i} = {i}\n" for i in range(35))
    )

    # Test file — good assertions
    test = tmp_path / "tests" / "test_app.py"
    test.parent.mkdir()
    test.write_text(
        "from app import greet\n\n"
        "def test_greet():\n"
        "    assert greet('Alice') == 'Hello, Alice'\n\n"
        "def test_greet_empty():\n"
        "    assert greet('') == 'Hello, '\n"
    )

    return tmp_path


@pytest.fixture
def insecure_project(tmp_path):
    """Project with security issues."""
    src = tmp_path / "bad.py"
    src.write_text(
        "import subprocess\n"
        "password = 'hunter2'\n"
        "subprocess.run(cmd, shell=True)\n"
    )
    return tmp_path


class TestCodeQuality:
    def test_clean_project_scores_high(self, sample_project):
        result = check_code_quality(sample_project)
        assert result["score"] >= 80
        assert result["long_functions"] == 1  # long.py has one

    def test_deductions_for_long_functions(self, sample_project):
        result = check_code_quality(sample_project)
        assert result["long_functions"] > 0
        assert result["score"] < 100


class TestSecurity:
    def test_clean_project_scores_high(self, sample_project):
        result = check_security(sample_project)
        assert result["score"] >= 90
        assert result["shell_true_count"] == 0

    def test_insecure_project_scores_low(self, insecure_project):
        result = check_security(insecure_project)
        assert result["score"] < 80
        assert result["shell_true_count"] > 0
        assert result["hardcoded_secrets"] > 0


class TestTestQuality:
    def test_project_with_tests(self, sample_project):
        result = check_test_quality(sample_project)
        assert result["score"] >= 50  # has tests, decent density
        assert result["test_count"] == 2
        assert result["sloppy_assertions"] == 0

    def test_project_without_tests(self, tmp_path):
        (tmp_path / "app.py").write_text("x = 1\n")
        result = check_test_quality(tmp_path)
        assert result["score"] == 0
        assert result["test_count"] == 0


class TestEfficiency:
    def test_small_project(self, sample_project):
        result = check_efficiency(sample_project)
        assert result["score"] >= 80

    def test_empty_project(self, tmp_path):
        result = check_efficiency(tmp_path)
        assert result["score"] >= 80  # nothing wrong with empty


class TestScoreCodebase:
    def test_returns_all_dimensions(self, sample_project):
        scores = score_codebase(sample_project)
        assert "code_quality" in scores
        assert "security" in scores
        assert "test_quality" in scores
        assert "efficiency" in scores
        assert "completeness" in scores
        for key, value in scores.items():
            assert 0 <= value <= 100, f"{key} out of range: {value}"

    def test_scores_are_integers(self, sample_project):
        scores = score_codebase(sample_project)
        for key, value in scores.items():
            assert isinstance(value, int), f"{key} is {type(value)}"
