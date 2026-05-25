# Daily workflow

How to build, commit, and push with Agent Toolkit gates.

## Pick a starting skill

| Situation | Start with |
|-----------|------------|
| New project | `/requirements` → `/architecture` → `/implementation` |
| Existing repo | `/explore .` → `/implementation` |
| Bug | "fix …" or `/debug` |
| Before release | `/reviewer` → `/evaluate` |
| Hands-off pipeline | `/requirements auto my-app` — see [orchestrator](../shared/orchestrator.md) |

## Commit (default: minimal profile)

Default: **legacy + block + minimal** — `/precommit` required before `git commit`.

```
1. Do your work
2. /precommit
3. Write .scratch/precommit_<slug>/findings.json
4. python3 hooks/finalize_report.py precommit .scratch/.../findings.json
5. git commit -m "..."
```

Step 4 re-runs tests/lint, writes `reports/precommit/…`, and sets `.gates/precommit-passed`. With default **`report_protect`** and **`gate_protect`**, only the hook writes those paths — not the agent.

**The agent must not:**
- Skip tests (`--no-verify`, ignoring failures)
- Write directly to `reports/`, `.gates/`, or `.session/`
- Claim "ready" without running real checks
- Commit without precommit passing

## Push (standard / guarded profile)

`profile: "standard"` (or `agent-toolkit-setup --guarded`) requires `/evaluate` before push (score ≥ `eval_threshold`, default 95).

```
1. /precommit → finalize → commit
2. /evaluate → finalize   (flag survives commit)
3. git push
```

`gate_cleanup.py` clears **precommit** on commit; evaluate/reviewer/assess flags stay valid until push.

## Push (strict / lockdown)

| Profile | Push requires |
|---------|---------------|
| **strict** | evaluate + **reviewer** |
| **paranoid** (lockdown) | evaluate + reviewer + **assess** |

Same finalize pattern for each gated skill:

```bash
python3 hooks/finalize_report.py evaluate .scratch/evaluate_<slug>/findings.json
python3 hooks/finalize_report.py reviewer .scratch/reviewer_<slug>/findings.json
python3 hooks/finalize_report.py assess .scratch/assess_<slug>/findings.json
```

## Gate profiles at a glance

| Profile | Commit | Push |
|---------|--------|------|
| **minimal** (default) | precommit | — |
| **standard** | precommit | evaluate |
| **strict** | precommit + evaluate | reviewer |
| **paranoid** | precommit + evaluate | reviewer + assess |

Full reference: [gate-unlock.md](../shared/gate-unlock.md)

## Troubleshooting gates

| Symptom | Fix |
|---------|-----|
| `git commit` blocked after precommit | Re-run `finalize_report.py`; check `.gates/precommit-passed` contains `READY` |
| `git push` blocked after evaluate | Re-run finalize; check score ≥ threshold in `.gates/evaluate-passed` |

More: [troubleshooting.md](../shared/troubleshooting.md)
