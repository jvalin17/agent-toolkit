#!/usr/bin/env python3
"""Tests for detect_role.py — role detection from project signals."""

import json
from pathlib import Path

import pytest
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "roles"))


class TestDetectRolesFromFiles:
    """Detect roles based on file existence in project directory."""

    def test_empty_project_returns_no_roles(self, tmp_path):
        from detect_role import detect_roles

        result = detect_roles(tmp_path)
        assert result == []

    def test_detects_frontend_from_package_json_with_react(self, tmp_path):
        from detect_role import detect_roles

        pkg = {"dependencies": {"react": "^18.0.0"}}
        (tmp_path / "package.json").write_text(json.dumps(pkg))

        result = detect_roles(tmp_path)
        role_names = [r["name"] for r in result]
        assert "frontend" in role_names

    def test_detects_backend_from_express(self, tmp_path):
        from detect_role import detect_roles

        pkg = {"dependencies": {"express": "^4.0.0"}}
        (tmp_path / "package.json").write_text(json.dumps(pkg))

        result = detect_roles(tmp_path)
        role_names = [r["name"] for r in result]
        assert "backend" in role_names

    def test_detects_backend_from_fastapi(self, tmp_path):
        from detect_role import detect_roles

        (tmp_path / "requirements.txt").write_text("fastapi==0.100.0\nuvicorn\n")

        result = detect_roles(tmp_path)
        role_names = [r["name"] for r in result]
        assert "backend" in role_names

    def test_detects_ios_from_podfile(self, tmp_path):
        from detect_role import detect_roles

        (tmp_path / "Podfile").write_text("platform :ios, '17.0'\n")

        result = detect_roles(tmp_path)
        role_names = [r["name"] for r in result]
        assert "ios" in role_names

    def test_detects_ios_from_xcodeproj(self, tmp_path):
        from detect_role import detect_roles

        (tmp_path / "MyApp.xcodeproj").mkdir()

        result = detect_roles(tmp_path)
        role_names = [r["name"] for r in result]
        assert "ios" in role_names

    def test_detects_android_from_build_gradle(self, tmp_path):
        from detect_role import detect_roles

        (tmp_path / "build.gradle").write_text("apply plugin: 'com.android.application'\n")

        result = detect_roles(tmp_path)
        role_names = [r["name"] for r in result]
        assert "android" in role_names

    def test_detects_dba_from_prisma_schema(self, tmp_path):
        from detect_role import detect_roles

        prisma_dir = tmp_path / "prisma"
        prisma_dir.mkdir()
        (prisma_dir / "schema.prisma").write_text("model User { id Int @id }\n")

        result = detect_roles(tmp_path)
        role_names = [r["name"] for r in result]
        assert "dba" in role_names

    def test_detects_dba_from_migrations_dir(self, tmp_path):
        from detect_role import detect_roles

        migrations = tmp_path / "migrations"
        migrations.mkdir()
        (migrations / "001_create_users.sql").write_text("CREATE TABLE users();\n")

        result = detect_roles(tmp_path)
        role_names = [r["name"] for r in result]
        assert "dba" in role_names

    def test_detects_security_from_env_file(self, tmp_path):
        from detect_role import detect_roles

        (tmp_path / ".env").write_text("SECRET_KEY=abc123\n")
        # Security is cross-cutting — also needs some app signals
        pkg = {"dependencies": {"express": "^4.0.0"}}
        (tmp_path / "package.json").write_text(json.dumps(pkg))

        result = detect_roles(tmp_path)
        role_names = [r["name"] for r in result]
        assert "security" in role_names

    def test_detects_infrastructure_from_dockerfile(self, tmp_path):
        from detect_role import detect_roles

        (tmp_path / "Dockerfile").write_text("FROM node:20\n")

        result = detect_roles(tmp_path)
        role_names = [r["name"] for r in result]
        assert "infrastructure" in role_names

    def test_detects_infrastructure_from_terraform(self, tmp_path):
        from detect_role import detect_roles

        tf_dir = tmp_path / "terraform"
        tf_dir.mkdir()
        (tf_dir / "main.tf").write_text('resource "aws_instance" "web" {}\n')

        result = detect_roles(tmp_path)
        role_names = [r["name"] for r in result]
        assert "infrastructure" in role_names


