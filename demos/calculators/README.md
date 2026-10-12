# Demo: calculators

Small multi-module calculator demo for **agent-toolkit** LLM-agnostic skills.
Built by parallel Cursor agents (Grok / Gemini / GPT / Composer) using skill stubs.

| Module | Agent model | Ops |
|--------|-------------|-----|
| `basic` | Grok | add, subtract, multiply, divide |
| `scientific` | Gemini | power, sqrt, percent |
| `finance` | GPT | compound interest, tip |
| `expression` | Composer | safe `+ - * /` expression eval |

## Setup

```bash
/path/to/agent-toolkit/generate-project-rules.sh --cursor
python3 -m pytest tests/ -q
```

Skills: pull stub with `toolkit_pull.py get_skill implementation` or Cursor Agent Skills under `~/.cursor/skills`.
