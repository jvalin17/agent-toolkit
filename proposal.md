# Proposal: Orchestrator + Auto Mode

## Problem

Skills exist but don't chain automatically. Users must manually invoke each skill, approve each step, and remember to update README. This wastes tokens on ceremony and means quality gates get skipped when the user isn't watching.

The toolkit needs a foundation feature — not a new skill — that lets any skill chain into the next automatically, with quality gates enforced structurally.

## Scope

**This is a foundation feature for building basic apps with minimum token usage.** It is NOT for:
- Production systems serving millions of users
- Monetary/business decisions
- Infrastructure provisioning
- Anything requiring human judgment on risk

Auto mode builds starter apps, prototypes, and well-structured codebases that are easy to hand back to a human for refinement.

## Design Principle: Plan Before Code

**Every implementation MUST start with a concrete code change plan.** No file is touched until the plan exists and passes eval.

The plan is a file-by-file, function-by-function specification:

```
## Code Change Plan: [feature]

### New files
- `src/models/item.py` — Item dataclass: id, name, quantity, category_id, low_stock_threshold
- `src/routes/items.py` — CRUD endpoints: GET /items, POST /items, PUT /items/:id, DELETE /items/:id
- `tests/test_items.py` — 8 tests: create, read, update, delete, list, filter, low_stock, validation

### Modified files
- `src/main.py` — add items router (1 line: `app.include_router(items_router)`)
- `README.md` — add Items API section, env vars, test command

### Dependencies
- None new (uses existing FastAPI + SQLite)

### Evidence
- [D-ARCH-1] FastAPI chosen for CRUD-heavy app (functional-researcher output)
- [D-IMPL-1] SQLite sufficient at <1K users (scale-estimator)
- Requirement R3: "track items with name, quantity, category"
```

**Planning uses Opus (high accuracy). Implementation uses Sonnet/Haiku (cost-efficient).**
This split ensures quality decisions with cheap execution.

## Model Selection Strategy

| Phase | Model | Why |
|-------|-------|-----|
| Requirements gathering | Opus | Needs judgment, ambiguity detection |
| Architecture decisions | Opus | Trade-off analysis, evidence weighing |
| Code change planning | Opus | File-level design, dependency analysis |
| Implementation (code writing) | Sonnet/Haiku | Mechanical — plan already specifies what to write |
| Test writing | Sonnet/Haiku | Follows established patterns from plan |
| Precommit checks | Sonnet | Pattern matching against known rules |
| Evaluation | Opus | Quality judgment, nuanced scoring |
| Cleanup/README | Sonnet | Mechanical consolidation |

User can override: `/implementation auto model=opus inventory-app` forces Opus throughout.

## What Gets Built

### 1. `shared/orchestrator.md` — loaded by any skill when `auto` flag is passed

Not a new skill. A shared document (like `guardrails-quick.md`) that any skill reads when the user appends `auto`. Example: `/implementation auto inventory-app`.

**Core rules:**
- Chain: build → verify → precommit → readme validate+fix → eval gate → commit
- 95% eval gate default (configurable by user)
- Below 70% = hard stop, report to user
- 70-94% = auto-fix mechanical issues, re-eval once, then stop if still below 95%
- Commit requires precommit passing (all steps, no shortcuts)
- Evidence-first: never change code without citing requirement, test result, or code evidence
- Never assume: if a decision isn't obvious from docs, stop and ask
- Token-aware: track context usage, generate handoff before hitting reliable threshold (~25-32K)

**Auto-research:**
- Research agents (functional-researcher, tech-stack-advisor, pattern-advisor, scale-estimator) auto-trigger on signals:
  - New domain → functional-researcher (how do existing products do this?)
  - Tech choice needed → tech-stack-advisor
  - Pattern question → pattern-advisor
- Research stays scoped — top 2-3 findings, not exhaustive surveys
- Research output becomes evidence for decisions, not extra context to carry

**Pause triggers (stops and waits for user):**
- Ambiguous requirements / needs a judgment call
- Same failure twice after auto-fix attempt
- Output looks like data dump (the "walking score 72" problem)
- Eval below 70%
- Any decision that could affect cost, security, or external services

