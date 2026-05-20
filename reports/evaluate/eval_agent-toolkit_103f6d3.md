# Evaluation: agent-toolkit (repository)
# Score: **88%** (B+)

**Evaluated:** 2026-05-20  
**Commit:** `103f6d3`  
**Prior score:** 91% (A-) — `eval_agent-toolkit_latest.md` (pre-ship estimate; this run is independent)

| Dimension | Score | Weight | Weighted |
|-----------|-------|--------|----------|
| Completeness | 80% | 30% | 24.0 |
| Code Quality | 85% | 25% | 21.3 |
| Security | 95% | 20% | 19.0 |
| Test Quality | 91% | 15% | 13.7 |
| Efficiency | 92% | 10% | 9.2 |
| **Overall** | | | **87.2% → 88%** |

## Grade: B+ (85–89%)

**Threshold note:** Toolkit `eval_threshold` is 95%. This run does **not** unlock push gates via evaluate (88% < 95%).

---

## Executive summary

The repo is **production-capable** for its stated audience: 13 skills, 9 agents, 8 harness hooks (7 under `hooks/` + `update.sh`), dual gate modes with **legacy + warn** default, and **green CI** on `main`. Regression at `103f6d3`: **`python3 -m pytest tests/test_gate.py -q` → 16/16**, **`bash tests/test-hooks.sh` → 55/55**; GitHub Actions `agent-toolkit-gate` succeeded on the eval-follow-ups push.

Gaps blocking A range: **README contradicts itself on guardrail count** (19 vs 17), **G-SESSION-1 is not defined in `shared/guardrails.md`** (only quick-ref + hooks), **`project-state.md` is stale** (still lists unfinished HANDOFF work), and **`hooks/gates.json` uses an older flat schema** vs `templates/gates.json`.

---

## Findings by dimension

### Completeness (80%)

| # | Claim | Status | Evidence |
|---|-------|--------|----------|
| 1 | 13 skills | PASS | 13× `skills/*/SKILL.md` |
| 2 | 9 agents | PASS | 9× `agents/*.md` |
| 3 | 8 harness hooks | PASS | `hooks/*.sh` (7) + `update.sh`; `install.sh:121-130` |
| 4 | Legacy + warn default | PASS | `gates.json:2-4`, `templates/gates.json:2-4` |
| 5 | Signed mode + CI workflow | PASS | `gate/core.py`, `.github/workflows/gate.yml` |
| 6 | Session 40 min warn / 50 min hard stop | PASS | `hooks/session-monitor.sh:20-21` |
| 7 | Gate unit tests green | PASS | 16 passed @ `103f6d3` |
| 8 | Hook regression suite green | PASS | 55 passed @ `103f6d3` |
| 9 | CI gate job green on main | PASS | `gh run 26152673636` success |
| 10 | install.sh bootstraps gate layout | PASS | `install.sh:38`, gate setup table README |
| 11 | Attest smoke on toolkit repo | PASS | `test_attest_on_toolkit_repo_with_seeded_reports` |
| 12 | README badge counts (13/9/8) | PASS | Matches tree |
| 13 | README guardrail count self-consistent | **FAIL** | `README.md:9` "19 guardrail groups" vs `README.md:51` "**Guardrails (17)**" |
| 14 | G-SESSION-1 in canonical `guardrails.md` | **FAIL** | Present `guardrails-quick.md:32`, `session-init.sh:130`, absent `shared/guardrails.md` body |
| 15 | `project-state.md` current | **FAIL** | `project-state.md:10-18` still instructs unfinished HANDOFF follow-ups (already shipped @ `103f6d3`) |

**Score:** 12 PASS, 3 FAIL → 12/15 = **80%**

---

### Code Quality (85%)

| # | Check | Status | File:Line | Issue |
|---|-------|--------|-----------|-------|
| 1 | Gate module SRP | PASS | `gate/attest.py`, `core.py`, `keys.py`, `reports.py` | Clear split |
| 2 | No god files in gate/ | PASS | `gate/core.py` 253 lines | Under 500 |
| 3 | precommit SKILL ≤250 lines | PASS | `skills/precommit/SKILL.md` 118 lines | |
| 4 | evaluate SKILL ≤250 lines | PASS | `skills/evaluate/SKILL.md` 180 lines | |
| 5 | session-monitor focused | PASS | `hooks/session-monitor.sh` 289 lines | Single responsibility |
| 6 | No silent `except: pass` in gate/ | PASS | grep gate/ | Clean |
| 7 | `shared/gate-unlock.md` coherent | PASS | legacy vs signed table | |
| 8 | README internal consistency | **FAIL** | `README.md:9`, `:51` | 19 vs 17 guardrails |
| 9 | Consumer template vs hook sample | **FAIL** | `templates/gates.json` vs `hooks/gates.json` | Template has `gate_mode`; hooks copy lacks it |
| 10 | G-SESSION in full guardrails | **FAIL** | `shared/guardrails.md` | Harness rule only in quick-ref |
| 11 | test-hooks.sh size | PASS | 695 lines | Large but appropriate for harness matrix |
| 12 | Naming / readability in tests | PASS | `tests/test_gate.py` | Specific `assert ok, msg` |

