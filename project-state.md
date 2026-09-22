# Project state — agent-toolkit

**Last updated:** 2026-09-16

## Resume in a new session

1. `rm -rf .session` in repo root (clears harness hard stop if tripped).
2. Read this file and [`README.md`](README.md). Gate details: [`shared/gate-unlock.md`](shared/gate-unlock.md).

## Current branch

`main` — single `"mode"` field in `gates.json` controls all enforcement. Default mode: `"default"` (TDD + precommit). Seven modes: minimal, tdd, planned, guarded, default, standard, safe. `report_protect` and `gate_protect` both **true** by default. Signed mode optional via `scripts/setup-signed-gates.sh`.

## Recently shipped

| Item | Note |
|------|------|
| Anti-fake: G-REPORT-1 (`report_protect`) | `session_monitor` blocks agent writes to `reports/` |
| Hook-owned gated skill reports | `finalize_report.py` (+ `finalize_schema.py`, `finalize_render.py`) — precommit, evaluate, reviewer, assess |
| Selective gate cleanup | `gate_cleanup.py` — commit clears precommit only; push clears evaluate/reviewer/assess |
| `gate_hook.py` refactor | Smaller helpers; signed mode blocks when verify fails/unavailable |
| `finalize_report.py` split | Schema, render, and common modules extracted from monolith |
| `setup_modes.py` split | Data and I/O in `setup_modes_data.py` / `setup_modes_io.py` |
| CI workflow consolidated | Single `.github/workflows/agent-toolkit-gate.yml` (pytest + hooks + attest) |
| `update.sh` retry + honest exit | Retries twice, logs to stderr, exits 1 on failure; `session_init` surfaces errors |
| Auto pull + sync | `update.sh` on session start and before each skill |
| Hook integrity checks toolkit path | `session_init` uses toolkit clone, not `project/hooks/` |
| G-GATE-1 default on | `gate_protect: true`; finalize writes `.gates/*-passed` |
| `session_monitor` split | `session_state.py`, `path_protection.py`, `session_limits.py` |
| Docs hub | `docs/README.md`, slim README, workflow/install guides |
| ~~TDD strict mode (F2.1–F2.6)~~ | ~~Replaced by mode system~~ — TDD enforcement now controlled by mode (`tdd`, `default`, `standard`, `safe` all enable it) |
| Demo prompt (F3.2–F3.3) | `skill_passed.py` injects demo reminder after `/implementation` (new features only) |
| Auto-restart built-in | `continue: true` (default) — hook spawns background restarter that relaunches `claude` after session exit |
| `continue: false` keeps session alive | Limits only warn, no handoff/stop — killing without restart is pointless |
| `path_protection.py` consolidated | Single `PROTECTED_PATHS` table, eliminated 3x duplication |
| `finalize_render.py` deduped | Shared `_report_header` and `_append_summary_and_gate` helpers |
| `test_gate.py` graceful skip | `pytest.importorskip("jwt")` when cryptography has arch mismatch |
| Consolidated mode system | 5 config axes (profile/tdd/tdd_mode/enforcement/mode) → single `"mode"` field with 7 named modes. `mode_resolver.py` is single source of truth. Net -560 lines. |
| `/agent-toolkit-mode` command | Switch mode mid-session: `/agent-toolkit-mode safe`. Updates `gates.json` live. |
| Role detection tests complete | All 17 roles in `ROLE_SIGNALS` now have detection tests (was 7/17) |

## Structural hooks (9)

| # | Hook | Location | Events |
|---|------|----------|--------|
| 1 | `session_init.py` | `hooks/` | SessionStart, PostCompact |
| 2 | `session_monitor.py` | `hooks/` | PreToolUse, PostToolUse, UserPromptSubmit, PostCompact |
| 3 | `route_to_skill.py` | `hooks/` | UserPromptSubmit |
| 4 | `gate_hook.py` | `hooks/` | PreToolUse (git commit/push) |
| 5 | `skill_passed.py` | `hooks/` | PostToolUse (Skill) |
| 6 | `tdd_enforce.py` | `hooks/` | PreToolUse (Edit/Write) |
| 7 | `check_doc_write.sh` | `hooks/` | PreToolUse (Write) |
| 8 | `gate_cleanup.py` | `hooks/` | PostToolUse (Bash git commit) |
| 9 | `update.sh` | repo root | Session start + PreToolUse (Skill) |

**Report writer (explicit, not a Claude hook event):** `hooks/finalize_report.py`

## In progress

None.

## Open work

- Optional: commit untracked `reports/` if keeping CI fixtures in-repo

## Verified fixes (2026-05-24)

| Issue | True? | Fix kept |
|-------|-------|----------|
| Hook integrity checked `project/hooks/` | Yes (not `.agent-toolkit/hooks/`) | `session_init` → toolkit path + settings.json |
| finalize used `Path.cwd()` | Yes | `resolve_project_root()` from git / `.scratch` hint |
| Duplicate settings.json hooks | Yes (can recur on re-install) | `install.sh` dedupe pass |
| Missing `test_command` → wrong Python | Partially — auto-detect already uses venv; explicit `python3` in custom command did not | `_normalize_python_cmd`; no template override (auto-detect stays default) |
| Signed verify silent OSError fallback | Yes | `gate_hook.py` logs and blocks |
| Duplicate CI workflows | Yes | Merged into `agent-toolkit-gate.yml` |
| `update.sh` swallowed failures | Yes | Retries + exit 1; stderr no longer redirected in hook command |