### 2. Upgrade `agents/readme-validator.md` — from read-only to validate+fix

Absorb the line-by-line validation and fix logic from the current `/readme` skill into the agent. The agent becomes the single place for README maintenance.

**What it gains (from current /readme skill):**
- Line-by-line claim extraction (install commands, features, file paths, endpoints, env vars, links, test details, code examples)
- Fix mode: auto-correct factual inaccuracies (wrong ports, dead paths, stale counts)
- Link verification: HTTP HEAD on every external link, flag 404s
- Test detail enforcement: README must document how to run tests, expected output, debugging
- Missing section detection: flag if README lacks install, run, test, env, or debug sections
- G-RM-1: never delete user-written prose (About, Contributing, License)
- G-RM-2: never fabricate features — if code doesn't have it, README must not claim it

**What stays the same:**
- Precommit Step 5b invokes it — now with fix capability, not just validation
- Triggered by G10 after feature changes

### 3. Delete `skills/readme/` and `skills/auto/`

Content preserved — `/readme` logic moves to readme-validator agent, `/auto` logic moves to `shared/orchestrator.md`. No functionality lost, two fewer skills.

Skill count: 14 → 13 (back to original count, but with stronger coverage).

### 4. Guardrail: G-AUTO-1

Added to `shared/guardrails-quick.md` and `shared/guardrails.md`:

```
G-AUTO-1: In auto mode, every change must cite its evidence source
(requirement ID, test result, code grep, research output). Never
change code based on assumption. If evidence is missing, stop and ask.
```

### 5. Handoff on context limit

**Location:** `HANDOFF.md` in project root. Orchestrator reads this FIRST on startup — before any other file. If it exists, orchestrator is resuming, not starting fresh.

**When generated:** Context approaching reliable threshold (~25-32K tokens), estimated via line/character counts (~4 chars per token). No external dependencies.

**Contents:**

```markdown
# HANDOFF: [project name]
<!-- Orchestrator reads this first. If this file exists, resume — don't restart. -->

## Status
- Phase: [IMPLEMENTATION / slab 3 of 4]
- Last commit: [hash] [message]
- Tests: [24 passing, 0 failing]
- Eval: [96% on last slab]

## What's Done
| Slab | Commit | Tests | Eval |
|------|--------|-------|------|
| 1. Walking skeleton | abc1234 | 4 | 96% |
| 2. Full CRUD | def5678 | 12 | 96% |

## What's Next
| Slab | Spec (from requirements) | Files to create/modify |
|------|--------------------------|----------------------|
| 3. Low stock alerts | "Notify when quantity < threshold" (R5) | src/alerts.py, tests/test_alerts.py |
| 4. Search + filter | "Filter by category, search by name" (R6) | src/routes/search.py, tests/test_search.py |

## Decisions
| ID | Decision | Evidence | Made By |
|----|----------|----------|---------|
| D-ARCH-1 | Python+FastAPI | functional-researcher: CRUD-heavy | /architecture |
| D-ARCH-2 | SQLite | scale-estimator: <1K users | /architecture |
| D-IMPL-1 | Repository pattern | pattern-advisor: testable CRUD | /implementation |

## Code Change Plan (for next slab)
[Pre-computed plan for slab 3 — ready to execute immediately]

## Resume
Run: `/implementation auto slab-3`
Read: requirements/inventory-app.md, architecture/inventory-app.md
Context: project-state.md has full feature status
```

**Key design choices:**
- Spec excerpts are actual requirement text (copied), not summaries — no lossy compression
- Code change plan for the NEXT slab is pre-computed before handoff — new session executes immediately, no planning overhead
- Commit hashes allow tracing back to exact state
- Decision IDs allow overriding specific choices without re-reading full context

### 6. Decision logging with typed IDs

Decisions get typed IDs in project-state.md. The prefix tells you which phase made the decision:

