# Gate unlock — signed vs legacy

Check `gates.json` → `gate_mode` (default: **`legacy`** for daily work; **`signed`** is optional for long sessions / teams — see README timeline).

**`enforcement`:** default **`warn`** — hook adds **GATE WARNING** context but does **not** stop the shell (works with Cursor and other LLM tools). Use **`block`** only when you want a hard stop.

**`AGENT_TOOLKIT_GATE_SECRET`:** not required. CI and local issue/verify can use `.gate/signing.key`. Set the GitHub secret only if you want one stable key everywhere.

## Signed mode

Skills produce **reports** under `reports/<skill>/`. They do **not** unlock git by writing `.gates/` files.

Before `git commit` / `git push`:

1. Run required skills (`/precommit`, `/evaluate`, … per profile).
2. Each skill writes a completed report (see skill for required markers).
3. Refresh the gate token:
   ```bash
   pip install -r .agent-toolkit/gate/requirements.txt
   python .agent-toolkit/gate/scripts/verify_gate.py attest --project-root .
   python .agent-toolkit/gate/scripts/issue_token.py --project-root . --action push
   ```
   Or push to GitHub — workflow **agent-toolkit-gate** issues `.gate/gate-token.jwt` (download artifact).

Token must match `git rev-parse HEAD`. Re-issue after every new commit.

**Merge authority:** Enable branch protection requiring check `agent-toolkit-gate`. Anyone with `.gate/signing.key` can mint local tokens — CI + branch protection is the real merge gate.

## Legacy mode

Set `"gate_mode": "legacy"` in `gates.json`.

On pass, skills may write proof files:

| Skill | File | Required content |
|-------|------|------------------|
| `/precommit` | `.gates/precommit-passed` | `READY` |
| `/evaluate` | `.gates/evaluate-passed` | `PASSED` + score ≥ threshold |
| `/reviewer` | `.gates/reviewer-passed` | `PASSED` |
| `/assess` | `.gates/assess-passed` | `PASSED` |

Legacy is weaker (agent can `echo` flags). With `enforcement: warn`, the harness nudges without blocking — skills and guardrails carry most of the quality bar.
