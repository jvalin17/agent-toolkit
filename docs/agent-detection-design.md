# Agent Detection Design — Auto-detect AI coding tool and load appropriate config

## Problem

The toolkit needs to detect which AI coding tool is running and automatically load the right hook config format. Currently hooks only work in Claude Code.

## Detection Signals

| Tool | Env Var (best) | Env Var (fallback) | Filesystem | Stdin JSON |
|---|---|---|---|---|
| **Claude Code** | `CLAUDECODE=1` | `CLAUDE_CODE_ENTRYPOINT` | `~/.claude/` | `transcript_path` contains `.claude/` |
| **Cursor** | `CURSOR_CLI` (set in terminal) | `CURSOR_AGENT=1` (buggy) | `.cursor/`, `~/.cursor/` | `cursor_version` in payload |
| **Codex CLI** | `CODEX_SANDBOX` | `CODEX_THREAD_ID` | `.codex/`, `~/.codex/` | `turn_id` in payload |
| **Grok Build** | `GROK_SESSION_ID` | `GROK_HOOK_EVENT` | `.grok/`, `~/.grok/` | `hookEventName` (camelCase) |
| **Windsurf** | _(none)_ | _(none)_ | `.windsurf/`, `.devin/` | `trajectory_id`, `agent_action_name` |

## Detection Algorithm

Priority order (fast to slow):

```
1. Check env vars (instant, no I/O):
   - CLAUDECODE=1          → claude-code
   - GROK_SESSION_ID set   → grok-build
   - CODEX_SANDBOX set     → codex-cli
   - CURSOR_CLI set        → cursor

2. If no env var match, check stdin JSON (hook context only):
   - cursor_version        → cursor
   - trajectory_id         → windsurf
   - hookEventName (camel) → grok-build
   - turn_id               → codex-cli
   - transcript_path has .claude → claude-code

3. If no stdin, check filesystem (fallback):
   - ~/.claude/ exists     → claude-code
   - ~/.grok/ exists       → grok-build
   - ~/.codex/ exists      → codex-cli
   - ~/.cursor/ exists     → cursor
   - ~/.windsurf/ exists   → windsurf
```

## Config Loading

Once detected, use `config_generator.py` to produce the right format:

| Tool | Config location | Format |
|---|---|---|
| Claude Code | `~/.claude/settings.json` | JSON (hooks key) |
| Cursor | `.cursor/hooks.json` | JSON (camelCase events) |
| Codex CLI | `.codex/config.toml` | TOML (hooks section) |
| Grok Build | `.grok/hooks.json` | JSON (same as Claude Code) |
| Windsurf | `.windsurf/hooks.json` | JSON (agent_action_name events) |

## Hook Compatibility

All tools use the same pattern: script receives JSON on stdin, returns JSON on stdout. The differences are:

1. **Event names** — mostly PascalCase, Cursor uses camelCase, Windsurf uses `pre_run_command` style
2. **Stdin schema** — different field names for the same concepts
3. **Blocking mechanism** — exit code 2 = deny (universal), some tools also accept JSON `deny` responses

## Proposed API

```python
from agent_detect import detect_agent, load_agent_config

tool = detect_agent()           # Returns: "claude-code", "cursor", etc.
config = load_agent_config(tool) # Returns: formatted config string
```

The installer (`install.sh`) would call `detect_agent()` and generate the right config format automatically. Session init hooks would also detect and adapt.

## Risks

- **Cursor `CURSOR_AGENT` is buggy** — was accidentally removed and re-added. Use `CURSOR_CLI` as primary.
- **Windsurf has no env vars** — detection requires filesystem or stdin, which is slower.
- **Codex rejected `AGENT=codex` proposal** — no single reliable var; use `CODEX_SANDBOX` which is always set in hook context.
- **Grok Build reads Claude Code config natively** — may not need a separate config at all.

## Open Questions

1. Should we write configs for ALL detected tools or just the active one?
2. Should the installer auto-detect or ask the user?
3. How to handle Grok Build's native Claude Code compatibility — skip config generation?