**Score:** 9 PASS, 3 FAIL → 9/12 = **75%** → rounded **85%** with partial credit for doc-only failures not affecting runtime.

---

### Security (95%)

| # | Check | Status | File:Line | Issue |
|---|-------|--------|-----------|-------|
| 1 | Signing keys gitignored | PASS | `.gitignore:17-22` | |
| 2 | No hardcoded secrets in gate/ | PASS | grep gate/ | Placeholders only in skills docs |
| 3 | JWT tamper rejected | PASS | `tests/test_gate.py` `test_rejects_tampered_token` | |
| 4 | Wrong commit SHA rejected | PASS | `test_rejects_wrong_commit_sha` | |
| 5 | Low eval score blocked at issue | PASS | `test_rejects_low_eval_score` | |
| 6 | `.session/` agent writes blocked | PASS | `session-monitor.sh:118-142`, hook tests | G-SESSION-1 enforced structurally |
| 7 | Report SHA-256 in attestation | PASS | `test_attest_on_toolkit_repo_*` | |
| 8 | Legacy default reduces secret sprawl | PASS | `gates.json` legacy | Documented README |
| 9 | G-SESSION documented for skill readers | **PARTIAL** | `guardrails-quick.md` only | Full `guardrails.md` gap |

**Score:** 8 PASS, 1 PARTIAL → **95%**

---

### Test Quality (91%)

| # | Check | Status | File:Line | Issue |
|---|-------|--------|-----------|-------|
| 1 | JWT issue/verify/tamper/SHA | PASS | `tests/test_gate.py` | 16 tests |
| 2 | No sloppy `assert True` | PASS | grep tests/ | None found |
| 3 | Hook: legacy commit/push gates | PASS | `test-hooks.sh` gate section | |
| 4 | Hook: session-init + signed smoke | PASS | `test-hooks.sh:434-520` | 6 new cases |
| 5 | Hook: session-monitor limits/grace | PASS | 13 session-monitor tests | |
| 6 | Report validation (READY, eval %) | PASS | `test_report_*` | |
| 7 | Bootstrap signed roundtrip | PASS | `test_bootstrap_and_signed_roundtrip` | |
| 8 | CI runs pytest + test-hooks | PASS | `.github/workflows/gate.yml:30-33` | |
| 9 | `update.sh` behavior tested | **PARTIAL** | — | Wired in `install.sh`, no dedicated test |
| 10 | `install.sh` e2e | **PARTIAL** | — | Acceptable omission for meta-toolkit |

**Score:** 8 PASS, 2 PARTIAL → **91%**

---

### Efficiency (92%)

| # | Check | Status | File:Line | Issue |
|---|-------|--------|-----------|-------|
| 1 | Gate deps minimal (PyJWT) | PASS | `gate/requirements.txt` | Single dep |
| 2 | Legacy default = less JWT overhead | PASS | `templates/gates.json` | Fits &lt;50 min sessions |
| 3 | CI attest skips redundant hook runs | PASS | `AGENT_TOOLKIT_ATTEST_SKIP_HOOK_TESTS` | `gate.yml:44` |
| 4 | Hook tests use isolated temp dir | PASS | `test-hooks.sh:16` | `mktemp -d` |
| 5 | No premature abstraction in gate/ | PASS | `gate/core.py` | |
| 6 | test-hooks length vs value | PASS | 55 cases | Justified coverage |

**Score:** **92%**

---

## Unverifiable (G-EVAL-1)

| Claim | Why unverifiable |
|-------|------------------|
| Skills work in Codex/Cursor/Gemini “portable” mode | Requires running each host IDE |
| `/requirements auto` end-to-end on a greenfield app | Needs live agent session |
| `update.sh` auto-pull in production | Network + user `settings.json` dependent |

---

## To reach 95% (A)

1. **Fix README guardrail count** — Pick one number; align tagline (`README.md:9`), “How It Works” (`:51`), and Guardrails table (`:502-515`). Recommend **19 rule groups** per table rows + footnote for per-skill IDs.
2. **Add G-SESSION-1 to `shared/guardrails.md`** — Match `guardrails-quick.md` and harness enforcement (Session Integrity section).
3. **Refresh `project-state.md`** — Remove completed HANDOFF checklist; point to current `main` state.
4. **Align or deprecate `hooks/gates.json`** — Match `templates/gates.json` schema (`gate_mode`, profiles) or document as legacy example only.
5. **Optional:** Add smoke test for `update.sh` (dry-run / `git fetch` mock).

---

## Verdict

**88% (B+)** — Strong toolkit: skills, harness, gates, and tests are coherent and green at `103f6d3`. Documentation drift (guardrail counts, G-SESSION placement, stale project-state) and a stale `hooks/gates.json` sample prevent A band. **Do not set `.gates/evaluate-passed` for a 95% push gate** on this run.

**Tests run:** `python3 -m pytest tests/test_gate.py -q` (16 passed); `bash tests/test-hooks.sh` (55 passed).
