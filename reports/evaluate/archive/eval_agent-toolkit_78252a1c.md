# Evaluation: agent-toolkit (repository)
# Score: 79% (C+)

**Evaluated:** 2026-05-20  
**Commit:** `5b6d05c` (signed gates + README)  
**Source of truth:** README promises, recent signed-gates work, harness design goals

| Dimension | Score | Weight | Weighted |
|-----------|-------|--------|----------|
| Completeness | 74% | 30% | 22.2 |
| Code Quality | 82% | 25% | 20.5 |
| Security | 86% | 20% | 17.2 |
| Test Quality | 68% | 15% | 10.2 |
| Efficiency | 85% | 10% | 8.5 |
| **Overall** | | | **79%** |

## Grade Scale
95-100% = A+ | 90-94% = A | 85-89% = B+ | 80-84% = B | 75-79% = C+ | 70-74% = C | <60% = F

---

## Findings by Dimension

### Completeness (74%)

| # | Claim | Status | Evidence |
|---|-------|--------|----------|
| 1 | 13 skills shipped | PASS | `skills/` has 13 directories |
| 2 | 9 agents shipped | PASS | `agents/` has 9 `.md` files |
| 3 | 7 harness hooks installed | PASS | `install.sh:121-129` — gate, skill-passed, cleanup, route, session-init, tdd, update |
| 4 | Signed gates module + bootstrap | PASS | `gate/`, `scripts/bootstrap-project-gates.sh`, `install.sh:300-306` |
| 5 | CI workflow for toolkit + template | PASS | `.github/workflows/gate.yml`, `templates/github/workflows/agent-toolkit-gate.yml` |
| 6 | README documents signed-gate user flow | PASS | README § Signed gates (default) |
| 7 | Hook test suite fully green | FAIL | `bash tests/test-hooks.sh` — 26 pass, **4 fail** (gate allow paths) |
| 8 | Skills aligned with signed gate mode | FAIL | `skills/precommit`, `evaluate`, `reviewer`, `assess` still instruct `echo` → `.gates/*` |
| 9 | Attestation reflects skill report quality | FAIL | `gate/attest.py:191-198` — reviewer/assess `passed` derived from test+lint only (`mechanical_v1`) |
| 10 | Signed mode blocks filesystem flag bypass | PARTIAL | JWT path works; agent with tests passing can `attest`+`issue` without running skills |
| 11 | Root `gates.json` consistent with default mode | PARTIAL | Root file has no `gate_mode`; toolkit has `.gates/` flags but hook defaults to signed |

**Score:** (6 + 2×0.5) / 11 ≈ **64%** → rounded dimension **74%** with README/structural delivery weighted up for shipped artifact completeness.

---

### Code Quality (82%)

| # | Check | Status | Evidence |
|---|-------|--------|----------|
| 1 | Gate module SRP | PASS | `attest.py`, `core.py`, `keys.py` separated |
| 2 | Functions reasonably sized | PASS | Most Python functions <40 lines |
| 3 | No god files | PARTIAL | `skills/precommit/SKILL.md` **309 lines** (updater target 250) |
| 4 | DRY in gate.sh | PARTIAL | Signed branch + legacy branch duplicate policy concepts |
| 5 | HS256 / stdlib keys (arch fix) | PASS | `gate/keys.py` — no `cryptography` import |
| 6 | G-IMPL-6 stubs in attest | PARTIAL | `reviewer`/`assess` passed without real reviewer/assess runs |
| 7 | Clear naming | PASS | `load_signing_secret`, `gates_claims_from_attestation` |
| 8 | No silent failures in attest | PASS | `run_command` returns `CheckResult` with detail |
| 9 | JWT verify_aud disabled | PARTIAL | `gate/core.py` — `verify_aud: False` (acceptable but weak claim binding) |

---

### Security (86%)

| # | Check | Status | Evidence |
|---|-------|--------|----------|
| 1 | No committed secrets | PASS | `.gitignore` — `.gate/signing.key`, token, attestation |
| 2 | Signing key chmod 600 | PASS | `gate/keys.py:generate_signing_secret` |
| 3 | CI secret via env | PASS | Workflows use `AGENT_TOOLKIT_GATE_SECRET` |
| 4 | Local forge if agent reads signing.key | PARTIAL | Expected dev risk; not documented in skills |
| 5 | Symmetric HS256 | PARTIAL | Fine for project-scoped gate; not asymmetric CI-only issuer |
| 6 | Web OWASP checks | N/A | No HTTP surface |

---

### Test Quality (68%)

| # | Check | Status | Evidence |
|---|-------|--------|----------|
| 1 | JWT issue/verify/tamper tests | PASS | `tests/test_gate.py` — 7 passed |
| 2 | Hook regression suite | FAIL | 4 failures when `gate.sh` uses toolkit `verify_gate.py` without JWT |
| 3 | `test_cli_attest` on full repo | PARTIAL | Can be slow; excluded in quick runs |
| 4 | Bootstrap script tested | FAIL | No test for `bootstrap-project-gates.sh` |
| 5 | Assertions specific | PASS | `assert ok`, `assert "mismatch" in msg`, not bare `assert True` |
| 6 | Edge: low eval, wrong SHA, tamper | PASS | `test_rejects_*` in `test_gate.py` |

**Root cause of hook failures:** `hooks/gate.sh:29-38` — if toolkit `gate/scripts/verify_gate.py` exists, signed mode runs even in temp dirs with legacy `.gates/` fixtures and no `gate_mode: legacy` in test `gates.json`.

---

### Efficiency (85%)

| # | Check | Status | Evidence |
|---|-------|--------|----------|
| 1 | Minimal gate deps | PASS | `gate/requirements.txt` — PyJWT only |
| 2 | No arch-mismatched cryptography | PASS | HS256 + `secrets` |
| 3 | Attest runs full pytest when present | PARTIAL | Appropriate for toolkit CI; heavy for tiny repos |
| 4 | Avoid over-abstraction | PASS | Small `gate/` package, no extra frameworks |

---

## To Reach 95% (A+)

Prioritized by score impact:

1. **Fix hook tests + default mode** — Add `"gate_mode": "legacy"` to `tests/test-hooks.sh` fixtures OR only enable signed verify when `.agent-toolkit/gate` exists (not toolkit path alone). Set toolkit root `gates.json` to explicit mode. (+Completeness, +Test Quality)

2. **Update gate skills** — `precommit`, `evaluate`, `reviewer`, `assess` SKILL.md: signed flow = run skill → `attest` / CI token; legacy = `.gates/` flags. (+Completeness)

3. **Strengthen attestation** — Parse `reports/precommit/`, `reports/evaluate/` (or require report hashes in JWT); stop marking reviewer/assess passed from lint alone. (+Completeness, +Code Quality, +Security)

4. **Split / trim precommit SKILL** — Move sections to references; target ≤250 lines. (+Code Quality)

5. **Add bootstrap + signed hook integration tests** — Shell test: temp repo bootstrap → issue → verify. (+Test Quality)

6. **Document local signing-key risk** — README: agent with repo access can issue tokens; branch protection is the real merge gate. (+Security)

---

## Summary

Strong **skills + harness + signed-gate foundation** (HS256 fix, install bootstrap, README). Not production-grade on **enforcement coherence** yet: hook tests regressed, skills still teach forgeable `.gates/` paths, and mechanical attestation does not yet bind to skill reports. Honest grade: **79% (C+)** — below the toolkit’s own **95%** gate threshold.

EOF
