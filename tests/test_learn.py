#!/usr/bin/env python3
"""Tests for roles/learn.py — fetcher/learning system for role knowledge."""

import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "roles"))


# --- Fetch ---


class TestFetch:
    def test_fetch_local_path(self, tmp_path):
        from learn import fetch

        project = tmp_path / "my-project"
        project.mkdir()
        (project / "package.json").write_text('{"name": "test"}')
        (project / "src").mkdir()
        (project / "src" / "index.ts").write_text("console.log('hello');")

        result = fetch("path", str(project), tmp_path / "cache")
        assert result.source_type == "path"
        assert result.path == project
        assert result.path.is_dir()

    def test_fetch_local_path_not_exists(self, tmp_path):
        from learn import fetch

        with pytest.raises(ValueError, match="not a directory"):
            fetch("path", str(tmp_path / "nope"), tmp_path / "cache")

    def test_fetch_url_saves_markdown(self, tmp_path):
        from learn import fetch

        cache = tmp_path / "cache"
        # Mock HTTP response
        with patch("learn.httpx") as mock_httpx:
            mock_resp = MagicMock()
            mock_resp.text = "<html><body><h1>Title</h1><p>Content here</p></body></html>"
            mock_resp.status_code = 200
            mock_httpx.get.return_value = mock_resp

            result = fetch("url", "https://example.com/blog/post", cache)

        assert result.source_type == "article"
        assert result.path.exists()
        content = result.path.read_text()
        assert "Title" in content or "Content" in content

    def test_fetch_repo_clones(self, tmp_path):
        from learn import fetch

        cache = tmp_path / "cache"
        # Mock git clone
        with patch("learn.subprocess") as mock_sub:
            mock_sub.run.return_value = MagicMock(returncode=0)

            result = fetch("repo", "https://github.com/test/repo", cache)

        assert result.source_type == "repo"
        mock_sub.run.assert_called_once()
        call_args = mock_sub.run.call_args[0][0]
        assert "git" in call_args
        assert "clone" in call_args


# --- Extract ---


class TestExtractRepo:
    def test_extracts_package_json(self, tmp_path):
        from learn import extract_repo

        (tmp_path / "package.json").write_text('{"dependencies": {"express": "4"}}')
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "index.ts").write_text("import express from 'express';")

        result = extract_repo(tmp_path)
        assert "package.json" in result.file_tree
        assert any("package.json" in f for f in result.files)

    def test_extracts_file_tree(self, tmp_path):
        from learn import extract_repo

        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "routes").mkdir()
        (tmp_path / "src" / "routes" / "users.ts").write_text("// users")
        (tmp_path / "src" / "models").mkdir()
        (tmp_path / "src" / "models" / "user.ts").write_text("// user model")

        result = extract_repo(tmp_path)
        assert "src" in result.file_tree
        assert "routes" in result.file_tree

    def test_extracts_routes_and_models(self, tmp_path):
        from learn import extract_repo

        (tmp_path / "src").mkdir()
        routes = tmp_path / "src" / "routes"
        routes.mkdir()
        (routes / "users.ts").write_text("export const usersRouter = Router();")
        models = tmp_path / "src" / "models"
        models.mkdir()
        (models / "user.ts").write_text("export class User { id: number; }")

        result = extract_repo(tmp_path)
        file_paths = [f for f in result.files]
        assert any("routes" in f for f in file_paths)
        assert any("models" in f for f in file_paths)

    def test_caps_content_at_limit(self, tmp_path):
        from learn import extract_repo

        (tmp_path / "big.ts").write_text("x" * 100000)

        result = extract_repo(tmp_path)
        assert len(result.to_text()) <= 35000  # ~8K tokens with margin

    def test_ignores_node_modules(self, tmp_path):
        from learn import extract_repo

        nm = tmp_path / "node_modules"
        nm.mkdir()
        (nm / "express").mkdir()
        (nm / "express" / "index.js").write_text("// express")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "app.ts").write_text("// app")

        result = extract_repo(tmp_path)
        assert "node_modules" not in result.file_tree

    def test_extracts_readme(self, tmp_path):
        from learn import extract_repo

        (tmp_path / "README.md").write_text("# My Project\n\nA great project.")

        result = extract_repo(tmp_path)
        assert any("README" in f for f in result.files)


class TestExtractArticle:
    def test_extracts_markdown_content(self, tmp_path):
        from learn import extract_article

        article = tmp_path / "post.md"
        article.write_text("# Great Blog Post\n\nHere is the content about patterns.")

        result = extract_article(article)
        text = result.to_text()
        assert "Great Blog Post" in text
        assert "patterns" in text

    def test_caps_long_articles(self, tmp_path):
        from learn import extract_article

        article = tmp_path / "long.md"
        article.write_text("word " * 50000)

        result = extract_article(article)
        assert len(result.to_text()) <= 35000


# --- Study ---


