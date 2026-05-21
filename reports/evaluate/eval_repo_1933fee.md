# Evaluation: agent-toolkit (repository)
# Score: **87%** (B+)

**Evaluated:** 2026-05-20  
**Commit:** `1933fee`  
**Prior score:** 88% (B+) — `eval_agent-toolkit_103f6d3.md`

| Dimension | Score | Weight | Weighted |
|-----------|-------|--------|----------|
| Completeness | 86% | 30% | 25.8 |
| Code Quality | 85% | 25% | 21.3 |
| Security | 95% | 20% | 19.0 |
| Test Quality | 80% | 15% | 12.0 |
| Efficiency | 92% | 10% | 9.2 |
| **Overall** | | | **87.3% → 87%** |

## Grade: B+ (85–89%)

**Threshold note:** Toolkit `eval_threshold` is 95%. This run does **not** unlock push gates via evaluate (87% < 95%).

---

## Executive summary

The repo delivers on its core promise: **13 skills**, **9 agents**, **10 structural hooks**, dual gate modes (legacy default), auto-continuation (`claude-auto` / `auto_continue.py`), and a strong local test suite (**117/117 pytest**, **55/55 hook tests**). Since the prior eval (`103f6d3`), **G-SESSION-1** is now in `shared/guardrails.md`, **`hooks/gates.json`** matches the template schema, and **`project-state.md`** is current.

Score remains below 95% because: **CI only runs 16 gate tests** (not the full 117), the README **"19 guardrail groups"** claim does not reconcile with the 11-group taxonomy in the same doc, and **`auto_continue.py`** has a silent `except: pass` on state reads.

**Tests run:** `python3 -m pytest tests/ -q` → 117 passed; `bash tests/test-hooks.sh` → 55 passed.

---

## Findings by dimension

### Completeness (86%)

| # | Claim | Status | Evidence |
|---|-------|--------|----------|
| 1 | 13 skills | PASS | 13× `skills/*/SKILL.md` |
| 2 | 9 agents | PASS | 9× `agents/*.md` |
| 3 | 10 structural hooks | PASS | 7× `hooks/*.sh` + 2× `hooks/*.py` + `update.sh`; badge `README.md:5` |
| 4 | Legacy + warn + minimal default | PASS | `gates.json:2-4`, `templates/gates.json:2-4` |
| 5 | Signed mode + bootstrap scripts | PASS | `gate/core.py`, `scripts/setup-signed-gates.sh` |
| 6 | install.sh wires Python hooks | PASS | `install.sh:128-130` uses `session_init.py`, `session_monitor.py` |
| 7 | Auto-continuation shipped | PASS | `scripts/auto_continue.py`, `scripts/claude-auto`, `README.md:178-200` |
| 8 | claude-auto install wiring | PASS | `install.sh:381-409` |
| 9 | Gate unit tests green | PASS | 16/16 `tests/test_gate.py` |
| 10 | Hook regression suite green | PASS | 55/55 `tests/test-hooks.sh` |
| 11 | Full local pytest green | PASS | 117/117 @ `1933fee` |
| 12 | G-SESSION-1 in canonical guardrails | PASS | `shared/guardrails.md:126-131` (fixed since `103f6d3`) |
| 13 | hooks/gates.json schema aligned | PASS | `hooks/gates.json` matches `templates/gates.json` profiles |
| 14 | project-state.md current | PASS | `project-state.md:1-28` updated 2026-05-20 |
| 15 | README badge counts (13/9/10) | PASS | Matches tree |
| 16 | README "19 guardrail groups" verifiable | PARTIAL | `README.md:9,219` claim "19"; guardrails table `README.md:221-230` enumerates **11** named groups |
| 17 | CI runs full pytest suite | FAIL | `.github/workflows/gate.yml:32` runs only `tests/test_gate.py`; 101 tests (init/monitor/auto_continue) excluded |

**Score:** 14 PASS, 1 FAIL, 1 PARTIAL → (14 + 0.5) / 17 = **86%**

---

### Code Quality (85%)

| # | Check | Status | File:Line | Issue |
|---|-------|--------|-----------|-------|
| 1 | Gate module SRP | PASS | `gate/attest.py`, `core.py`, `keys.py`, `reports.py` | Clear split |
| 2 | No god files | PASS | Max `hooks/session_monitor.py` 397 lines | Under 500 |
| 3 | precommit/evaluate SKILL ≤250 lines | PASS | 118 / 180 lines | |
| 4 | No silent except in gate/ | PASS | grep gate/ | Clean |
| 5 | G-SESSION in full guardrails | PASS | `shared/guardrails.md:126` | Fixed |
| 6 | hooks/gates.json coherent | PASS | Matches template | Fixed |
| 7 | auto_continue readable structure | PASS | `scripts/auto_continue.py` | Class + focused methods |
| 8 | Silent catch on state read | FAIL | `scripts/auto_continue.py:161-162` | `except (json.JSONDecodeError, OSError): pass` swallows errors |
| 9 | README guardrail taxonomy clarity | PARTIAL | `README.md:9` vs `:221-230` | "19 groups" vs 11-row table |
| 10 | Naming / readability in tests | PASS | `tests/test_auto_continue.py` | Descriptive class names |
| 11 | Intentional bash+python hook pairs | PASS | `session-init.sh` + `session_init.py` | Documented migration path |
| 12 | shared/gate-unlock.md coherent | PASS | Legacy vs signed tables | |

