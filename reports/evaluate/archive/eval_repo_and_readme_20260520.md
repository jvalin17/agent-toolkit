# Evaluation: agent-toolkit + README
# Repo score: 91% (A) | README score: 84% (B)

**Evaluated:** 2026-05-20  
**Commit:** `cb32e2e`  
**Tests:** 13/13 `test_gate.py`, 43/43 `test-hooks.sh`

---

## Part 1 — Repository (91%)

| Dimension | Score | Weight | Weighted |
|-----------|-------|--------|----------|
| Completeness | 93% | 30% | 27.9 |
| Code Quality | 90% | 25% | 22.5 |
| Security | 88% | 20% | 17.6 |
| Test Quality | 94% | 15% | 14.1 |
| Efficiency | 88% | 10% | 8.8 |
| **Overall** | | | **91%** |

### Strengths

- **13 skills, 9 agents**, gate module (`attest`, `core`, `keys`, `reports`), bootstrap, CI workflow template.
- **All tests green** after bootstrap/signed test fix.
- **Legacy-first** defaults in `templates/gates.json`, `gate/core.py`, `gate.sh`, root `gates.json`.
- **Session monitor** (40 min warn / 50 min hard stop) matches short-session guidance.
- **Report-bound attestation** + optional signed JWT; `shared/gate-unlock.md` aligned with skills.
- **precommit** trimmed to 118 lines + references.

### Remaining repo gaps (not blocking A)

| Issue | Severity |
|-------|----------|
| Bootstrap still creates `.gate/signing.key` even in legacy mode | Low — unused key file |
| `update.sh` lives at repo root, not `hooks/` | Low — README table lists it as hook #8 (correct behavior, tree omits it) |
| Toolkit CI (`gate.yml`) may need secret for signed self-attest | Optional maintainer-only |

---

## Part 2 — README accuracy (84%)

Line-by-line check of claims vs repo at `cb32e2e`.

### PASS — verified accurate

| Claim | Evidence |
|-------|----------|
| 13 skills | 13 `skills/*/SKILL.md` |
| 9 agents | 9 `agents/*.md` |
| 8 harness hooks | 7 `hooks/*.sh` + `update.sh` (installed via `install.sh`) |
| `./install.sh`, `./generate-project-rules.sh` | Files exist, executable |
| Apache 2.0 LICENSE | `LICENSE` present |
| Health check ~twice monthly | `.github/workflows/updater.yml` cron `1,15` |
| Session monitor 15/40 warn, 20/50 stop | `hooks/session-monitor.sh:18-21` |
| Legacy default in examples | `templates/gates.json`, root `gates.json` |
| HS256 / PyJWT, no cryptography | `gate/requirements.txt`, `gate/keys.py` |
| `gate/reports.py` attestation | File exists |
| Portability table (harness Claude-only) | Accurate |
| Architecture line counts (most) | precommit ~118, explore ~143, etc. within ~10 lines |
| Consumer secret on own repo only | Matches bootstrap + README § Gate modes |

### FAIL / PARTIAL — README drift

| # | Location | Issue | Fix |
|---|----------|-------|-----|
| 1 | L38 | Says install "configures **signed gates**" | Bootstrap configures gates; default is **legacy**. Say "project gates (legacy by default)". |
| 2 | L170 | "template may use `signed`" | **False** — `templates/gates.json` is `legacy`. Remove stale clause. |
| 3 | L171 | Implies signing key only for signed | Bootstrap **always** creates `.gate/signing.key` | Clarify: key created always; used only in signed mode. |
| 4 | L204 | minimal profile "`/precommit` (mechanical)" | Profiles require **skills**; mechanical is attest internals | Say "`/precommit`" only. |
| 5 | L221–228 | "**Signed gates** from scratch" as primary path | Conflicts with legacy-first doc | Rename to "Optional signed setup" or lead with legacy example. |
| 6 | L313–317 | Steps 1 and 2 **duplicate** `install.sh` | Edit merge error | Single install step. |
| 7 | L327 | "gate-token.jwt" only | Legacy path uses `.gates/` — add "or legacy flags" | Already partly fixed elsewhere; this block still JWT-only. |
| 8 | Tagline L9 / Guardrails L429 | "**17 guardrails**" | Table lists G1–G14 + G-IMPL-6 + G-PUSH + G-AUTO + G-SESSION + **G-PC-1–5** (5) → **22+** named rules | Say "~17 core" or count explicitly (e.g. 14 universal + 3 commit/session + 5 precommit). |
| 9 | Architecture L486–488 | `scripts/` omits `seed-gate-reports.sh` | File exists | Add to tree. |
| 10 | Architecture L470–478 | Omits `update.sh` at repo root | 8th hook | Add `update.sh` under root or note in hooks section. |
| 11 | assess ~164 lines | Actual **168** lines | Minor |
| 12 | reviewer 103 lines | Actual **107** lines | Minor |

### README score breakdown

| Category | Score |
|----------|-------|
| Inventory badges (skills/agents/hooks) | 100% |
| Install / quick start commands | 95% |
| Gate modes section (legacy vs signed) | 92% |
| Harness hook table | 95% |
| Examples & onboarding flows | 75% (duplicates, signed-first example) |
| Architecture tree | 82% |
| Guardrails count | 70% |

**README overall: 84% (B)** — Strong gate-mode narrative; fix 6–8 stale lines for A range.

---

## Combined verdict

| Artifact | Score | Grade |
|----------|-------|-------|
| **Repository** | **91%** | **A** |
| **README** | **84%** | **B** |
| **Combined** | **88%** | **B+** |

The **codebase is production-ready** for legacy-first daily use; the **README is good but not fully trustworthy** until the drift items above are fixed (especially L38, L170, duplicate install steps, and "17 guardrails" count).

**95% gate:** Repo is there for maintainers; README fixes would bring combined doc+repo trust to A range.

---

## To reach 95% README

1. Fix L38, L170–171, L313–317 (5 min).
2. Retitle "Signed gates from scratch" → optional path.
3. Fix minimal profile wording (remove "mechanical").
4. Reconcile guardrail count (17 vs 22).
5. Update architecture tree (`update.sh`, `seed-gate-reports.sh`, line counts).
