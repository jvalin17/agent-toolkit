# Gate unlock — signed vs legacy

Check `gates.json` → `gate_mode` (default: **`legacy`** for daily work; **`signed`** is optional).

| Mode | Unlock mechanism | Best for |
|------|------------------|----------|
| **legacy** | Hook-owned reports + `.gates/` flags via `finalize_report.py` | Daily development (default) |
| **signed** | Skills write `reports/` → attest → `.gate/gate-token.jwt` | 2+ hour sessions, HANDOFF resume, team `main`, regulated work |

**Enforcement is always block.** Hooks block commit/push when required gates are missing; there is no advisory mode. A `gates.json` that exists but cannot be parsed blocks every git action until it is fixed (fail closed).

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
| Default | `./install.sh` only | `legacy`, `mode: default` |
| Enable signed | `scripts/setup-signed-gates.sh` or `set-gate-mode.sh signed` | `signed` + bootstrap + smoke test |
| Back to legacy | `set-gate-mode.sh legacy` | `legacy`, `mode: default` |
| Signed + GitHub secret | `setup-signed-gates.sh --upload-github-secret` | + `AGENT_TOOLKIT_GATE_SECRET` |
| Stricter profile | `setup-signed-gates.sh --profile strict` | `signed`, `profile: strict` |

**Agent prompts:** *“Run `set-gate-mode.sh status`”* · *“Enable signed gates with `setup-signed-gates.sh`”* · *“Switch to legacy with `set-gate-mode.sh legacy`”*

## Which skills a commit or push needs

**Legacy mode** reads the `mode` field (`minimal` … `safe`); see the mode table in the README [Configuration](../README.md#configuration) section and `hooks/mode_resolver.py`.

**Signed mode** reads a `profile` (used by `gate/core.py` when issuing and verifying tokens):

| Profile | Commit needs | Push needs |
|---------|-------------|------------|
| **minimal** | `/precommit` | *(none — commit already gated)* |
| **standard** (signed default) | `/precommit` | `/evaluate` (≥ threshold) |
| **strict** | `/precommit` + `/evaluate` | `/reviewer` *(evaluate survives commit)* |
| **paranoid** | `/precommit` + `/evaluate` | `/reviewer` + `/assess` |

**Gate cleanup:** `gate_cleanup.py` clears `precommit-passed` on commit only.
Push-scoped flags (`evaluate`, `reviewer`, `assess`) survive commit so you
finalize once, commit, then push without re-running evaluate. Push clears
push-scoped flags for the next cycle.

```json
{
  "gate_mode": "legacy",
  "mode": "default",
  "eval_threshold": 95
}
```

Set `"gate_mode": "signed"` for JWT workflow. Attestation requires mechanical checks plus valid skill reports under `reports/` (SHA-256 bound). See `gate/reports.py`.

## Legacy mode

| Skill | File | Required content |
|-------|------|------------------|
| `/precommit` | `.gates/precommit-passed` | `READY` |
| `/evaluate` | `.gates/evaluate-passed` | `PASSED` + score ≥ threshold (written by `finalize_report.py`) |
| `/reviewer` | `.gates/reviewer-passed` | `PASSED` (written by `finalize_report.py`) |
| `/assess` | `.gates/assess-passed` | `PASSED` (written by `finalize_report.py`) |

With default **`gate_protect: true`** and **`report_protect: true`**, only
`hooks/finalize_report.py` writes `.gates/` and `reports/`. Run the skill,
write `.scratch/<skill>_<slug>/findings.json`, then finalize — do not create
or edit gate or report files directly.

## Signed mode

**Why signed mode:** JWT attestation binds mechanical checks and report hashes
to `commit_sha` — suited to team `main`, CI branch protection, and regulated
workflows. Legacy mode uses the same finalize flow; signed mode adds
cryptographic verification on top.

| Layer | Role |
|-------|------|
| Skills | Run workflows; write reports under `reports/` |
| Attestation | Tests/lint + report validation → `.gate/attestation.json` |
| JWT | `.gate/gate-token.jwt` — `gate_hook.py` checks via `verify_gate.py` (blocks if verify fails or is unavailable; no silent fallback) |
| GitHub (optional) | Workflow `agent-toolkit-gate`; branch protection on that check |

HS256 + `.gate/signing.key` (PyJWT only — no `cryptography` wheel).

**Enable (~5 min):**

```bash
/path/to/agent-toolkit/scripts/setup-signed-gates.sh
# --upload-github-secret | --profile strict
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

## Important rare options

These settings exist for CI bootstrap and toolkit maintenance — not for daily bypass. Defaults (`gate_protect: true`, `report_protect: true`) should stay on for any repo where the agent can commit or push.

There is no advisory (`warn`) enforcement. Rolling gates out to a team is done by choosing a lighter `mode` (for example `minimal` or `guarded`), never by making a required gate non-blocking.

### Environment overrides (maintainers / CI)

Any `gates.json` key can be overridden at runtime via `AGENT_TOOLKIT_{KEY_UPPER}`. Hooks read env **after** file config; useful for one-off CI jobs or local debugging — not for weakening production gates.

| Variable | Effect |
|----------|--------|
| `AGENT_TOOLKIT_GATE_PROTECT` | `true` / `false` — G-GATE-1 |
| `AGENT_TOOLKIT_REPORT_PROTECT` | `true` / `false` — G-REPORT-1 |
| `AGENT_TOOLKIT_MODE` | `strict` — anti-fake mode without editing `gates.json` |
| `AGENT_TOOLKIT_GATE_SECRET` | Shared HS256 key for signed mode (GitHub Actions + laptop) |
| `AGENT_TOOLKIT_ATTEST_SKIP_HOOK_TESTS` | CI only — skip redundant hook test re-run during attest |
| `AGENT_TOOLKIT_ATTEST_SKIP_GATE_TESTS` | CI only — skip redundant gate pytest during attest |

### Mode combination matrix

Two independent axes in `gates.json`:

| Axis | Values | Read by |
|------|--------|---------|
| `gate_mode` | `legacy` · `signed` | `hooks/gate_hook.py` |
| `mode` (legacy) | `minimal` · `tdd` · `planned` · `guarded` · `default` · `standard` · `safe` | `hooks/mode_resolver.py` |
| `profile` (signed) | `minimal` · `standard` · `strict` · `paranoid` | `gate/core.py` |

| Combo | Commit gates | Push gates | Notes |
|-------|-------------|------------|-------|
| legacy · mode default | precommit | — | Template default |
| legacy · mode standard | precommit | evaluate | Common production preset |
| legacy · mode safe | precommit | evaluate + reviewer | Lockdown preset |
| signed · profile standard | precommit (JWT) | evaluate (JWT) | Team + CI |
| signed · profile paranoid | precommit + evaluate | reviewer + assess | Strongest team setup |

## Mode reference

**Defaults:** `legacy`, `mode: default`, `gate_protect: true`, `report_protect: true`.

Signed mode adds JWT verification; profiles add skills required at commit/push.
See [Gate profiles](#gate-profiles) above, [System overview](../docs/system-overview.md), and README [Configuration](../README.md#configuration).