| Prefix | Phase | Example |
|--------|-------|---------|
| `D-REQ-` | Requirements | D-REQ-1: "MVP scope excludes reporting" |
| `D-ARCH-` | Architecture | D-ARCH-1: "FastAPI over Django — CRUD-only, no admin needed" |
| `D-IMPL-` | Implementation | D-IMPL-1: "Repository pattern for data access" |
| `D-SEC-` | Security | D-SEC-1: "bcrypt for password hashing" |
| `D-AUTO-` | Orchestrator | D-AUTO-1: "Skipped search slab — ambiguous requirement, paused for user" |

```
| ID | Decision | Evidence | Made By | Date |
|----|----------|----------|---------|------|
| D-ARCH-1 | Python+FastAPI | functional-researcher: CRUD-heavy apps favor Python | /architecture | 2026-05-19 |
| D-ARCH-2 | SQLite | scale-estimator: <1K users, single server | /architecture | 2026-05-19 |
| D-IMPL-1 | Repository pattern | pattern-advisor: testable CRUD separation | /implementation | 2026-05-19 |
```

When user comes back and wants to change something, they see WHY each choice was made. Changing D-ARCH-2 from SQLite to Postgres is a scoped change — the decision ID tells you what depends on it.

### 7. Cleanup phase (after successful completion)

After all slabs are committed and eval passes:

1. Consolidate key decisions from requirements/, architecture/, reports/ into README "Architecture Decisions" section
2. Update project-state.md: mark all features as verified
3. README becomes source of truth — includes:
   - What it does, install, run, test, debug, env vars
   - Key decisions with rationale (from decision log)
   - All links verified
4. Archive old .md artifacts to `archive/` directory with datestamp:
   - `archive/2026-05-19/requirements/inventory-app.md`
   - `archive/2026-05-19/reports/...`
   - README + project-state.md remain in project root as living documents
5. Delete `HANDOFF.md` — work is complete, no resume needed

### 8. Archive cleanup script

`scripts/cleanup-archive.sh` — deletes archive files older than 30 days.

```bash
#!/bin/bash
# Deletes archived .md files older than 30 days
ARCHIVE_DIR="${1:-.}/archive"
if [ -d "$ARCHIVE_DIR" ]; then
  find "$ARCHIVE_DIR" -name "*.md" -mtime +30 -delete
  find "$ARCHIVE_DIR" -type d -empty -delete
  echo "Cleaned archive files older than 30 days"
fi
```

Can be run manually, via cron, or as a post-completion step in the orchestrator.

### 9. Guardrail testing

All guardrails must be tested by the orchestrator after completion:
- G-IMPL-6 (no easy way out): scan all committed code
- G-PUSH-1 (precommit before commit): verify every commit had precommit pass
- G-PC-1 through G-PC-5: verify test quality, instruction compliance
- G-AUTO-1: verify every change has evidence citation
- README accuracy: full readme-validator pass on final README

If any guardrail violation is found post-completion, log it and flag to user.

### 10. Token tracking strategy

**Approach: line/character estimation (~4 chars per token for English).** Zero external dependencies.

| Approach evaluated | Verdict | Why |
|--------------------|---------|-----|
| Line/char estimation | **Use this** | Cheap, no deps, good enough for "am I near the danger zone?" |
| RAG / Vector DB | Skip | Not searching large doc collections. project-state.md is simple enough. |
| Graph RAG | Skip | Decision→evidence relationships fit in a markdown table. |
| MoE (Mixture of Experts) | N/A | Model architecture concern, not an implementation choice. |
| MCP server for token counting | **Revisit later** | Could expose precise token counts as a tool. Adds infrastructure dependency. Worth it only if estimation proves unreliable. |
| ADK (Agent SDK) | **Revisit later** | Relevant if we outgrow Claude Code's built-in Agent tool for multi-agent orchestration. Not needed now. |
| Harness engineering | **Use this** | Claude Code already has `/compact`, context compression, hooks. Use what's built in. |

**Implementation:** Orchestrator estimates tokens after each phase by summing character counts of conversation context. When estimate exceeds 25K tokens (~100K chars), trigger handoff generation.

