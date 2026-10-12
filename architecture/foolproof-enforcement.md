# Architecture: Foolproof multi-host enforcement

Phases A–D (see `requirements/foolproof-enforcement.md`).

## Components

| Piece | Role |
|-------|------|
| `hooks/hook_io.py` | Payload-first detect + normalize + block/context JSON |
| `hooks/stdin_adapter.py` | Per-host field maps; blocked outputs include `decision: block` |
| `gate_hook` / `tdd_enforce` / `skill_enforce` / `session_monitor` | Use `hook_io` |
| `scripts/install_host_hooks.py` | Write host hooks + AGENTS.md |
| `scripts/atk.py` | CLI commit/push gate for cli_only hosts |
| `install.sh --host` | Thin wrapper to install_host_hooks |

## Transport

```
Hook stdin → parse_hook_stdin (stdin signals > env)
         → canonical {event, tool_name, command, file_path}
         → policy (gates/TDD/skills)
         → make_block_json(agent) | make_context_json(agent)
```

Gemini: no hooks → `atk commit` checks `.gates/*-passed` READY flags.
