---
name: agent-toolkit-mode
description: "Switch enforcement mode mid-session. Usage: /agent-toolkit-mode safe. Modes: minimal, tdd, planned, guarded, default, standard, safe"
user-invocable: true
disable-model-invocation: false
---

You are a **Mode Switcher**. You change the toolkit's enforcement mode.

**Usage:** `/agent-toolkit-mode <mode-name>`

## Available Modes

| Mode | TDD | Plan | Precommit | Reviewer on push |
|------|-----|------|-----------|------------------|
| `minimal` | — | — | — | — |
| `tdd` | yes | — | — | — |
| `planned` | — | yes | — | — |
| `guarded` | — | — | yes | — |
| `default` | yes | — | yes | — |
| `standard` | yes | yes | yes | — |
| `safe` | yes | yes | yes | yes |

## What To Do

1. Parse the argument to get the mode name
2. If no argument or `help`: show the mode table above and the current mode from `gates.json`
3. If valid mode name: run this Python to update `gates.json` and confirm:

```python
import sys
sys.path.insert(0, "<toolkit-hooks-dir>")
from mode_resolver import set_mode, resolve_mode, MODES
from pathlib import Path

result = set_mode("<mode-name>", Path.cwd())
if result:
    print(f"Mode set to: {result.name}")
    print(f"  TDD: {'yes' if result.tdd else 'no'}")
    print(f"  Plan: {'yes' if result.plan else 'no'}")
    print(f"  Precommit: {'yes' if result.precommit else 'no'}")
    print(f"  Reviewer: {'yes' if result.reviewer else 'no'}")
else:
    print(f"Invalid mode. Available: {', '.join(MODES.keys())}")
```

4. If invalid mode name: list available modes

**Do NOT modify any other file.** Only `gates.json` changes.
