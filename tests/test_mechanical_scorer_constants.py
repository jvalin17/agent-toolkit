"""mechanical_scorer thresholds are named constants and actually drive the scores."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "hooks"))

import mechanical_scorer as ms  # noqa: E402


def _function_of_lines(name: str, body_lines: int) -> str:
    body = "\n".join(f"    total += {i}" for i in range(body_lines))
    return f"def {name}(total: int) -> int:\n{body}\n    return total\n"


def test_named_thresholds_drive_scores(tmp_path):
    """One function just over LONG_FUNCTION_LINES costs exactly PENALTY_PER_LONG_FUNCTION."""
    (tmp_path / "billing.py").write_text(
        _function_of_lines("compute_invoice", ms.LONG_FUNCTION_LINES + 1)
    )
    result = ms.check_code_quality(tmp_path)
    assert result["long_functions"] == 1
    assert result["score"] == 100 - ms.PENALTY_PER_LONG_FUNCTION

    (tmp_path / "billing.py").write_text(
        _function_of_lines("compute_invoice", ms.LONG_FUNCTION_LINES - 5)
    )
    assert ms.check_code_quality(tmp_path)["score"] == 100


def test_large_file_threshold(tmp_path):
    lines = ["def f%d():\n    return %d\n" % (i, i) for i in range(ms.LARGE_FILE_LINES // 2 + 1)]
    (tmp_path / "ledger.py").write_text("\n".join(lines))
    result = ms.check_code_quality(tmp_path)
    assert result["large_files"] == 1
    assert result["score"] == 100 - ms.PENALTY_PER_LARGE_FILE


def test_penalties_are_capped(tmp_path):
    # 12 long functions × PENALTY_PER_LONG_FUNCTION exceeds the cap; keep each in
    # its own module so no file crosses LARGE_FILE_LINES.
    for i in range(12):
        (tmp_path / f"step_{i}.py").write_text(
            _function_of_lines(f"step_{i}", ms.LONG_FUNCTION_LINES + 1)
        )
    result = ms.check_code_quality(tmp_path)
    assert result["long_functions"] == 12
    assert result["large_files"] == 0
    assert result["score"] == 100 - ms.MAX_PENALTY_LONG_FUNCTIONS


def test_security_constants(tmp_path):
    (tmp_path / "deploy.py").write_text(
        'import subprocess\nsubprocess.run("ls", shell=True)\n'
    )
    result = ms.check_security(tmp_path)
    assert result["shell_true_count"] == 1
    assert result["score"] == 100 - ms.PENALTY_PER_SHELL_TRUE


def test_efficiency_constants(tmp_path):
    (tmp_path / "report.py").write_text(
        _function_of_lines("render_report", ms.VERY_LONG_FUNCTION_LINES + 1)
    )
    result = ms.check_efficiency(tmp_path)
    assert result["very_long_functions"] == 1
    assert result["score"] == 100 - ms.PENALTY_PER_VERY_LONG_FUNCTION
    assert ms.check_efficiency(tmp_path / "empty")["score"] == ms.EFFICIENCY_SCORE_NO_SOURCE


def test_completeness_proxy_constants(tmp_path):
    (tmp_path / "app.py").write_text("def ping():\n    return 'pong'\n")
    assert ms.score_codebase(tmp_path)["completeness"] == ms.COMPLETENESS_WITHOUT_TESTS
    (tmp_path / "test_app.py").write_text("def test_ping():\n    assert True is True\n")
    assert ms.score_codebase(tmp_path)["completeness"] == ms.COMPLETENESS_WITH_TESTS
