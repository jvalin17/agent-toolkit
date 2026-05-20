# Gate unlock — signed vs legacy

Check `gates.json` → `gate_mode` (default: **`legacy`** for daily work; **`signed`** is optional for long sessions / teams — see README timeline).

## Signed mode (default)

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

Legacy is weaker (agent can `echo` flags). Use only for solo local work without CI.