class TestStudy:
    def test_study_builds_role_specific_prompt(self, tmp_path):
        from learn import study, ExtractResult

        # Create a role definition
        role_dir = tmp_path / "roles" / "backend"
        role_dir.mkdir(parents=True)
        (role_dir / "role.md").write_text(
            "---\nname: backend\nscope: API development\n"
            "not_scope: UI rendering\n---\n\n## Advisory\n\nBackend role.\n"
        )

        extracted = ExtractResult()
        extracted.add_content("app.ts", "import express from 'express';")
        source_info = {"name": "test-repo", "type": "repo", "url_or_path": "/test"}

        with patch("learn.call_llm") as mock_llm:
            mock_llm.return_value = "## Patterns\n- Express middleware chain"

            knowledge = study("backend", extracted, source_info,
                              roles_dir=tmp_path / "roles")

        assert knowledge.role == "backend"
        assert knowledge.content == "## Patterns\n- Express middleware chain"
        # Verify the prompt included role scope
        prompt_sent = mock_llm.call_args[0][0]
        assert "API development" in prompt_sent
        assert "UI rendering" in prompt_sent  # not_scope should be in prompt

    def test_study_includes_extracted_content(self, tmp_path):
        from learn import study, ExtractResult

        role_dir = tmp_path / "roles" / "frontend"
        role_dir.mkdir(parents=True)
        (role_dir / "role.md").write_text(
            "---\nname: frontend\nscope: UI\nnot_scope: backend\n---\n\n## Advisory\n\nFE.\n"
        )

        extracted = ExtractResult()
        extracted.add_content("App.tsx", "function App() { return <div>Hello</div> }")
        source_info = {"name": "test-app", "type": "repo", "url_or_path": "/test"}

        with patch("learn.call_llm") as mock_llm:
            mock_llm.return_value = "## Patterns\n- Functional components"
            study("frontend", extracted, source_info, roles_dir=tmp_path / "roles")

        prompt_sent = mock_llm.call_args[0][0]
        assert "App.tsx" in prompt_sent
        assert "Hello" in prompt_sent


# --- Store ---


class TestStore:
    def test_saves_knowledge_file(self, tmp_path):
        from learn import store, Knowledge

        knowledge = Knowledge(
            role="backend",
            source={"name": "test-repo", "type": "repo", "url_or_path": "https://github.com/test"},
            content="## Patterns\n- Express middleware",
            studied_at="2026-08-16T10:00:00",
        )

        path = store(knowledge, roles_dir=tmp_path)
        assert path.exists()
        content = path.read_text()
        assert "Express middleware" in content
        assert "github.com/test" in content

    def test_creates_role_knowledge_dir(self, tmp_path):
        from learn import store, Knowledge

        knowledge = Knowledge(
            role="frontend",
            source={"name": "react-patterns", "type": "url", "url_or_path": "https://example.com"},
            content="## Patterns\n- Hooks",
            studied_at="2026-08-16T10:00:00",
        )

        store(knowledge, roles_dir=tmp_path)
        assert (tmp_path / "frontend" / "knowledge").is_dir()

    def test_updates_sources_json(self, tmp_path):
        from learn import store, Knowledge

        knowledge = Knowledge(
            role="backend",
            source={"name": "test-repo", "type": "repo", "url_or_path": "https://github.com/test"},
            content="## Patterns\n- Middleware",
            studied_at="2026-08-16T10:00:00",
        )

        store(knowledge, roles_dir=tmp_path)
        sources_file = tmp_path / "backend" / "sources.json"
        assert sources_file.exists()
        sources = json.loads(sources_file.read_text())
        assert len(sources) == 1
        assert sources[0]["name"] == "test-repo"

    def test_appends_to_existing_sources(self, tmp_path):
        from learn import store, Knowledge

        # Store first
        k1 = Knowledge(
            role="backend",
            source={"name": "repo-1", "type": "repo", "url_or_path": "/1"},
            content="## P1", studied_at="2026-08-16T10:00:00",
        )
        store(k1, roles_dir=tmp_path)

        # Store second
        k2 = Knowledge(
            role="backend",
            source={"name": "repo-2", "type": "repo", "url_or_path": "/2"},
            content="## P2", studied_at="2026-08-16T11:00:00",
        )
        store(k2, roles_dir=tmp_path)

        sources = json.loads((tmp_path / "backend" / "sources.json").read_text())
        assert len(sources) == 2


# --- Synthesize ---


