# Evaluation: agent-toolkit (repository)
# Score: 86% (B+)

**Evaluated:** 2026-05-20  
**Commit:** `611c930`  
**Prior score:** 79% (C+) at `5b6d05c`

| Dimension | Score | Weight | Weighted |
|-----------|-------|--------|----------|
| Completeness | 86% | 30% | 25.8 |
| Code Quality | 85% | 25% | 21.3 |
| Security | 87% | 20% | 17.4 |
| Test Quality | 84% | 15% | 12.6 |
| Efficiency | 90% | 10% | 9.0 |
| **Overall** | | | **86%** |

## Grade: B+ (85–89%)

---

## Executive summary

The repo improved materially since the last evaluation: **legacy is the documented default**, skills point at `shared/gate-unlock.md`, report-bound attestation exists, hook tests are green (43/43), and session limits (40 min warn / 50 min hard stop) align with short-session workflows. Remaining gaps: **one failing gate unit test** after the legacy default change, and **root `gates.json` still `"signed"`** while README recommends legacy.

---

## Findings by dimension

### Completeness (86%)

| # | Claim | Status | Evidence |
|---|-------|--------|----------|
| 1 | 13 skills | PASS | `skills/` count |
| 2 | 9 agents | PASS | `agents/` count |
| 3 | Harness + session monitor | PASS | `install.sh:130,293` — session-monitor installed |
| 4 | Legacy default for consumers | PARTIAL | `templates/gates.json` + `gate/core.py` + `gate.sh` default legacy; **root `gates.json` still `"signed"`** |
| 5 | Signed optional + session timeline in README | PASS | README § Gate modes |
| 6 | No consumer secret on toolkit repo | PASS | README states clearly |
| 7 | Report-backed attestation | PASS | `gate/reports.py`, `gate/attest.py` |
| 8 | Skills document signed vs legacy | PASS | `shared/gate-unlock.md`; gate skills updated |
| 9 | Hook tests all pass | PASS | `bash tests/test-hooks.sh` → 43/43 |
| 10 | Gate unit tests all pass | FAIL | `pytest tests/test_gate.py` → **12 pass, 1 fail** |
| 11 | Session time enforcement | PASS | `hooks/session-monitor.sh` WARN 40m / STOP 50m |

**Failed test:** `test_bootstrap_and_signed_roundtrip` — bootstrap copies template with `gate_mode: legacy`; `verify_token` expects JWT but falls through to legacy `.gates/` check (`legacy gates missing: precommit, evaluate`).

---

### Code Quality (85%)

| Check | Status | Notes |
|-------|--------|-------|
| Gate module SRP | PASS | attest / core / keys / reports split |
| precommit SKILL ≤250 lines | PASS | 118 lines + references |
| README clarity | PASS | Legacy vs signed, timeline table |
| Config consistency | PARTIAL | Root `gates.json` vs template/README |
| session-monitor.sh size | PASS | 289 lines, focused responsibility |

---

### Security (87%)

| Check | Status | Notes |
|-------|--------|-------|
| Secrets gitignored | PASS | `.gate/signing.key`, tokens |
| Legacy default reduces secret sprawl | PASS | Matches user intent |
| Signed optional documented | PASS | Trust model + branch protection |
| Report SHA-256 binding | PASS | `report_sha256` in attestation |
| Session state agent-write blocked | PASS | G-SESSION-1 in session-monitor header |

---

### Test Quality (84%)

| Check | Status | Notes |
|-------|--------|-------|
| JWT issue/verify/tamper | PASS | Multiple tests in `test_gate.py` |
| Report validation tests | PASS | precommit READY, evaluate threshold |
| Hook regression suite | PASS | 43 tests including session-monitor |
| Bootstrap signed roundtrip | FAIL | Regression after legacy template default |
| Recursive attest avoided | PASS | `AGENT_TOOLKIT_ATTEST_SKIP_*` env |

---

### Efficiency (90%)

| Check | Status | Notes |
|-------|--------|-------|
| PyJWT-only gate deps | PASS | No cryptography wheel issue |
| Legacy default = less CI/secret overhead | PASS | Good fit for &lt;30 min sessions |
| Attest skip flags in CI | PASS | Avoids duplicate slow runs |

---

## To reach 95% (A)

1. **Fix `test_bootstrap_and_signed_roundtrip`** — After bootstrap, set `"gate_mode": "signed"` in test `gates.json` (or pass signed template).
2. **Align root `gates.json`** with README — `"gate_mode": "legacy"` for this repo (or document why toolkit CI stays signed).
3. **Update README hook count** — Badge says 7 hooks; `session-monitor.sh` is an 8th installed hook.
4. **Green CI on full `test_gate.py`** including optional `test_attest_on_toolkit_repo` smoke without timeout.

---

## Verdict

**86% (B+)** — Production-quality skills and harness; gate story is now coherent for real users (legacy daily, signed extreme cases). One test regression and a small config/README drift block A range. Below toolkit’s own 95% eval threshold — do not set `.gates/evaluate-passed` on this run.
