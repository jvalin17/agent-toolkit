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


# --- Compaction event per host ---


class TestCompactionEvent:
    """PostCompact is not a real hook event anywhere; each host gets its native name."""

    def _monitor_hooks(self, groups):
        return [h for g in groups for h in g["hooks"] if "session_monitor" in h["command"]]

    def test_no_generator_emits_postcompact(self):
        for tool, output in generate_all(collect_toolkit_hooks(ROOT), ROOT).items():
            assert "PostCompact" not in output, f"{tool} still emits PostCompact"

    def test_claude_code_uses_session_start_compact(self):
        parsed = json.loads(generate_claude_code(collect_toolkit_hooks(ROOT), ROOT))
        compact = [g for g in parsed["hooks"]["SessionStart"] if g["matcher"] == "compact"]
        assert len(compact) == 1
        assert len(self._monitor_hooks(compact)) == 1

    def test_grok_build_uses_session_start_compact(self):
        parsed = json.loads(generate_grok_build(collect_toolkit_hooks(ROOT), ROOT))
        compact = [g for g in parsed["hooks"]["SessionStart"] if g["matcher"] == "compact"]
        assert len(self._monitor_hooks(compact)) == 1

    def test_cursor_uses_precompact(self):
        parsed = json.loads(generate_cursor(collect_toolkit_hooks(ROOT), ROOT))
        assert "preCompact" in parsed["hooks"]
        assert len(self._monitor_hooks(parsed["hooks"]["preCompact"])) == 1
        assert all("matcher" not in g for g in parsed["hooks"]["preCompact"])

    def test_windsurf_uses_post_compact(self):
        parsed = json.loads(generate_windsurf(collect_toolkit_hooks(ROOT), ROOT))
        monitors = [h for h in parsed["hooks"]["post-compact"] if "session_monitor" in h["command"]]
        assert len(monitors) == 1

    def test_codex_uses_session_start_compact(self):
        output = generate_codex_cli(collect_toolkit_hooks(ROOT), ROOT)
        assert "[[hooks.SessionStart]]" in output
        assert 'matcher = "compact"' in output


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