## Inventory App Example (walkthrough, not implementation)

User says: `/requirements auto inventory-app`

```
Phase 1: REQUIREMENTS [Opus]
├─ Orchestrator activates, auto-triggers functional-researcher
│  └─ Researches: Sortly, inFlow — extracts CRUD, categories, alerts patterns
├─ /requirements asks Q1 (what?) + Q4 (how today?), drafts early
├─ Eval gate [Opus]: completeness ≥ 95%? YES → continue
├─ Writes: requirements/inventory-app.md, updates project-state.md
├─ Decisions: [D-REQ-1] MVP = CRUD + categories + alerts (evidence: functional-researcher)
└─ Tokens used: ~4K

Phase 2: ARCHITECTURE [Opus]
├─ Auto-triggers: tech-stack-advisor, pattern-advisor
├─ /architecture designs with evidence from research
│  └─ [D-ARCH-1] Python+FastAPI (evidence: CRUD-heavy)
│  └─ [D-ARCH-2] SQLite (evidence: <1K users, scale-estimator)
│  └─ [D-ARCH-3] Repository pattern (evidence: pattern-advisor, testable CRUD)
├─ Eval gate [Opus]: ≥ 95%? YES → continue
├─ Writes: architecture/inventory-app.md, updates project-state.md
└─ Tokens used: ~12K cumulative

Phase 3: CODE CHANGE PLAN [Opus]
├─ Produces concrete plan BEFORE any code is written:
│  └─ Slab 1: skeleton — files, functions, tests, dependencies listed
│  └─ Slab 2: CRUD — files, functions, tests listed
│  └─ Slab 3: alerts — files, functions, tests listed
│  └─ Slab 4: search — files, functions, tests listed
├─ Eval gate [Opus]: plan completeness, evidence for each file
├─ Writes: plan saved to project-state.md
└─ Tokens used: ~16K cumulative

Phase 4: IMPLEMENTATION [Sonnet — cheaper model] (slab-by-slab)
├─ Slab 1: Skeleton (plan says: 3 files, 4 tests)
│  ├─ Sonnet writes code following the plan exactly
│  ├─ Precommit [Sonnet]: tests ✓, G-IMPL-6 ✓, README updated
│  ├─ Eval [Opus]: 96% → auto-commit
│  └─ Tokens: ~22K cumulative
│
├─ Slab 2: Full CRUD + categories (plan says: 4 files, 12 tests)
│  ├─ Precommit + eval: 94% → auto-fix missing edge case → 96% → commit
│  └─ Tokens: ~32K — APPROACHING LIMIT
│
├─ ⚠️ CONTEXT CHECK: ~32K tokens estimated
│  ├─ HANDOFF.md generated with:
│  │  └─ Done: slabs 1-2, 16 tests, decisions D-ARCH-1 to D-IMPL-1
│  │  └─ Next: slab 3 spec (copied from requirements, not summarized)
│  │  └─ Code change plan for slab 3 (pre-computed, ready to execute)
│  │  └─ Resume: `/implementation auto slab-3`
│  └─ project-state.md updated with full status
│
├─ [New session reads HANDOFF.md first, continues]
├─ Slab 3: Low stock alerts (8 tests) → eval 97% → commit
├─ Slab 4: Search + filter (6 tests) → eval 95% → commit

Phase 5: FINAL QUALITY [Opus]
├─ /evaluate full: 95% overall
├─ readme-validator: validate+fix entire README
│  └─ Line-by-line: 42 claims verified, 0 broken links
│  └─ Test section: how to run, expected output, single test, coverage
│  └─ Debug section: logging, common issues
├─ Guardrail audit: all G-rules pass on committed code
└─ Auto-commit: "Final quality pass"

Phase 6: CLEANUP [Sonnet]
├─ Key decisions (D-ARCH-*, D-IMPL-*) → README "Decisions" section
├─ Archive: requirements/, architecture/, reports/ → archive/2026-05-19/
├─ project-state.md: all features verified
├─ Delete HANDOFF.md (work complete)
├─ README = source of truth
└─ Summary: 4 slabs, 30 tests, 95% eval, 6 commits
```

