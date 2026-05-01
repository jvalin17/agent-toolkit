# Pipeline Implementation
Keywords: CI/CD, build, deploy, test infrastructure, environment setup

Implement CI/CD pipelines, build scripts, deployment automation, test infrastructure, and environment setup.

## When Pipeline Runs

Pipeline is typically its own slab, not stitched into feature slabs. It runs after enough feature slabs exist to have meaningful tests to automate.

## Inputs

Read from upstream docs:
- **Requirements doc:** CI/CD expectations, deployment targets, environment requirements
- **Architecture doc:** deployment architecture, infrastructure decisions, environment strategy
- **Testing architecture:** test pyramid, what must pass before merge, regression policy

## TDD Pattern: Smoke Tests First, Then Stage Verification

```
1. SMOKE TEST — Define: "what must work for the pipeline to be healthy?"
2. IMPLEMENT STAGE — Build one CI/CD stage
3. VERIFY STAGE — Run smoke test for that stage
4. NEXT STAGE — Move to next stage
```

Build stages incrementally. Each stage should be verified before moving to the next.

For guardrails and core principles, see the main `SKILL.md`.
