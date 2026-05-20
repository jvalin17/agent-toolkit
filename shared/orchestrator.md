# Orchestrator — Auto Mode Protocol

> Loaded by any skill when the user appends `auto` to their invocation.
> Example: `/implementation auto inventory-app`, `/requirements auto my-project`
>
> This is NOT a skill. It is a shared protocol that modifies how existing skills behave.
> Without `auto`, every skill works exactly as before — no behavior changes.

## When Auto Mode Activates

| User says | Auto mode? |
|-----------|-----------|
| `/implementation auto X` | Yes — chain after implementation completes |
| `/requirements auto X` | Yes — chain full pipeline from requirements |
| "build X and commit when ready" | Yes — infer auto from intent |
| "auto", "hands-off", "I'll be away" | Yes |
| `/implementation X` (no auto flag) | No — normal interactive mode, this file is not read |

## Core Principles

1. **Never stop to ask between skills.** Auto mode means AUTO. Chain skills without pausing for confirmation. Do not ask "Ready to continue?" or "Should I proceed?" — just proceed. The only reason to pause is ambiguity or failure, not ceremony.
2. **Plan before code.** No file is touched until a concrete code change plan exists and passes eval.
3. **Evidence-first (G-AUTO-1).** Every change cites its source: requirement ID, test result, code grep, or research output. Never assume.
4. **Minimum tokens.** Use the cheapest model that can do the job. Plan with Opus, implement with Sonnet/Haiku.
5. **All gates still apply.** Auto mode removes user wait time between passing steps — it does NOT lower quality bars.
6. **Stop ONLY on:** ambiguity that can't be resolved from docs, same failure twice after auto-fix, eval < 70%. NOT on skill transitions.
7. **Backward compatible.** Without `auto` flag, nothing changes. Every skill works exactly as before.

## What "Auto" Means — No Stopping

**CRITICAL:** When `auto` is set, the agent MUST NOT:
- Ask "Ready to continue to /implementation?" — just run it
- Ask "Should I proceed with the next slab?" — just build it
- Ask "Want me to commit?" — if precommit passes, commit
- Present a summary and wait — present and immediately continue
- Ask for confirmation between any two skills in the pipeline

**The ONLY acceptable pauses:**
- A requirement is genuinely ambiguous (not just complex)
- The same fix has failed twice
- Eval score is below 70%
- A decision affects cost, security, or external services

Everything else: **keep going.**

## Model Selection

| Phase | Model | Why |
|-------|-------|-----|
| Requirements gathering | Opus | Judgment, ambiguity detection |
| Architecture decisions | Opus | Trade-off analysis, evidence weighing |
| Code change planning | Opus | File-level design, dependency analysis |
| Implementation | Sonnet/Haiku | Mechanical — plan specifies what to write |
| Test writing | Sonnet/Haiku | Follows patterns from plan |
| Precommit checks | Sonnet | Pattern matching against rules |
| Evaluation | Opus | Quality judgment, nuanced scoring |
| README/Cleanup | Sonnet | Mechanical consolidation |

User can override: `/implementation auto model=opus X` forces Opus throughout.

## Auto Pipeline

```
1. RESUME?    — read HANDOFF.md if it exists (resume, don't restart)
2. RESEARCH   — auto-trigger relevant agents for context
3. PLAN       — concrete code change plan (file-by-file, function-by-function)
4. EVAL PLAN  — plan must score ≥ 95% completeness before implementation starts
5. BUILD      — /implementation per slab (Sonnet/Haiku)
6. VERIFY     — /verify (output quality, skip user-confirms)
7. GATE       — /precommit full mode (tests, G-IMPL-6, standards, README)
8. EVAL       — /evaluate quick on slab (must score ≥ 95%)
9. COMMIT     — auto-commit with descriptive message
10. NEXT      — loop to step 5 for next slab, or FINAL QUALITY
11. FINAL     — /evaluate full, readme-validator fix, guardrail audit
12. CLEANUP   — archive artifacts, README = source of truth
```

## Step 1: Resume Check

On startup, check for `HANDOFF.md` in project root.

- **If exists:** This is a resumed session. Read handoff, skip to the step indicated. Do NOT re-plan or re-research what's already done.
- **If not exists:** Fresh start. Proceed to step 2.

Also read `project-state.md` if it exists — check decisions, feature status, warnings.

## Step 2: Auto-Research

**CRITICAL: When user input is sparse (one-liner like "build inventory app"), research is MANDATORY before building.** Don't assume what the app needs — investigate what every app in that category has. The one-line input defines the domain. Research fills in the details.

Ask: "What does every app in this category have?" — not "What did the user literally say?"

**Why this rule exists:** The orchestrator once assumed a basic CRUD app for "inventory app", missed barcode scanning (core to any real inventory workflow), missed pricing/sales tracking, and built a non-interactive dashboard. All table-stakes features that 5 minutes of research would have caught.

Trigger research agents:

| Signal | Agent | Scope |
|--------|-------|-------|
| **Sparse input / new domain** | functional-researcher | **ALWAYS for one-liners.** Top 2-3 products, extract table-stakes features, common workflows, domain-specific patterns |
| Tech choice needed | tech-stack-advisor | Options with trade-offs, don't decide |
| Design pattern question | pattern-advisor | 2-3 patterns with when-to-use |
| Scale mentioned | scale-estimator | Back-of-envelope numbers |

**Rules:**
- Sparse input = functional-researcher is MANDATORY, not optional
- Research output becomes evidence for decisions (cited as `[functional-researcher]`, `[tech-stack-advisor]`)
- Research stays scoped — don't exhaustively survey, get enough to decide
- If requirements/architecture docs already exist and are sufficient, skip research
- After research, draft requirements that include domain table-stakes — not just what the user said