**If user comes back and says "I don't like the categories design":**
1. Read project-state.md → see [D3] categories decision with evidence
2. User gives new requirements
3. Change is 1 slab (SOLID/DRY enforced, components isolated, tests catch cascading breaks)
4. Not a rewrite — structured code means structured changes

## What's NOT in scope

- Multi-service architectures (orchestrator builds single apps)
- Cost/pricing decisions (always defers to user)
- Infrastructure provisioning (no cloud deploys)
- Long-running background processes without user authorization
- Pushing to remote without explicit prior auth

## Concrete File Change Plan

| # | Action | File | What changes | Lines est. |
|---|--------|------|-------------|------------|
| 1 | Create | `shared/orchestrator.md` | Auto mode rules, chaining protocol, evidence-first, plan-before-code, model selection, token tracking, handoff protocol, cleanup | ~150 |
| 2 | Modify | `agents/readme-validator.md` | Absorb /readme fix logic: line-by-line claim extraction, fix mode, link verification, test detail enforcement, missing section detection, G-RM-1/2/3 | +80 lines |
| 3 | Modify | `shared/guardrails.md` | Add G-AUTO-1 (evidence-first in auto mode) | +10 lines |
| 4 | Modify | `shared/guardrails-quick.md` | Add G-AUTO-1 one-liner | +1 line |
| 5 | Modify | `skills/precommit/SKILL.md` | Step 5b: invoke readme-validator in fix mode (not just validate). Reference orchestrator for auto mode behavior | +5 lines |
| 6 | Modify | `shared/project-state-template.md` | Decision ID column (typed: D-ARCH, D-IMPL, etc.), resume section, code change plan section | +20 lines |
| 7 | Delete | `skills/readme/SKILL.md` | Content preserved in readme-validator agent (#2) | -225 lines |
| 8 | Delete | `skills/auto/SKILL.md` | Content preserved in orchestrator (#1) | -180 lines |
| 9 | Create | `scripts/cleanup-archive.sh` | Delete archive files older than 30 days | ~10 lines |
| 10 | Modify | `README.md` | Update skill count (14→13), add orchestrator section, update guardrails list | ~20 lines |
| 11 | Modify | `HANDOFF.md` | Update counts, add orchestrator to infrastructure section | ~10 lines |

**Net change:** +80 lines new content, -405 lines deleted (consolidated, not lost). Fewer files, stronger coverage.

## Resolved decisions

| # | Question | Decision | Rationale |
|---|----------|----------|-----------|
| 1 | Handoff file location | Project root as `HANDOFF.md` | Orchestrator reads it first on startup — must be discoverable |
| 2 | Decision ID format | Typed: `D-ARCH-1`, `D-IMPL-1`, `D-REQ-1`, etc. | Prefix tells you which phase, enables scoped overrides |
| 3 | Token tracking | Line/char estimation (~4 chars/token) | Zero deps, good enough. MCP server is a future option if estimation proves unreliable |
| 4 | Cleanup | Archive to `archive/` + 30-day cleanup script | Safe default — nothing lost, clutter managed automatically |
| 5 | Auto-research depth | Top 2-3 products/patterns | Fewer tokens, sufficient context for decisions |
| 6 | Plan before code | Mandatory — Opus plans, Sonnet/Haiku implements | Quality decisions, cheap execution |

## Open questions for reviewer

1. **Auto-research scope** — should research agents auto-trigger on signals (new domain, tech choice), or only when the planning phase explicitly needs them?
2. **Handoff threshold** — 25K tokens estimated (~100K chars)? Or should it be configurable per session?
3. **Model override syntax** — `/implementation auto model=opus` or `/implementation auto --opus`? Or should model selection be in a project config?
4. **Cleanup trigger** — run cleanup automatically after final quality pass, or require explicit `/cleanup` invocation?
5. **Guardrail testing depth** — full re-scan of all committed code post-completion, or spot-check only files changed in this auto run?
