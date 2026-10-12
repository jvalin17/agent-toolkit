# Agent Toolkit demos

Small apps that exercise the **LLM-agnostic modular** path:

1. Generate short project rules  
2. Pull skill stubs / modules  
3. Build with TDD  

| Demo | What it shows |
|------|----------------|
| [calculators](calculators/) | Multi-module app built by Grok / Gemini / GPT / Composer agents |
| [unit-converter](unit-converter/) | Pure functions + pytest |
| [todo-list](todo-list/) | Tiny domain object + edge cases |
| [password-strength](password-strength/) | Scoring / validation style feature |

## Quick start (any demo)

```bash
# from this demos/ directory
./run_demos.sh                 # generate rules + run all tests
./run_demos.sh calculators     # one demo only

# or manually
cd unit-converter
../../generate-project-rules.sh --cursor
python3 ../../scripts/toolkit_pull.py get_skill implementation
python3 -m pytest tests/ -q
```

## Try with Cursor agents

Open a demo folder, ensure `AGENTS.md` exists, then ask Agent:

> Use the implementation skill stub (or `~/.cursor/skills/implementation`).  
> Add a failing test first, then implement.

Link skills once:

```bash
mkdir -p ~/.cursor/skills
ln -sfn "$(cd .. && pwd)/skills/implementation" ~/.cursor/skills/implementation
ln -sfn "$(cd .. && pwd)/skills/precommit" ~/.cursor/skills/precommit
```
