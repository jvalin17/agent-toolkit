# Configuration

All settings live in **`gates.json`** at the project root.

```bash
agent-toolkit-setup --status       # show current config
agent-toolkit-setup --balanced     # daily dev
agent-toolkit-setup --guarded      # production (standard profile)
agent-toolkit-setup --lockdown     # strict mode + paranoid profile
agent-toolkit-setup --tdd off      # toggle one setting
```

## Presets

| Preset | Typical use |
|--------|-------------|
| **balanced** | Daily development |
| **guarded** | Production — block + protect on |
| **lockdown** | Strict mode + paranoid profile |
| **quick** | Local experiments only — disables structural protection; not for shared branches |

Demo: `scripts/demo-modes.sh`

## Common settings

| Setting | Default | What it does |
|---------|---------|--------------|
| `enforcement` | `block` | Block commit/push when gates missing |
| `profile` | `minimal` | Which skills required — see [workflow.md](workflow.md) |
| `gate_mode` | `legacy` | `legacy` = finalize + flags; `signed` = JWT |
| `gate_protect` | **`true`** | Block agent writes to `.gates/` (G-GATE-1) |
| `report_protect` | **`true`** | Block agent writes to `reports/` (G-REPORT-1) |
| `tdd` | `true` | Remind test-first before source edits |
| `tdd_mode` | `remind` | `remind` = advisory; `strict` = block source edits until tests exist |
| `skill_routing` | `true` | Auto-detect intent → skill |
| `mode` | `normal` | `strict` = anti-fake drift detection |
| `eval_threshold` | `95` | Minimum evaluate score to pass gate |

Keep **`block`**, **`gate_protect`**, and **`report_protect`** at defaults for any project where the agent can commit or push.

## Rare but important

| Option | When |
|--------|------|
| `enforcement: warn` | Rolling out gates — first violation escalates to block |
| `setup-signed-gates.sh --warn` | Signed-mode CI smoke test |
| `gate_mode: signed` | Team `main`, branch protection, JWT attestation |
| `profile: strict` / `paranoid` | Extra push gates |
| `mode: strict` | Fixture provenance, drift detection |
| Env overrides | Maintainer/CI — `AGENT_TOOLKIT_ENFORCEMENT`, etc. |

Full reference: [gate-unlock.md](../shared/gate-unlock.md)

## Signed gates (teams / CI)

```bash
scripts/setup-signed-gates.sh
scripts/set-gate-mode.sh status
```

Details: [gate-unlock.md](../shared/gate-unlock.md)
