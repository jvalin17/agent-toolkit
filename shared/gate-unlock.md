# Gate unlock — signed vs legacy

Check `gates.json` → `gate_mode` (default: **`legacy`** for daily work; **`signed`** is optional).

| Mode | Unlock mechanism | Best for |
|------|------------------|----------|
| **legacy** | Skills write `.gates/<skill>-passed` | Solo dev, sessions up to ~50 min, prototypes |
| **signed** | Skills write `reports/` → attest → `.gate/gate-token.jwt` | 2+ hour sessions, HANDOFF resume, team `main`, regulated work |

**`enforcement`:** default **`block`** — hook blocks commit/push when required gates are missing. Use **`warn`** to remind without blocking.

**`AGENT_TOOLKIT_GATE_SECRET`:** optional. Not needed for legacy or single-job CI (bootstrap creates `.gate/signing.key`). Use `scripts/setup-signed-gates.sh --upload-github-secret` only when GitHub and your laptop must share one key.

## Switch modes

```bash
/path/to/agent-toolkit/scripts/set-gate-mode.sh status    # current mode
/path/to/agent-toolkit/scripts/set-gate-mode.sh signed    # enable signed (full setup)
/path/to/agent-toolkit/scripts/set-gate-mode.sh legacy    # back to default
```

Review `gates.json` after switching.

| What you want | Command | Result in `gates.json` |
|---------------|---------|-------------------------|
| Default | `./install.sh` only | `legacy`, `block`, `minimal` |
| Enable signed | `scripts/setup-signed-gates.sh` or `set-gate-mode.sh signed` | `signed` + bootstrap + smoke test |
| Back to legacy | `set-gate-mode.sh legacy` | `legacy`, `block`, `minimal` |
| Signed + GitHub secret | `setup-signed-gates.sh --upload-github-secret` | + `AGENT_TOOLKIT_GATE_SECRET` |
| Signed, non-blocking hooks | `setup-signed-gates.sh --warn` | `signed`, `enforcement: warn` |
| Stricter profile | `setup-signed-gates.sh --profile strict` | `signed`, `profile: strict` |

**Agent prompts:** *“Run `set-gate-mode.sh status`”* · *“Enable signed gates with `setup-signed-gates.sh`”* · *“Switch to legacy with `set-gate-mode.sh legacy`”*

## Gate profiles (`gates.json`)

| Profile | Commit needs | Push needs |
|---------|-------------|------------|
| **minimal** (template default) | `/precommit` | `/precommit` |
| **standard** | `/precommit` | `/precommit` + `/evaluate` (≥ threshold) |
| **strict** | `/precommit` + `/evaluate` | + `/reviewer` |
| **paranoid** | `/precommit` + `/evaluate` | + `/reviewer` + `/assess` |

```json
{
  "gate_mode": "legacy",
  "enforcement": "block",
  "profile": "minimal",
  "eval_threshold": 95
}
```

Set `"gate_mode": "signed"` for JWT workflow. Attestation requires mechanical checks plus valid skill reports under `reports/` (SHA-256 bound). See `gate/reports.py`.

## Legacy mode

| Skill | File | Required content |
|-------|------|------------------|
| `/precommit` | `.gates/precommit-passed` | `READY` |
| `/evaluate` | `.gates/evaluate-passed` | `PASSED` + score ≥ threshold |
| `/reviewer` | `.gates/reviewer-passed` | `PASSED` |
| `/assess` | `.gates/assess-passed` | `PASSED` |

Legacy is weaker when `gate_protect` is off (agent can `echo` flags). With default **`gate_protect: true`**, only hooks such as `finalize_report.py` write `.gates/` files. With `enforcement: warn`, skills and guardrails carry most of the quality bar. Before push: run skills per profile; flags must contain real markers, not empty files.

## Signed mode

**Why:** Legacy flags are filesystem files the agent could forge. Signed mode splits **workflow** (skills) from **authority** (CI + JWT bound to `commit_sha`).

| Layer | Role |
|-------|------|
| Skills | Run workflows; write reports under `reports/` |
| Attestation | Tests/lint + report validation → `.gate/attestation.json` |
| JWT | `.gate/gate-token.jwt` — `gate_hook.py` checks via `verify_gate.py` |
| GitHub (optional) | Workflow `agent-toolkit-gate`; branch protection on that check |

HS256 + `.gate/signing.key` (PyJWT only — no `cryptography` wheel).

**Enable (~5 min):**

```bash
/path/to/agent-toolkit/scripts/setup-signed-gates.sh
# --upload-github-secret | --warn | --profile strict
```

**Before commit/push (local loop):**

```bash
pip install -r .agent-toolkit/gate/requirements.txt   # once
python .agent-toolkit/gate/scripts/verify_gate.py attest --project-root .
python .agent-toolkit/gate/scripts/issue_token.py --project-root . --action push
```

Re-issue after each new commit. Token must match `git rev-parse HEAD`. Or rely on CI on push/PR and branch protection (strongest for teams).

## What `./install.sh` adds (git projects)

- `.agent-toolkit/gate/` — scripts for CI and local verify
- `gates.json` — template if missing (`legacy`, `block`, `minimal`)
- `.gate/signing.key` — gitignored (optional GitHub secret)
- `.github/workflows/agent-toolkit-gate.yml` — attest → issue → verify

Manual signed setup: copy `templates/gates.signed.example.json` or edit `gates.json` by hand after install.

## All mode combinations (quick reference)

Same content as README [Gate mode examples](../README.md#gate-mode-examples): **2** `gate_mode` × **2** `enforcement` × **4** `profile` = **16** configs. Legacy unlocks via `.gates/*-passed`; signed via attest + JWT. `warn` never blocks the shell (exit 0); `block` returns exit 2 when checks fail.