## Tests

```bash
python3 -m pytest tests/ -q        # 910 passed
bash tests/test-hooks.sh            # 33 passed
```


## Session Summary (2026-09-22)

**Skills used:** /precommit
**Files changed:** findings.json, skill_enforce.py, test_skill_enforce.py
**Tests:** 925 passed

## Test Plans

### reviewer-findings-fix-slabs-2-4 (2026-09-14)

- session-log-exact-match: find_latest_session_log uses exact match, not substring → tests/test_session_log.py:test_exact_match_no_cross_project
- session-log-finds-correct: Exact match finds the right project even with similar names → tests/test_session_log.py:test_exact_match_finds_correct
- session-log-missing: Returns None when no log dir exists → tests/test_session_log.py:test_missing_log_dir
- session-limits-hard-stop: apply_session_limits returns hard stop message → tests/test_session_limits.py:test_hard_stop_returns_message
- session-limits-checkpoint: apply_session_limits returns checkpoint on compact threshold → tests/test_session_limits.py:test_compact_threshold_returns_checkpoint
- session-limits-warning: apply_session_limits returns warning message → tests/test_session_limits.py:test_warning_returns_message
- skill-enforce-pre-code-block: PRE_CODE_SKILLS block code edits in block mode → tests/test_skill_enforce.py:test_pre_code_skill_blocks_in_block_mode
- skill-enforce-pre-code-warn: PRE_CODE_SKILLS warn in remind mode → tests/test_skill_enforce.py:test_pre_code_skill_warns_in_remind_mode
- context-cursor-setup: setup_for_project writes .cursor/rules/roles.md → tests/test_context.py:test_cursor_writes_rules_file
- context-gemini-setup: setup_for_project writes .gemini/rules/roles.md → tests/test_context.py:test_gemini_writes_rules_file
- context-generic-setup: setup_for_project writes AGENTS.md → tests/test_context.py:test_generic_writes_agents_md
- taxonomy-keyword-priority: Implementation keywords take priority over read-only keywords → tests/test_taxonomy_enforce.py:test_mixed_review_and_fix_gets_tdd
- Edge cases: Cross-project slug substring match (foo vs foobar), Missing or empty log directory, PRE_CODE_SKILLS in both block and remind modes, Mixed read-only + implementation keywords in same prompt

### compliance-split-refactor (2026-09-14)

- backward-compat-tracker: ComplianceTracker importable from compliance → tests/test_compliance.py:test_record_obeyed
- backward-compat-evidence: verify_evidence importable from compliance → tests/test_compliance.py:test_no_evidence_fails
- backward-compat-audit: audit_session_actions importable from compliance → tests/test_compliance.py:test_detects_server_start
- backward-compat-diff: check_diff_for_untested_functions importable from compliance → tests/test_compliance.py:test_detects_new_function_without_test
- backward-compat-test-plan: validate_test_plan importable from compliance → tests/test_compliance.py:test_valid_plan
- backward-compat-summary: generate_session_summary importable from compliance → tests/test_compliance.py:test_empty_log
- Edge cases: All existing imports from compliance still work (re-exports), No circular imports between submodules

### consolidate-modes (2026-09-15)

- TC1: resolve_mode returns correct flags for minimal → tests/test_mode_resolver.py:test_minimal_mode
- TC2: resolve_mode returns correct flags for tdd → tests/test_mode_resolver.py:test_tdd_mode
- TC3: resolve_mode returns correct flags for planned → tests/test_mode_resolver.py:test_planned_mode
- TC4: resolve_mode returns correct flags for guarded → tests/test_mode_resolver.py:test_guarded_mode
- TC5: resolve_mode returns correct flags for default → tests/test_mode_resolver.py:test_default_mode
- TC6: resolve_mode returns correct flags for standard → tests/test_mode_resolver.py:test_standard_mode
- TC7: resolve_mode returns correct flags for safe → tests/test_mode_resolver.py:test_safe_mode
- TC8: resolve_mode falls back to default for unknown mode → tests/test_mode_resolver.py:test_unknown_mode_falls_back
- TC9: resolve_mode respects AGENT_TOOLKIT_MODE env var override → tests/test_mode_resolver.py:test_env_var_override
- TC10: required_skills_for_commit returns correct skills per mode → tests/test_mode_resolver.py:test_required_skills_for_commit
- TC11: required_skills_for_push returns reviewer for safe mode → tests/test_mode_resolver.py:test_required_skills_for_push_safe
- TC12: is_tdd_enforced returns True only for modes with tdd → tests/test_mode_resolver.py:test_is_tdd_enforced
- TC13: is_plan_enforced returns True only for modes with plan → tests/test_mode_resolver.py:test_is_plan_enforced
- Edge cases: unknown mode name, env var override, None/empty mode string

### agent-toolkit-mode (2026-09-16)

- TC1: set_mode updates gates.json mode field → tests/test_mode_resolver.py:test_set_mode_updates_gates_json
- TC2: set_mode rejects invalid mode names → tests/test_mode_resolver.py:test_set_mode_rejects_invalid
- TC3: set_mode preserves other gates.json fields → tests/test_mode_resolver.py:test_set_mode_preserves_other_fields
- TC4: set_mode creates gates.json if missing → tests/test_mode_resolver.py:test_set_mode_creates_gates_json
- Edge cases: invalid mode name, missing gates.json, preserves unrelated fields
