# Evaluation: agent-toolkit (latest)
# Score: 91% (A-)

**Evaluated:** 2026-05-20  
**Scope:** Eval follow-ups (README session timeline, template gates, hook coverage)  
**Prior score:** 86% (B+) — see `archive/eval_agent-toolkit_20260520.md`

| Dimension | Score | Weight | Weighted |
|-----------|-------|--------|----------|
| Completeness | 92% | 30% | 27.6 |
| Code Quality | 90% | 25% | 22.5 |
| Security | 91% | 20% | 18.2 |
| Test Quality | 92% | 15% | 13.8 |
| Efficiency | 90% | 10% | 9.0 |
| **Overall** | | | **91%** |

## Grade: A- (90–94%)

---

## Executive summary

Eval follow-ups landed: README documents **~50 min** hard stop, **19 guardrail groups**, and **`update.sh`** in the harness tree; `templates/gates.json` drops redundant top-level `commit_requires`/`push_requires` (profile-only); hook tests add **session-init** (4) and **signed gate smoke** (2). Full regression: **`pytest tests/test_gate.py` → 16/16**, **`bash tests/test-hooks.sh` → 55/55**. Older evaluate reports moved to `archive/`; this file is the canonical latest scorecard.

---

## Findings by dimension

### Completeness (92%)

| # | Claim | Status | Evidence |
|---|-------|--------|----------|
| 1 | README session timeline (~50 min) | PASS | README session-monitor table + workflow diagram |
| 2 | 19 guardrail groups documented | PASS | README tagline + guardrails section |
| 3 | `update.sh` in tree / install | PASS | `install.sh`, README architecture |
| 4 | Template gates profile-only requires | PASS | `templates/gates.json` — no top-level commit/push keys |
| 5 | session-init hook tested | PASS | 4 tests in `test-hooks.sh` |
| 6 | Signed mode hook smoke | PASS | JWT allow/block in `test-hooks.sh` |
| 7 | Gate unit tests green | PASS | 16/16 `test_gate.py` |
| 8 | Hook suite green | PASS | 55/55 `test-hooks.sh` |

### Code Quality (90%)

| Check | Status | Notes |
|-------|--------|-------|
| gates.json template clarity | PASS | Profiles own `commit_requires` / `push_requires` |
| README / install alignment | PASS | 8 hooks + `update.sh`, 50 min stop |
| HANDOFF follow-up doc | PASS | Appendix A applied; archive script run |

### Security (91%)

| Check | Status | Notes |
|-------|--------|-------|
| Signed smoke: token required | PASS | Blocks commit without JWT (exit 2) |
| session-init clears stale `.gates/` | PASS | Prevents cross-session flag bleed |
| G-SESSION-1 in session-init output | PASS | Agent reminded not to write `.session/` |

### Test Quality (92%)

| Check | Status | Notes |
|-------|--------|-------|
| Gate JWT + legacy + bootstrap | PASS | 16 pytest cases |
| Hook regression breadth | PASS | 55 cases incl. session-init + signed |
| Evaluate report hygiene | PASS | Historical reports in `archive/` |

### Efficiency (90%)

| Check | Status | Notes |
|-------|--------|-------|
| Hook tests in temp dir | PASS | Isolated `mktemp` workspace |
| Legacy default for consumers | PASS | Template `gate_mode: legacy`, warn enforcement |

---

## To reach 95% (A)

1. Align root consumer `gates.json` with README legacy-first story where applicable.
2. CI badge / doc line counts if drift recurs after edits.
3. Optional: dedupe or document hook test numbering if 55 vs documented 54 matters for badges.

---

## Verdict

**91% (A-)** — Follow-ups complete; tests green. Meets toolkit narrative for short-session legacy workflows. Below internal 95% push threshold — do not set `.gates/evaluate-passed` for a strict push gate on this run alone.

**Tests:** `python3 -m pytest tests/test_gate.py -q` → 16 passed; `bash tests/test-hooks.sh` → 55 passed.
