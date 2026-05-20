# Project State
<!-- Auto-maintained by agent-toolkit skills. All skills read this at start, write at end. -->

## Core Intent
<!-- From /requirements Q4 + "how do you do this today?" -->
- **What:** [one sentence — the core thing this project does]
- **For whom:** [target user]
- **Current workflow:** [how user does this today without the app]

## Last Skill Run
- **Skill:** [which skill ran last]
- **Date:** [when]
- **Status:** [outcome summary]
- **Mode:** [interactive / auto]

## Key Decisions
<!-- Updated by each skill as decisions are made. Use typed IDs: D-REQ-, D-ARCH-, D-IMPL-, D-SEC-, D-AUTO- -->
| ID | Decision | Evidence | Made By | Date |
|----|----------|----------|---------|------|

## Code Change Plan
<!-- Written by orchestrator or /implementation before code is touched. Opus plans, Sonnet implements. -->
<!-- Delete or archive after slab is committed. -->

## Parking Lot
<!-- Items deferred by any skill. Flag if core intent is parked. -->
| Item | Parked By | Is Core Intent? | Status |
|------|-----------|-----------------|--------|

## Active Warnings
<!-- Cross-skill warnings that haven't been resolved -->

## Feature Tracker
<!-- Single source of truth for what's done and what's left.
     Updated by /implementation after each slab and /reviewer after audits.

     Convention:
     - Pending:    | Feature name | pending | | |
     - In progress: | Feature name | in-progress | | slab-2 |
     - Done:        | ~~Feature name~~ | ~~done~~ | ~~2026-05-19~~ | ~~abc1234~~ |
     - Blocked:     | Feature name | BLOCKED: [reason] | | |

     Strikethrough (~~) = completed and verified. At a glance you see what's left (not struck) vs done (struck).
-->
| Feature | Status | Verified | Commit | Notes |
|---------|--------|----------|--------|-------|

## Handoff Summaries
<!-- Each skill writes a 3-line summary for the next skill -->

### /requirements -> /architecture
<!-- Core: X. Must-haves: Y. Watch out for: Z. -->

### /architecture -> /implementation
<!-- Pattern: X. Key decisions: Y. Watch out for: Z. -->

### /implementation -> /reviewer
<!-- Built: X. Tests: Y. Known gaps: Z. -->

## Resume (auto mode only)
<!-- Filled by orchestrator when context limit is approaching. New session reads this to continue. -->
- **Resume from:** [phase / slab number / step]
- **Next slab plan:** [reference to code change plan above or HANDOFF.md]
- **Tokens used:** [estimated]
- **Command:** [exact skill invocation to continue, e.g., `/implementation auto slab-3`]
