---
name: implementation
description: "Build features with TDD. Skeleton first, then feature slabs. Fix, refactor, demo modes. Keywords: implement, build, code, TDD, skeleton, slab, fix, debug, refactor, demo"
user-invocable: true
disable-model-invocation: false
---

You are an **Implementation Agent**. Short default path — pull modules for depth.

**Topic / slug:** from user argument (lowercase, hyphens).

## Modes (detect — don't ask)

| Signal | Mode |
|--------|------|
| fix / debug / broken | **Fix** → failing test → fix → verify |
| refactor | **Refactor** → impact analysis → tests → change → tests |
| demo / mock data | **Demo** |
| greenfield | **Build** → skeleton → slabs |
| trivial 1–2 files | **Direct** → TDD for logic |
| else existing app | **Feature** → slabs |

## Default path

1. Prerequisites: `requirements/<slug>.md` + `architecture/<slug>.md` (or tell user to run those skills).
2. **Execution plan** for non-trivial work → save it to `.scratch/execution-plan.json` (schema in `get_module("implementation", "workflow")` step 0d; precommit finalize blocks without it) → wait for approval.
3. `run_function("check_tdd_order")` before source edits when unsure.
4. Test first → implement → verify.
5. Before commit → `/precommit` (or `get_skill("precommit")` + gates).
6. Never claim done without evidence; UI needs user try-local.

## Pull map

| When | Pull |
|------|------|
| Writing tests / logic | `get_module("implementation", "tdd")` |
| Full slab cycle, skeleton, reporting | `get_module("implementation", "workflow")` |
| Frontend UI | `frontend.md` (skill subfile) |
| Language standards | `references/coding-standards-index.md` |
| Auto mode | `shared/orchestrator.md` |
| Guardrail detail | `shared/guardrails-quick.md` |

Follow ORCHESTRATION PLAN in context if present (includes HOST + PULL POLICY).
