# Configuration

All settings live in **`gates.json`** at the project root.

```bash
agent-toolkit-setup --status       # show current config
agent-toolkit-setup --balanced     # daily dev
agent-toolkit-setup --guarded      # production → mode: standard
agent-toolkit-setup --lockdown     # → mode: safe
```

## Presets

| Preset | Sets `mode` | Typical use |
|--------|-------------|-------------|
| **balanced** | `default` | Daily development (TDD + precommit) |
| **guarded** | `standard` | Production — plan, review depth, spot checks |
| **lockdown** | `safe` | Everything on, reviewer required for push |
| **quick** | `minimal` | Local experiments only — no structural protection; not for shared branches |

Demo: `scripts/demo-modes.sh`

## Common settings

| Setting | Default | What it does |
|---------|---------|--------------|
| `mode` | `default` | Which gates apply: `minimal` · `tdd` · `planned` · `guarded` · `default` · `standard` · `safe` (table in the [README](../README.md#configuration)) |
| `gate_mode` | `legacy` | `legacy` = finalize + flags; `signed` = JWT |
| `gate_protect` | **`true`** | Block agent writes to `.gates/` (G-GATE-1) |
| `report_protect` | **`true`** | Block agent writes to `reports/` (G-REPORT-1) |
| `skill_routing` | `true` | Auto-detect intent → skill |
| `eval_threshold` | `95` | Minimum evaluate score to pass gate |
| `canary` | `""` | Greeting word checked on every reply (`"Hey"` to enable) |
| `test_command` / `lint_command` | auto-detect | Commands finalize re-runs; split on whitespace, never passed to a shell |

Enforcement is always block. A `gates.json` that exists but cannot be parsed blocks commit and push until it is fixed. Keep **`gate_protect`** and **`report_protect`** at defaults for any project where the agent can commit or push.

## Rare but important

| Option | When |
|--------|------|
| `gate_mode: signed` | Team `main`, branch protection, JWT attestation |
| `profile: strict` / `paranoid` | Signed mode only — extra push gates |
| `AGENT_TOOLKIT_MODE=safe` | One-session mode override |
| Env overrides | Maintainer/CI — any key as `AGENT_TOOLKIT_<KEY>` |

Full reference: [gate-unlock.md](../shared/gate-unlock.md)

## Signed gates (teams / CI)

```bash
scripts/setup-signed-gates.sh
scripts/set-gate-mode.sh status
```

Details: [gate-unlock.md](../shared/gate-unlock.md)
