#!/usr/bin/env python3
"""Tests for roles/context.py — universal role context CLI."""

import json
from pathlib import Path

import pytest
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "roles"))


class TestContextCLI:
    def test_returns_role_context_for_project(self, tmp_path):
        from context import get_context

        # Create a project that looks like backend
        pkg = {"dependencies": {"express": "^4.0.0"}}
        (tmp_path / "package.json").write_text(json.dumps(pkg))

        # Create minimal role files
        roles_dir = ROOT / "roles"
        context = get_context(tmp_path, roles_dir=roles_dir)

        assert "ACTIVE ROLES:" in context
        assert "backend" in context.lower()

    def test_empty_project_returns_no_roles(self, tmp_path):
        from context import get_context

        roles_dir = ROOT / "roles"
        context = get_context(tmp_path, roles_dir=roles_dir)

        assert context == ""

    def test_json_output_format(self, tmp_path):
        from context import get_context_json

        pkg = {"dependencies": {"express": "^4.0.0"}}
        (tmp_path / "package.json").write_text(json.dumps(pkg))

        roles_dir = ROOT / "roles"
        result = get_context_json(tmp_path, roles_dir=roles_dir)
        data = json.loads(result)

        assert "roles" in data
        assert "context" in data
        assert isinstance(data["roles"], list)
        assert len(data["roles"]) > 0

    def test_specific_role_override(self, tmp_path):
        from context import get_context

        roles_dir = ROOT / "roles"
        context = get_context(tmp_path, roles_dir=roles_dir,
                              config_roles=["frontend", "security"])

        assert "ACTIVE ROLES:" in context
        assert "frontend" in context.lower()
        assert "security" in context.lower()

    def test_text_output_includes_manager(self, tmp_path):
        from context import get_context

        pkg = {"dependencies": {"react": "^18.0.0"}}
        (tmp_path / "package.json").write_text(json.dumps(pkg))

        roles_dir = ROOT / "roles"
        context = get_context(tmp_path, roles_dir=roles_dir)

        assert "QUALITY" in context
        assert "SCOPE" in context