**Score:** 9 PASS, 1 FAIL, 1 PARTIAL → (9 + 0.5) / 11 = **86%** → **85%** (doc-only partial weighted down)

---

### Security (95%)

| # | Check | Status | File:Line | Issue |
|---|-------|--------|-----------|-------|
| 1 | Signing keys gitignored | PASS | `.gitignore:19-24` | |
| 2 | No hardcoded secrets in source | PASS | grep `api_key\|password\|secret=` | None in code |
| 3 | JWT tamper rejected | PASS | `tests/test_gate.py` | |
| 4 | Wrong commit SHA rejected | PASS | `tests/test_gate.py` | |
| 5 | Low eval score blocked at issue | PASS | `tests/test_gate.py` | |
| 6 | `.session/` agent writes blocked | PASS | `hooks/session_monitor.py`, hook tests | G-SESSION-1 structural |
| 7 | Report SHA-256 in attestation | PASS | `test_attest_on_toolkit_repo_*` | |
| 8 | Legacy default reduces secret sprawl | PASS | `gates.json` legacy | Documented |
| 9 | Silent state-read catch (integrity) | PARTIAL | `auto_continue.py:161-162` | Wrong exit-reason classification possible |

**Score:** 8 PASS, 1 PARTIAL → **95%**

---

### Test Quality (80%)

| # | Check | Status | File:Line | Issue |
|---|-------|--------|-----------|-------|
| 1 | Gate JWT full matrix | PASS | 16 tests `tests/test_gate.py` | |
| 2 | session_init coverage | PASS | 33 tests | Goal/handoff/gates/context |
| 3 | session_monitor coverage | PASS | 38 tests | Thresholds, blocking, grace |
| 4 | auto_continue coverage | PASS | 30 tests | Goal, loop, CLI, launch |
| 5 | Hook integration matrix | PASS | 55 cases `tests/test-hooks.sh` | |
| 6 | No sloppy `assert True` | PASS | grep tests/ | None |
| 7 | Weak timestamp assertion | FAIL | `tests/test_auto_continue.py:196` | `assert "202" in content` — G-PC-1 violation |
| 8 | CI runs full pytest | FAIL | `.github/workflows/gate.yml:32` | 101/117 tests not in CI |
| 9 | install.sh e2e | PARTIAL | — | Wired but not tested |
| 10 | update.sh behavior tested | PARTIAL | — | Hook registered, no dedicated test |
| 11 | Tests fail if feature deleted | PASS | Unit tests assert specific values | |
| 12 | Edge cases (corrupt state, grace) | PASS | `test_session_monitor.py`, `test_session_init.py` | |

**Score:** 7 PASS, 2 FAIL, 2 PARTIAL → (7 + 1) / 11 = **73%** → **80%** with credit for strong local coverage

---

### Efficiency (92%)

| # | Check | Status | File:Line | Issue |
|---|-------|--------|-----------|-------|
| 1 | Gate deps minimal (PyJWT only) | PASS | `gate/requirements.txt` | Single dep |
| 2 | Legacy default = less JWT overhead | PASS | `templates/gates.json` | Fits short sessions |
| 3 | No over-engineered abstractions | PASS | gate/, hooks/ | Appropriate for toolkit scale |
| 4 | Bash+Python hook duplication | PARTIAL | `session-init.sh` + `session_init.py` | Migration cost, documented |
| 5 | Right tool for scale | PASS | Shell hooks + small Python | No unnecessary services |
| 6 | File size targets mostly met | PASS | Skills ≤250 line target in updater | |

**Score:** 5 PASS, 1 PARTIAL → **92%**

---

## To Reach 95%

1. **Expand CI pytest** — change `.github/workflows/gate.yml:32` to `python -m pytest tests/ -q` (+5–8% test quality, +2% completeness).
2. **Fix weak timestamp test** — replace `assert "202" in content` with ISO-8601 regex in `tests/test_auto_continue.py:196` (+2% test quality).
3. **Remove silent except** — log or return fallback explicitly in `auto_continue.py:161-162` (+3% code quality).
4. **Reconcile guardrail count** — either count to 19 with evidence or change README to match the 11-group table (+2% completeness, +2% code quality).

---

## Delta from prior eval (103f6d3 → 1933fee)

| Item | Before | Now |
|------|--------|-----|
| G-SESSION-1 in `guardrails.md` | FAIL | PASS |
| `hooks/gates.json` schema | FAIL | PASS |
| `project-state.md` stale | FAIL | PASS |
| auto_continue + tests | UNVERIFIED | PASS (30 tests) |
| CI full pytest | FAIL | FAIL (unchanged) |
| README guardrail count | FAIL (17 vs 19) | PARTIAL (19 vs 11-table) |
| Overall | 88% | **87%** |

Net: doc/harness fixes offset by stricter grading on CI gap and test-quality checks now that 117 tests exist locally but CI ignores most of them.