class TestMultiRoleDetection:
    """Full-stack projects should detect multiple roles."""

    def test_fullstack_detects_frontend_and_backend(self, tmp_path):
        from detect_role import detect_roles

        pkg = {"dependencies": {"react": "^18.0.0", "express": "^4.0.0"}}
        (tmp_path / "package.json").write_text(json.dumps(pkg))

        result = detect_roles(tmp_path)
        role_names = [r["name"] for r in result]
        assert "frontend" in role_names
        assert "backend" in role_names

    def test_fullstack_with_db_and_docker(self, tmp_path):
        from detect_role import detect_roles

        pkg = {"dependencies": {"react": "^18.0.0", "express": "^4.0.0"}}
        (tmp_path / "package.json").write_text(json.dumps(pkg))
        prisma_dir = tmp_path / "prisma"
        prisma_dir.mkdir()
        (prisma_dir / "schema.prisma").write_text("model User { id Int @id }\n")
        (tmp_path / "Dockerfile").write_text("FROM node:20\n")
        (tmp_path / ".env").write_text("DATABASE_URL=postgres://...\n")

        result = detect_roles(tmp_path, max_roles=10)
        role_names = [r["name"] for r in result]
        assert "frontend" in role_names
        assert "backend" in role_names
        assert "dba" in role_names
        assert "infrastructure" in role_names
        assert "security" in role_names


class TestRoleRanking:
    """Roles should be ranked by confidence (number of signals matched)."""

    def test_more_signals_means_higher_confidence(self, tmp_path):
        from detect_role import detect_roles

        # Backend has many signals
        pkg = {"dependencies": {"express": "^4.0.0", "prisma": "^5.0.0"}}
        (tmp_path / "package.json").write_text(json.dumps(pkg))
        src = tmp_path / "src"
        src.mkdir()
        routes = src / "routes"
        routes.mkdir()
        (routes / "users.ts").write_text("export const router = express.Router();\n")

        # Infrastructure has one signal
        (tmp_path / "Dockerfile").write_text("FROM node:20\n")

        result = detect_roles(tmp_path)

        # Backend should have higher confidence than infrastructure
        backend = next(r for r in result if r["name"] == "backend")
        infra = next(r for r in result if r["name"] == "infrastructure")
        assert backend["confidence"] >= infra["confidence"]

    def test_results_sorted_by_confidence_descending(self, tmp_path):
        from detect_role import detect_roles

        pkg = {"dependencies": {"react": "^18.0.0", "express": "^4.0.0"}}
        (tmp_path / "package.json").write_text(json.dumps(pkg))
        (tmp_path / "Dockerfile").write_text("FROM node:20\n")

        result = detect_roles(tmp_path)
        confidences = [r["confidence"] for r in result]
        assert confidences == sorted(confidences, reverse=True)


class TestConfigOverride:
    """Manual role configuration overrides auto-detection."""

    def test_explicit_roles_override_detection(self, tmp_path):
        from detect_role import detect_roles

        # Project looks like frontend
        pkg = {"dependencies": {"react": "^18.0.0"}}
        (tmp_path / "package.json").write_text(json.dumps(pkg))

        # But config says only backend
        result = detect_roles(tmp_path, config_roles=["backend"])
        role_names = [r["name"] for r in result]
        assert role_names == ["backend"]

    def test_roles_add_appends_to_detected(self, tmp_path):
        from detect_role import detect_roles

        pkg = {"dependencies": {"react": "^18.0.0"}}
        (tmp_path / "package.json").write_text(json.dumps(pkg))

        result = detect_roles(tmp_path, config_add=["security"])
        role_names = [r["name"] for r in result]
        assert "frontend" in role_names
        assert "security" in role_names

    def test_roles_exclude_removes_from_detected(self, tmp_path):
        from detect_role import detect_roles

        pkg = {"dependencies": {"react": "^18.0.0", "express": "^4.0.0"}}
        (tmp_path / "package.json").write_text(json.dumps(pkg))

        result = detect_roles(tmp_path, config_exclude=["backend"])
        role_names = [r["name"] for r in result]
        assert "frontend" in role_names
        assert "backend" not in role_names

    def test_max_roles_caps_results(self, tmp_path):
        from detect_role import detect_roles

        pkg = {"dependencies": {"react": "^18.0.0", "express": "^4.0.0"}}
        (tmp_path / "package.json").write_text(json.dumps(pkg))
        (tmp_path / "Dockerfile").write_text("FROM node:20\n")
        (tmp_path / ".env").write_text("SECRET=abc\n")

        result = detect_roles(tmp_path, max_roles=2)
        assert len(result) <= 2


