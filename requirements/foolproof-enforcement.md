# Requirements: Foolproof multi-host enforcement

> 2026-10-12 — Phases A–D (user approved)

## Goal

Make Cursor / Codex / Grok / Gemini as hard to bypass as Claude Code for TDD order and commit gates.

## Phases

| Phase | Must |
|-------|------|
| A | `hook_io` wraps detect+normalize; wire into gate/tdd/skill_enforce/session_monitor; fixtures prove Cursor/Grok/Codex commit block |
| B | `install.sh --host <id>` writes absolute-path hooks; test install to tmp |
| C | `atk commit` / `atk-git` CLI wraps git for cli_only hosts |
| D | Codex+Grok fixture suite; Gemini documented as CLI-required |

## Acceptance

1. Cursor payload `Shell` + `git commit` without `.gates/precommit-passed` → JSON includes block/deny  
2. Grok camelCase + Codex shell payloads same  
3. `install.sh --host cursor` creates `.cursor/hooks.json` under chosen project with toolkit absolute paths  
4. `atk commit` refuses when gate missing; succeeds (dry-run) when present  
5. Docs: Gemini must use `atk` for foolproof path  
