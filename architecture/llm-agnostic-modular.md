# Architecture: LLM-Agnostic Modular Toolkit (Option B)

> Based on: requirements/llm-agnostic-modular.md
> Date: 2026-10-12

## Pattern

**Policy vs transport split**

- **Policy** (host-independent): skill stubs, modules, functions, roles, gate semantics
- **Transport** (per host): detect → YAML config → rules file targets → hooks vs CLI → stamp mode

Orchestrator detects host, merges config, emits short bootstrap + pull_policy. Agents pull depth via MCP/CLI.

## Component diagram

```
┌──────────────┐     ┌─────────────────┐     ┌──────────────────┐
│ agent_detect │────▶│ host_config     │────▶│ bootstrap render │
└──────────────┘     │ load+merge YAML │     └────────┬─────────┘
                     └─────────────────┘              │
                                                      ▼
                     ┌─────────────────┐     ┌──────────────────┐
                     │ orchestrator    │────▶│ plan + pull_policy│
                     └─────────────────┘     └────────┬─────────┘
                                                      │
         ┌────────────────────────────────────────────┼────────────┐
         ▼                    ▼                       ▼            ▼
   get_skill            get_module              get_role     run_function
   (stub)               (one file)              (depth)      (gates)
```

## Directory layout

```
hosts/*.yaml
rules/core.md, skills-index.md, hosts/*.md
skills/<name>/SKILL.md          # stub
skills/<name>/modules/*.md      # depth
skills/<name>/functions/*.py    # deterministic
hooks/host_config.py            # NEW: load/merge
toolkit_mcp/server.py           # NEW tools
scripts/generate_project_rules.py
scripts/toolkit_pull.py         # CLI twin
```

## Host YAML schema

```yaml
id: cursor
rules_targets:
  - AGENTS.md
  - .cursor/rules/toolkit.mdc
skills_path: ~/.cursor/skills   # null if N/A
hooks: structural               # structural | cli_only
hooks_config:
  path: .cursor/hooks.json
  format: cursor
pull: [mcp, cli, read_file]
stamp_mode: cli_stamp           # hook_skill_passed | cli_stamp
bootstrap:
  inject: [rules/core.md, rules/hosts/cursor.md, rules/skills-index.md]
  max_chars: 4000
```

Merge: deep-merge dicts; host list/scalar overrides default.

## Local / cheap option

Pure Python 3.9+, no new dependencies. YAML via stdlib-safe subset: prefer JSON for hosts if PyYAML not present — **decision: use JSON `hosts/*.json` OR minimal YAML subset parser**.

**Decision D1:** Use **JSON** for host configs (`hosts/*.json`) to avoid new deps. Docs may call them "host config"; filenames `.json`. (Alternative: vendored minimal YAML — reject for v1.)

## API design

| Tool | Impl module |
|------|-------------|
| resolve_host | host_config.resolve_host(stdin_payload?) |
| get_bootstrap | host_config.render_bootstrap(cfg) |
| get_skill | skill_pull.get_skill |
| get_module | skill_pull.get_module |
| get_role | wrap load_role_context depth |
| run_function | skill_pull.run_function |
| stamp_skill | writes `.gates/stamps/<name>` |

## Security

- `project_dir` / module paths confined under TOOLKIT_ROOT and optional project root allowlist
- `run_function` allowlist registry only (no arbitrary import path from user)
- Bootstrap max_chars hard cap

## Concurrency

N/A — local stdio MCP, file reads.

## Migration

1. Keep existing long SKILL.md content by moving to `modules/full.md` or split modules; stub becomes new SKILL.md
2. Claude install unchanged except detect can resolve_host for future session_init injection
3. `docs/other-llms.md` → real generate script

## Extendability

New host = new `hosts/<id>.json` + detect signal + `rules/hosts/<id>.md` + fixture test. No skill forks.

## Decisions log

| ID | Decision | Why |
|----|----------|-----|
| D1 | Host configs as JSON | Zero new deps |
| D2 | v1 stubify implementation + precommit only | Scope |
| D3 | Functions live under skills/*/functions or shared functions/ | Shared `hooks/functions/` for cross-skill gates (tdd, gate_status); skill-local optional later |
| D4 | generate_project_rules in Python | Testable; shell wrapper optional |
