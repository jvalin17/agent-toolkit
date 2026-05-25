"""Tests for gate/attest.py helpers."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from gate.attest import _normalize_python_cmd


def test_normalize_python_cmd_uses_active_interpreter():
    assert _normalize_python_cmd(["python3", "-m", "pytest", "-q"])[0] == sys.executable
    assert _normalize_python_cmd(["python", "-V"])[0] == sys.executable


def test_normalize_python_cmd_leaves_other_commands():
    assert _normalize_python_cmd(["npm", "test"]) == ["npm", "test"]
