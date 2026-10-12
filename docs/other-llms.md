# Other LLMs (Cursor, GPT, Gemini, Grok, & more)

Agent Toolkit is **full strength on Claude Code** (structural hooks). On other hosts the **same development policy** applies via short rules + on-demand pull (Option B).

Orchestrator **detects the host** → loads `hosts/<id>.json` (merged with `hosts/default.json`) → injects a short bootstrap. Skills are **stubs**; depth is `get_module` / CLI.

## What works where

| Capability | Claude Code | Cursor / GPT / Gemini / Grok / others |
|------------|-------------|----------------------------------------|
| Short rules + skills index | Yes | Yes (`AGENTS.md` / `.cursor/rules/toolkit.mdc`) |
| Pull skill stub / module | MCP + Skill | MCP or `scripts/toolkit_pull.py` |
| `run_function` gates | Yes | Yes (CLI/MCP) |
| Structural commit hooks | Yes | Cursor: if hooks installed; else CLI |
| Report protection | Hook | CLI discipline + path advice |

## Setup (every non-Claude project)

From **your project root**:

```bash
# Auto-detect host, or pass --host / --cursor
/path/to/agent-toolkit/generate-project-rules.sh
/path/to/agent-toolkit/generate-project-rules.sh --cursor
/path/to/agent-toolkit/generate-project-rules.sh --host gemini
```

This writes a **short** `AGENTS.md` (and host overlays). It does **not** dump full skill bodies.

Pull on demand:

```bash
python3 /path/to/agent-toolkit/scripts/toolkit_pull.py get_skill implementation
python3 /path/to/agent-toolkit/scripts/toolkit_pull.py get_module implementation tdd
python3 /path/to/agent-toolkit/scripts/toolkit_pull.py run_function gate_status --project .
```

Or add the toolkit MCP server and use `resolve_host`, `get_skill`, `get_module`, `run_function`, `stamp_skill`.

Optional — bootstrap gates:

```bash
bash /path/to/agent-toolkit/scripts/bootstrap-project-gates.sh /path/to/agent-toolkit
```

## Cursor

1. `generate-project-rules.sh --cursor`
2. Open project; agent reads `AGENTS.md` + `.cursor/rules/toolkit.mdc`
3. Prefer MCP pull tools for skill depth

Optional skill stubs:

```bash
mkdir -p ~/.cursor/skills
for d in /path/to/agent-toolkit/skills/*/; do
  ln -sf "$d" ~/.cursor/skills/$(basename "$d")
done
```

## OpenAI Codex / GPT

```bash
generate-project-rules.sh --host codex-cli
```

Use plain language + pull CLI/MCP. Example: “Follow precommit stub; run gate_status before commit.”

## Google Gemini

```bash
generate-project-rules.sh --host gemini
# writes AGENTS.md + GEMINI.md
cd /path/to/your-project && gemini
```

## Grok

```bash
generate-project-rules.sh --host grok-build
```

Prefer CLI gates until all hooks normalize Grok camelCase stdin.

## Windsurf / Aider / generic

```bash
generate-project-rules.sh --host windsurf   # or omit --host for detect/default
```

## Extending a new LLM

1. Add `hosts/<id>.json` (merge over `default.json`)
2. Add `rules/hosts/<id>.md`
3. Add detect signal in `hooks/agent_detect.py`
4. Add fixture test — then document in README

## Keeping rules up to date

```bash
cd /path/to/agent-toolkit && git pull
cd /path/to/your-project
/path/to/agent-toolkit/generate-project-rules.sh --cursor
```
