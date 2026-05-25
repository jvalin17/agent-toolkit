# Other LLMs (Cursor, GPT, Gemini, & more)

Agent Toolkit is **full strength on Claude Code** — hooks block bad commits, protect reports, and auto-sync. On other tools you get the same **guardrails and workflows** via project rules; enforcement is prompt-based, not structural.

## What works where

| Capability | Claude Code | Cursor / GPT / Gemini / others |
|------------|-------------|--------------------------------|
| Guardrails & workflow rules | Yes (hooks + skills) | Yes (`AGENTS.md` / `.cursorrules`) |
| Slash skills (`/precommit`, …) | Yes (`~/.claude/skills/`) | Optional — see [Cursor](#cursor) |
| Auto skill routing | Yes (hook) | No — describe intent in chat |
| Commit/push gates | Yes (hook blocks) | No — you enforce manually |
| Report protection (`reports/`) | Yes (hook blocks) | No |
| Auto `git pull` + sync | Yes | No — pull toolkit yourself |

## Setup (every non-Claude project)

From **your project root**:

```bash
/path/to/agent-toolkit/generate-project-rules.sh          # AGENTS.md
/path/to/agent-toolkit/generate-project-rules.sh --cursor # + .cursorrules
```

Regenerate after toolkit updates. You do **not** need `./install.sh` unless you also use Claude Code.

Optional — bootstrap gates in a git repo (no Claude hooks):

```bash
bash /path/to/agent-toolkit/scripts/bootstrap-project-gates.sh /path/to/agent-toolkit
```

## Cursor

1. Generate rules: `generate-project-rules.sh --cursor`
2. Open project in Cursor, start Agent chat.
3. Talk normally — agent reads `.cursorrules` and `AGENTS.md`.

**Example prompts:** "Explore this codebase…", "Gather requirements for…", "Run a precommit-style review before commit."

**Optional — toolkit skills as Cursor Agent Skills:**

```bash
mkdir -p ~/.cursor/skills
for d in /path/to/agent-toolkit/skills/*/; do
  ln -sf "$d" ~/.cursor/skills/$(basename "$d")
done
```

**Without hooks:** run tests yourself, follow precommit discipline, use `hooks/finalize_report.py` if you adopt the report flow.

## OpenAI Codex / ChatGPT

1. Generate `AGENTS.md` in the project.
2. Open repo in Codex or agent-mode IDE.
3. Use plain language — slash commands are not registered:

```
Follow the precommit workflow in AGENTS.md and review my staged changes.
```

## Google Gemini CLI

```bash
cd /path/to/your-project && gemini
```

Reference workflows explicitly; Gemini reads workspace files including `AGENTS.md`.

## Windsurf, Aider, generic agents

| Tool | Rules file |
|------|------------|
| Windsurf | `AGENTS.md` or tool-specific rules |
| Aider | `AGENTS.md` or `.aider.conf.yml` |
| Generic | `AGENTS.md` at repo root |

**Pattern:** generate once → open project → describe the job using the same intent as slash skills (`explore`, `requirements`, `implementation`, `precommit`, `debug`).

## Keeping rules up to date

```bash
cd /path/to/agent-toolkit && git pull
cd /path/to/your-project
/path/to/agent-toolkit/generate-project-rules.sh --cursor   # or without --cursor
```

Claude Code users get pull + sync automatically — see [install-and-updates.md](install-and-updates.md).
