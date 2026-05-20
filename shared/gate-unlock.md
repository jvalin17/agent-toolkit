# Gate unlock — signed vs legacy

Check `gates.json` → `gate_mode` (default: **`legacy`** for daily work; **`signed`** is optional).

| Mode | Unlock mechanism |
|------|------------------|
| **legacy** | Skills write `.gates/<skill>-passed` (see table below) |
| **signed** | Skills write `reports/` → attest → `.gate/gate-token.jwt` |

**`enforcement`:** default **`warn`** — hook reminds without blocking. Use **`block`** for a hard stop.

**`AGENT_TOOLKIT_GATE_SECRET`:** optional. Use `scripts/setup-signed-gates.sh --upload-github-secret` when you want CI and laptop to share one key.

## Switch modes (human or agent)

```bash
/path/to/agent-toolkit/scripts/set-gate-mode.sh status    # what mode are we in?
/path/to/agent-toolkit/scripts/set-gate-mode.sh signed    # enable signed (full setup)
/path/to/agent-toolkit/scripts/set-gate-mode.sh legacy    # back to default
```

Review `gates.json` after switching. Ask your agent to run the commands above; you approve the result.

## Signed mode — before git commit / push

1. Run required skills (`/precommit`, `/evaluate`, … per `gates.json` profile).
2. Refresh token (after every new commit):

```bash
pip install -r .agent-toolkit/gate/requirements.txt   # once
python .agent-toolkit/gate/scripts/verify_gate.py attest --project-root .
python .agent-toolkit/gate/scripts/issue_token.py --project-root . --action push
```

Or push to GitHub — workflow **agent-toolkit-gate** runs attest/issue/verify; download **gate-token** artifact if needed locally.

Token must match `git rev-parse HEAD`.

**Teams:** branch protection → require check **`agent-toolkit-gate`**.

## Legacy mode

Set `"gate_mode": "legacy"` in `gates.json` (install template default).

| Skill | File | Required content |
|-------|------|------------------|
| `/precommit` | `.gates/precommit-passed` | `READY` |
| `/evaluate` | `.gates/evaluate-passed` | `PASSED` + score ≥ threshold |
| `/reviewer` | `.gates/reviewer-passed` | `PASSED` |
| `/assess` | `.gates/assess-passed` | `PASSED` |

Legacy is weaker (agent can `echo` flags). With `enforcement: warn`, skills and guardrails carry most of the quality bar.