class TestSynthesize:
    def test_merges_knowledge_files(self, tmp_path):
        from learn import synthesize

        # Create knowledge files
        kdir = tmp_path / "backend" / "knowledge"
        kdir.mkdir(parents=True)
        (kdir / "repo-1.md").write_text("## Patterns\n- Middleware chain\n- Error handling")
        (kdir / "repo-2.md").write_text("## Patterns\n- Rate limiting\n- Validation")

        # Create role definition
        role_dir = tmp_path / "backend"
        (role_dir / "role.md").write_text(
            "---\nname: backend\nscope: API\nnot_scope: UI\n---\n\n## Advisory\n\nBE.\n"
        )

        with patch("learn.call_llm") as mock_llm:
            mock_llm.return_value = (
                "## Advisory Context\nBackend patterns.\n\n"
                "## Patterns\n- Middleware\n- Rate limiting\n\n"
                "## Anti-Patterns + Fixes\n- N+1 → eager loading"
            )
            result = synthesize("backend", roles_dir=tmp_path)

        assert result.exists()
        assert result.name == "_synthesis.md"
        content = result.read_text()
        assert "Middleware" in content
        assert "backend" in content

    def test_raises_if_no_knowledge(self, tmp_path):
        from learn import synthesize

        role_dir = tmp_path / "backend"
        role_dir.mkdir(parents=True)
        (role_dir / "role.md").write_text("---\nname: backend\n---\n")

        with pytest.raises(ValueError, match="No knowledge files"):
            synthesize("backend", roles_dir=tmp_path)

    def test_skips_synthesis_file_as_input(self, tmp_path):
        from learn import synthesize

        kdir = tmp_path / "backend" / "knowledge"
        kdir.mkdir(parents=True)
        (kdir / "repo-1.md").write_text("## Patterns\n- Express")
        (kdir / "_synthesis.md").write_text("## Old synthesis\n- Old stuff")

        role_dir = tmp_path / "backend"
        (role_dir / "role.md").write_text(
            "---\nname: backend\nscope: API\nnot_scope: UI\n---\n"
        )

        with patch("learn.call_llm") as mock_llm:
            mock_llm.return_value = "## New synthesis"
            synthesize("backend", roles_dir=tmp_path)

        # Verify only repo-1.md was sent to LLM, not _synthesis.md
        prompt_sent = mock_llm.call_args[0][0]
        assert "Old stuff" not in prompt_sent
        assert "Express" in prompt_sent


# --- Health Check ---


class TestHealthCheck:
    def test_no_knowledge_reports_gap(self, tmp_path):
        from learn import check_role_health

        role_dir = tmp_path / "backend"
        role_dir.mkdir()
        (role_dir / "role.md").write_text("---\nname: backend\n---\n")

        report = check_role_health("backend", roles_dir=tmp_path)
        assert any("NO_KNOWLEDGE" in g["type"] for g in report.gaps)

    def test_healthy_role_no_gaps(self, tmp_path):
        from learn import check_role_health

        kdir = tmp_path / "backend" / "knowledge"
        kdir.mkdir(parents=True)
        (kdir / "_synthesis.md").write_text(
            "## advisory\ntest\n## anti_patterns\ntest\n"
            "## quality_checks\ntest\n## bug_fixes\ntest"
        )
        (tmp_path / "backend" / "role.md").write_text("---\nname: backend\n---\n")

        report = check_role_health("backend", roles_dir=tmp_path)
        assert len(report.gaps) == 0


# --- Slug ---


class TestCallLLM:
    def test_calls_anthropic_api(self, monkeypatch):
        from learn import call_llm

        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [{"type": "text", "text": "## Patterns\n- Middleware chain"}],
        }

        with patch("learn.httpx.post", return_value=mock_response) as mock_post:
            result = call_llm("test prompt", model="sonnet")

        assert "Middleware chain" in result
        # Verify correct model was sent
        call_json = mock_post.call_args[1]["json"]
        assert call_json["model"] == "claude-sonnet-4-6"
        assert call_json["messages"][0]["content"] == "test prompt"

    def test_opus_model_mapping(self, monkeypatch):
        from learn import call_llm

        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [{"type": "text", "text": "synthesis"}],
        }

        with patch("learn.httpx.post", return_value=mock_response) as mock_post:
            call_llm("test", model="opus")

        call_json = mock_post.call_args[1]["json"]
        assert call_json["model"] == "claude-opus-4-6"

    def test_raises_without_api_key(self, monkeypatch):
        from learn import call_llm

        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
            call_llm("test")

    def test_raises_on_api_error(self, monkeypatch):
        from learn import call_llm

        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Invalid API key"

        with patch("learn.httpx.post", return_value=mock_response):
            with pytest.raises(RuntimeError, match="401"):
                call_llm("test")

    def test_supports_full_model_id(self, monkeypatch):
        from learn import call_llm

        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [{"type": "text", "text": "ok"}],
        }

        with patch("learn.httpx.post", return_value=mock_response) as mock_post:
            call_llm("test", model="claude-sonnet-4-6")

        call_json = mock_post.call_args[1]["json"]
        assert call_json["model"] == "claude-sonnet-4-6"


class TestSlug:
    def test_url_to_slug(self):
        from learn import slug

        assert slug("https://github.com/nestjs/nest") == "nestjs-nest"

    def test_path_to_slug(self):
        from learn import slug

        assert slug("/Users/me/projects/my-app") == "my-app"

    def test_strips_special_chars(self):
        from learn import slug

        result = slug("https://example.com/blog/my-great-post?v=2")
        assert "?" not in result
        assert "=" not in result
