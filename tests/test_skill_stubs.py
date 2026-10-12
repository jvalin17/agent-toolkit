"""Skill stubs stay short; depth lives in modules."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _non_empty_lines(path: Path) -> int:
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def test_implementation_stub_under_120_lines():
    stub = ROOT / "skills" / "implementation" / "SKILL.md"
    assert stub.is_file()
    assert _non_empty_lines(stub) <= 120
    assert (ROOT / "skills" / "implementation" / "modules" / "workflow.md").is_file()
    assert (ROOT / "skills" / "implementation" / "modules" / "tdd.md").is_file()


def test_precommit_stub_under_120_lines():
    stub = ROOT / "skills" / "precommit" / "SKILL.md"
    assert stub.is_file()
    assert _non_empty_lines(stub) <= 120
    assert (ROOT / "skills" / "precommit" / "modules" / "workflow.md").is_file()
    assert (ROOT / "skills" / "precommit" / "modules" / "checks.md").is_file()


def test_workflow_modules_contain_depth():
    impl = (ROOT / "skills" / "implementation" / "modules" / "workflow.md").read_text()
    assert "Execution Plan" in impl or "TDD" in impl
    pre = (ROOT / "skills" / "precommit" / "modules" / "workflow.md").read_text()
    assert "Pre-Commit" in pre or "G-PC-1" in pre