## Step 3: Code Change Plan

**Mandatory before any code is written.** Produced by Opus.

```markdown
## Code Change Plan: [feature/slab]

### New files
- `path/file.ext` — purpose, key functions/classes, ~line count estimate

### Modified files
- `path/file.ext` — what changes (specific: "add router" not "update file")

### Tests
- `path/test_file.ext` — N tests: [list what each tests]

### Dependencies
- New: [list] or None
- Modified: [list] or None

### Evidence
- [D-REQ-N] requirement text (copied, not summarized)
- [D-ARCH-N] architecture decision with evidence source
- [D-IMPL-N] pattern choice with rationale
```

## Step 4: Eval Plan

Quick evaluation of the plan before implementation:
- Does every file map to a requirement? (no orphan files)
- Does every requirement map to a file? (no missing implementation)
- Are dependencies declared? (no surprise installs during implementation)
- Is the plan small enough for one slab? (if not, split)

If plan scores < 95% → revise plan. Do not proceed to code.

## Step 5: Build (per slab)

Run `/implementation` for the current slab using the cheaper model (Sonnet/Haiku).
- Follow all existing implementation rules (TDD, slab discipline, mock-first)
- Session limits still apply
- The plan constrains what gets built — Sonnet executes, doesn't redesign

**Auto-fix:** If a test fails, attempt fix (max 2 attempts). Still failing → PAUSE.

## Step 6: Verify

Run `/verify` in auto mode:
- Session health check (Step 1) — still applies
- Output quality check (Step 3) — still applies
- Skip "user confirms" (Step 5) — eval gate replaces human judgment

**Auto-judge heuristics (since user isn't watching):**
- Does output match format described in requirements?
- Is it curated (top 3-5 items) or raw dump (20+ items)?
- Are there unexplained numbers without context?
- Does it answer the user's question or just return data?

If any heuristic fails → PAUSE with specific concern.

## Step 7: Gate (Precommit)

Run `/precommit` full mode. All steps mandatory:
- Step 1: Instruction compliance
- Step 2: Test quality audit
- Step 2b: Test suite execution (if runner exists)
- Step 3: Code standards + G-IMPL-6 (no easy way out)
- Step 5: Project rules compliance
- Step 5b: README validation+fix (readme-validator in fix mode)

**Auto-fix minor issues:** missing imports, naming violations, missing .env.example entries.
**PAUSE on:** unaddressed instructions, architectural decisions, ambiguous choices, test failures that aren't obvious.

## Step 8: Eval Gate

Run `/evaluate` quick mode on the current slab (Opus).

| Score | Action |
|-------|--------|
| ≥ 95% | Proceed to commit |
| 70-94% | Auto-fix mechanical issues (naming, missing tests, formatting). Re-eval ONCE. If still < 95% → PAUSE |
| < 70% | PAUSE immediately — something fundamental is wrong |

**Commit requires:** precommit passing AND eval ≥ 95%. Both gates, not either.

## Step 9: Auto-Commit

If all gates pass:
1. Stage specific changed files (never `git add -A`)
2. Commit with descriptive message following G12
3. Format: `[slab N/M] <what this slab does> (<test count> tests)`
4. Push only if user previously authorized pushing

## Step 10: Next Slab or Final

If more slabs remain → loop to Step 5 (build).
If all slabs complete → proceed to Final Quality.

## Step 11: Final Quality (Opus)

1. `/evaluate` full — all dimensions, all slabs, overall score
2. readme-validator in fix mode — validate+fix entire README line-by-line
3. Guardrail audit — scan all committed code for violations:
   - G-IMPL-6 (no shortcuts)
   - G-PUSH-1 (precommit ran)
   - G-PC-1-5 (test quality, instructions)
   - G-AUTO-1 (evidence citations)

If any violation → fix and re-commit. If unfixable → report to user.

## Step 12: Cleanup (Sonnet)

1. Consolidate key decisions from requirements/, architecture/, reports/ into README "Architecture Decisions" section
2. Archive artifacts: `archive/<date>/requirements/`, `archive/<date>/reports/`
3. Update project-state.md: mark all features as verified
4. Delete HANDOFF.md (work is complete)
5. README becomes source of truth — must contain: what, install, run, test, debug, env vars, decisions

## Token Tracking

Estimate context usage: ~4 characters per token.

| Checkpoint | Threshold | Action |
|------------|-----------|--------|
| After each phase | ~20K tokens (~80K chars) | Continue |
| Approaching limit | ~25K tokens (~100K chars) | Pre-compute next slab plan, prepare for handoff |
| At limit | ~32K tokens (~128K chars) | Generate HANDOFF.md, stop |

## Handoff Protocol

When token limit approached:

1. Commit all work done so far
2. Pre-compute code change plan for next slab (so new session can execute immediately)
3. Generate `HANDOFF.md` in project root (see project-state-template.md for format)
4. Update `project-state.md` with full status
5. Report: "Context limit approaching. Handoff file created. Start new session to continue."

## Pause Protocol

When auto mode pauses:

```
AUTO PAUSED at [slab N/M], [step name]

Reason: [specific issue — not generic]
What I need: [specific question or decision]
What's done: [slabs committed, tests passing]
What's committed: [commit hashes]
Evidence reviewed: [what was checked before pausing]

Reply to continue, or /status for full picture.
```

## What Auto Mode Never Does

- Guess at ambiguous requirements
- Loop more than twice on the same failure
- Commit code scoring below 95% eval
- Skip precommit or any quality gate
- Push without prior authorization
- Make architectural decisions without evidence
- Delete user code or existing tests
- Install packages not in the plan
- Make monetary, infrastructure, or security-sensitive decisions
