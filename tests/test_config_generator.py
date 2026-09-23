"""Tests for scripts/config_generator.py — multi-tool config generation."""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from config_generator import (
    SUPPORTED_TOOLS,
    ToolkitHook,
    collect_toolkit_hooks,
    generate_claude_code,
    generate_codex_cli,
    generate_cursor,
    generate_grok_build,
    generate_windsurf,
    generate_all,
)


# --- ToolkitHook data class ---


class TestToolkitHook:
    def test_create(self):
        h = ToolkitHook(
            event="PreToolUse",
            matcher="Bash",
            command="python3 hooks/gate_hook.py",
            timeout=5,
        )
        assert h.event == "PreToolUse"
        assert h.matcher == "Bash"
        assert h.command == "python3 hooks/gate_hook.py"
        assert h.timeout == 5


# --- collect_toolkit_hooks ---


class TestCollectToolkitHooks:
    def test_collects_from_toolkit(self):
        hooks = collect_toolkit_hooks(ROOT)
        assert len(hooks) > 0
        events = {h.event for h in hooks}
        assert "PreToolUse" in events
        assert "PostToolUse" in events
        assert "UserPromptSubmit" in events

    def test_all_hooks_have_commands(self):
        hooks = collect_toolkit_hooks(ROOT)
        for h in hooks:
            assert h.command, f"Hook {h.event}/{h.matcher} has no command"

    def test_hooks_reference_existing_scripts(self):
        hooks = collect_toolkit_hooks(ROOT)
        for h in hooks:
            # Extract script path from command
            parts = h.command.split()
            script = parts[-1] if parts else ""
            # Only check python scripts (not bash -c or || true patterns)
            if script.endswith(".py"):
                script_name = Path(script).name
                assert (ROOT / "hooks" / script_name).exists(), (
                    f"Hook references {script_name} but it doesn't exist"
                )


# --- Claude Code output ---


class TestGenerateClaudeCode:
    def test_produces_valid_json(self):
        hooks = collect_toolkit_hooks(ROOT)
        result = generate_claude_code(hooks, ROOT)
        parsed = json.loads(result)
        assert "hooks" in parsed

    def test_contains_pre_tool_use(self):
        hooks = collect_toolkit_hooks(ROOT)
        result = generate_claude_code(hooks, ROOT)
        parsed = json.loads(result)
        assert "PreToolUse" in parsed["hooks"]

    def test_contains_post_tool_use(self):
        hooks = collect_toolkit_hooks(ROOT)
        result = generate_claude_code(hooks, ROOT)
        parsed = json.loads(result)
        assert "PostToolUse" in parsed["hooks"]


# --- Cursor output ---


class TestGenerateCursor:
    def test_produces_valid_json(self):
        hooks = collect_toolkit_hooks(ROOT)
        result = generate_cursor(hooks, ROOT)
        parsed = json.loads(result)
        assert "hooks" in parsed

    def test_uses_camelcase_events(self):
        hooks = collect_toolkit_hooks(ROOT)
        result = generate_cursor(hooks, ROOT)
        parsed = json.loads(result)
        hook_keys = set(parsed["hooks"].keys())
        # Cursor uses camelCase event names
        assert "preToolUse" in hook_keys or "PreToolUse" in hook_keys


# --- Codex CLI output ---


class TestGenerateCodexCli:
    def test_produces_toml_string(self):
        hooks = collect_toolkit_hooks(ROOT)
        result = generate_codex_cli(hooks, ROOT)
        assert "[hooks]" in result or "[[hooks." in result

    def test_contains_pre_tool_use(self):
        hooks = collect_toolkit_hooks(ROOT)
        result = generate_codex_cli(hooks, ROOT)
        assert "PreToolUse" in result


# --- Grok Build output ---


class TestGenerateGrokBuild:
    def test_produces_valid_json(self):
        hooks = collect_toolkit_hooks(ROOT)
        result = generate_grok_build(hooks, ROOT)
        parsed = json.loads(result)
        assert "hooks" in parsed

    def test_contains_pre_tool_use(self):
        hooks = collect_toolkit_hooks(ROOT)
        result = generate_grok_build(hooks, ROOT)
        parsed = json.loads(result)
        assert "PreToolUse" in parsed["hooks"]


# --- Windsurf output ---


class TestGenerateWindsurf:
    def test_produces_valid_json(self):
        hooks = collect_toolkit_hooks(ROOT)
        result = generate_windsurf(hooks, ROOT)
        parsed = json.loads(result)
        assert "hooks" in parsed or "cascade_hooks" in parsed


# --- generate_all ---


class TestGenerateAll:
    def test_returns_all_supported_tools(self):
        hooks = collect_toolkit_hooks(ROOT)
        results = generate_all(hooks, ROOT)
        assert set(results.keys()) == set(SUPPORTED_TOOLS)

    def test_all_outputs_non_empty(self):
        hooks = collect_toolkit_hooks(ROOT)
        results = generate_all(hooks, ROOT)
        for tool, output in results.items():
            assert len(output) > 10, f"{tool} output is too short"

    def test_write_to_directory(self, tmp_path):
        hooks = collect_toolkit_hooks(ROOT)
        results = generate_all(hooks, ROOT)
        for tool, content in results.items():
            out_file = tmp_path / f"{tool}.config"
            out_file.write_text(content)
            assert out_file.exists()
            assert out_file.stat().st_size > 0
