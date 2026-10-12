# Other LLMs (Cursor, GPT, Gemini, Grok, & more)

Agent Toolkit aims for **Claude-level foolproofness** on every host:

- **Structural hooks** where the host supports them (Cursor, Codex, Grok, Windsurf) — after `install_host_hooks`
- **`atk` CLI** where hooks are missing (Gemini) or as a belt-and-suspenders backup

Orchestrator detects the host → `hosts/<id>.json` → short bootstrap. Skills are stubs; depth is pulled.

## What works where

| Capability | Claude Code | Cursor / Codex / Grok | Gemini |
|------------|-------------|------------------------|--------|
| Short rules | Yes | Yes | Yes |
| Pull skill/module | MCP + Skill | MCP / CLI | MCP / CLI |
| Block bad commit | Hooks | Hooks after install | **`atk commit` required** |
| TDD / path protect | Hooks | Hooks (normalized via `hook_io`) | Prompt + `atk` |
| Skill stamps | Skill hook (`hook_skill_passed`) | `stamp_skill` MCP / CLI (`cli_stamp`) | `stamp_skill` CLI (`cli_stamp`) |
| Corrupt `gates.json` | Blocks commit/push | Blocks commit/push | `atk` refuses |

### Skill stamps per host

`.gates/stamps/<skill>` proves a skill ran. The host config (`hosts/<id>.json` → `stamp_mode`) decides who may write it:

- **`hook_skill_passed`** (Claude Code): the Skill PostToolUse hook writes the stamp. The `stamp_skill` MCP tool is **blocked** there, and finalize rejects any stamp marked `"source": "cli"` — otherwise an agent could forge `/reviewer` or `/precommit`.
- **`cli_stamp`** (Cursor, Codex, Grok, Windsurf, Gemini, default): there is no Skill hook, so the agent stamps through the tool after running the skill:

```bash
python3 /path/to/agent-toolkit/scripts/toolkit_pull.py stamp_skill reviewer --project .
```

The name must be a real skill (`skills/<name>/SKILL.md`); path separators and `..` are rejected. Stamps are JSON (`skill`, `timestamp`, `source`) on every host, so the stale-precommit check works the same everywhere.

## Foolproof setup

### Cursor / Codex / Grok / Windsurf

```bash
# From your project root — writes hooks + short AGENTS.md
/path/to/agent-toolkit/install.sh --host cursor --project .
# or: python3 /path/to/agent-toolkit/scripts/install_host_hooks.py --host cursor --project .
```

Hosts: `cursor`, `codex-cli`, `grok-build`, `windsurf`.

Hooks call the same Python as Claude (`gate_hook`, `tdd_enforce`, …) with **stdin normalized** so camelCase / Shell / turn_id payloads still block.

### Gemini (CLI-only)

```bash
/path/to/agent-toolkit/install.sh --host gemini --project .
# Creates AGENTS.md + .agent-toolkit/CLI_ONLY.md

# Always commit through atk:
python3 /path/to/agent-toolkit/scripts/atk.py --project . status
python3 /path/to/agent-toolkit/scripts/atk.py --project . commit -m "message"
```

Optional alias:

```bash
alias atk-git='python3 /path/to/agent-toolkit/scripts/atk.py --project . git --'
atk-git commit -m "message"
```

### Rules only (no hooks)

```bash
/path/to/agent-toolkit/generate-project-rules.sh --cursor
```

## Pull skills

```bash
python3 /path/to/agent-toolkit/scripts/toolkit_pull.py get_skill implementation
python3 /path/to/agent-toolkit/scripts/toolkit_pull.py get_module implementation tdd
python3 /path/to/agent-toolkit/scripts/toolkit_pull.py run_function gate_status --project .
python3 /path/to/agent-toolkit/scripts/toolkit_pull.py stamp_skill precommit --project .
```

## Extending a new LLM

1. `hosts/<id>.json` + `rules/hosts/<id>.md`
2. Detect signal in `agent_detect.py` + normalizer in `stdin_adapter.py` if hooks exist
3. Fixture in `tests/test_multihost_gates.py`
4. Document structural vs `atk` in this file

## Keeping rules up to date

```bash
cd /path/to/agent-toolkit && git pull
cd /path/to/your-project
/path/to/agent-toolkit/install.sh --host cursor --project .
```
