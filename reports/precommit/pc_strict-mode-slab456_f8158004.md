<!-- agent-toolkit:precommit | v1 | 2026-05-21 | f8158004 -->

# Pre-commit Report: Strict Mode Slabs 4-6

**Scope:** Gate enforcement, skill text updates, README, integration tests

## Changes Reviewed

| File | Change |
|------|--------|
| `hooks/gate.py` | Reads mode from config, appends "evaluate" to required skills when strict |
| `skills/implementation/SKILL.md` | Added DATA step (step 2) to slab cycle |
| `skills/precommit/SKILL.md` | Added G-IMPL-7 fixture provenance check to Step 2 |
| `skills/precommit/references/test-quality.md` | Added provenance to audit checklist |
| `README.md` | Added Strict Mode section, updated guardrails table (21 groups), updated session_monitor description |
| `tests/test_gate_strict.py` | 6 tests: strict requires evaluate, normal doesn't, score threshold, missing mode field |
| `tests/test_strict_mode.py` | 16 integration tests: lifecycle, drift accumulation, query reset, patch-forward, integrity check, context injection, drift score edge cases |

## Step 1: Instruction Compliance

- [x] gate.py reads mode, forces evaluate in strict — done (3 lines added)
- [x] DATA step in implementation SKILL.md — done (step 2 with G-IMPL-7 reference)
- [x] Precommit fixture provenance check — done (SKILL.md + test-quality.md)
- [x] README strict mode section — done (table + activation examples)
- [x] Integration test with simulated drift — done (16 tests)
- [x] project-state.md updated — done (local, gitignored)

## Step 2: Test Quality

**test_gate_strict.py (6 tests):**
- strict_mode_requires_evaluate_for_commit: `assert exit_code == 2` + `"evaluate" in output`
- strict_mode_allows_commit_with_both: `assert exit_code == 0`
- strict_mode_requires_evaluate_for_push: `assert exit_code == 2`
- normal_mode_minimal_does_not_require_evaluate: `assert exit_code == 0`
- strict_mode_evaluate_below_threshold_blocked: `assert exit_code == 2`
- no_mode_field_treated_as_normal: `assert exit_code == 0`

**test_strict_mode.py (16 tests):**
- Full lifecycle: init → state.json has mode=strict → monitor loads it → counters track
- Drift accumulation: 10 exchanges with no query → score=0.4 (exact float comparison)
- Query reset: curl resets exchanges_since_query to 0
- Patch-forward: test fail → source edit detected (count=1), with investigation (count=0)
- Integrity check: fires at exchange 15, includes drift score, critical drift stops session
- Normal mode: same scenario → all counters stay 0
- Drift score edge cases: boundary values at 0.3, 0.6, 0.8 thresholds

All tests use specific assertions. All would fail if feature deleted.

**Test quality: PASS** — 22 meaningful, 0 sloppy

## Step 2b: Test Suite

```
297 passed in 0.29s (was 275 — 22 new, 0 regressions)
```

## Step 3: Code Standards

- **gate.py change:** 3 lines — reads mode, appends evaluate if strict. Minimal and correct.
- **Skill text:** Descriptive, references G-IMPL-7 correctly.
- **README:** Matches implementation. Activation examples are real.
- **G-IMPL-6:** No shortcuts anywhere.

## Final Gate

```
Pre-commit report:
Instructions: 6/6 addressed
Test suite: 297 passed / 0 failed / 2 skipped (pre-existing)
Test quality: 22 meaningful, 0 sloppy
Principles: SOLID [ok] DRY [ok] KISS [ok] YAGNI [ok]
Standards: passed
Rules: 0 violations
G-IMPL-6: 0 shortcuts
README: UPDATED (strict mode section added)
App verification: N/A (hooks + docs)

[x] READY TO COMMIT
```