class TestLoadRoleContext:
    """Load role preamble text for injection into session context."""

    def test_load_context_for_detected_roles(self, tmp_path):
        from detect_role import load_role_context

        # Create a minimal role.md
        role_dir = tmp_path / "roles" / "backend"
        role_dir.mkdir(parents=True)
        (role_dir / "role.md").write_text(
            "---\nname: backend\nscope: API development\n---\n\n"
            "## Advisory Context\n\nYou are working on a backend project.\n"
        )

        context = load_role_context(["backend"], roles_dir=tmp_path / "roles")
        assert "ACTIVE ROLES: backend" in context
        assert "backend" in context.lower()

    def test_load_context_includes_manager(self, tmp_path):
        from detect_role import load_role_context

        role_dir = tmp_path / "roles" / "backend"
        role_dir.mkdir(parents=True)
        (role_dir / "role.md").write_text(
            "---\nname: backend\nscope: API\n---\n\n## Advisory\n\nBackend role.\n"
        )
        (tmp_path / "roles" / "manager.md").write_text(
            "## Manager Principles\n\n1. QUALITY\n2. SCOPE\n"
        )

        context = load_role_context(["backend"], roles_dir=tmp_path / "roles")
        assert "QUALITY" in context
        assert "SCOPE" in context

    def test_empty_roles_returns_empty_string(self, tmp_path):
        from detect_role import load_role_context

        context = load_role_context([], roles_dir=tmp_path / "roles")
        assert context == ""

    def test_caps_at_max_roles(self, tmp_path):
        from detect_role import load_role_context

        roles_root = tmp_path / "roles"
        for name in ["a", "b", "c", "d", "e"]:
            d = roles_root / name
            d.mkdir(parents=True)
            (d / "role.md").write_text(
                f"---\nname: {name}\nscope: test\n---\n\n## Advisory\n\nRole {name}.\n"
            )

        context = load_role_context(
            ["a", "b", "c", "d", "e"], roles_dir=roles_root, max_roles=3
        )
        # Should only include 3 roles
        assert context.count("## Advisory") <= 3

    def test_loads_synthesis_knowledge(self, tmp_path):
        from detect_role import load_role_context

        roles_root = tmp_path / "roles"
        role_dir = roles_root / "backend"
        role_dir.mkdir(parents=True)
        (role_dir / "role.md").write_text(
            "---\nname: backend\nscope: API\n---\n\n## Advisory\n\nBackend role.\n"
        )
        # Knowledge in JSON index
        (roles_root / "knowledge.json").write_text(json.dumps({
            "backend": "## Best Practices\n\n- Use cursor pagination\n- Connection pooling\n"
        }))

        context = load_role_context(["backend"], roles_dir=roles_root)
        assert "cursor pagination" in context
        assert "Connection pooling" in context
        assert "Practical Patterns" in context

    def test_skips_synthesis_if_missing(self, tmp_path):
        from detect_role import load_role_context

        roles_root = tmp_path / "roles"
        role_dir = roles_root / "frontend"
        role_dir.mkdir(parents=True)
        (role_dir / "role.md").write_text(
            "---\nname: frontend\nscope: UI\n---\n\n## Advisory\n\nFE role.\n"
        )
        # No knowledge.json

        context = load_role_context(["frontend"], roles_dir=roles_root)
        assert "FE role" in context
        assert "Practical Patterns" not in context

    def test_truncates_large_synthesis(self, tmp_path):
        from detect_role import load_role_context

        roles_root = tmp_path / "roles"
        role_dir = roles_root / "backend"
        role_dir.mkdir(parents=True)
        (role_dir / "role.md").write_text(
            "---\nname: backend\n---\n\n## Advisory\n\nBE.\n"
        )
        (roles_root / "knowledge.json").write_text(json.dumps({
            "backend": "x" * 5000
        }))

        context = load_role_context(["backend"], roles_dir=roles_root)
        assert "truncated" in context
