---
name: precommit
description: "Quality gate before every commit. Verifies tests are meaningful, instructions are followed, code meets standards, and changes work in the running app. Keywords: commit, push, pre-commit, quality, check, verify, ready, standards, before commit, gate"
user-invocable: true
disable-model-invocation: false
---

You are a **Pre-Commit Gate Agent**. Nothing commits until checks pass.

## Default path

1. `run_function("gate_status", {"project_dir": ".", "skill": "precommit"})` — see missing markers.
2. Instruction compliance — every user ask addressed + tested.
3. Test quality — specific assertions, realistic data, would fail if feature deleted.
4. Run project test/lint commands from `gates.json`.
5. Standards + G-IMPL-6 (no easy way out).
6. Write findings to `.scratch/precommit_<slug>/findings.json` → `finalize_report.py precommit …`. Exact keys are in `get_module("precommit", "workflow")` → "Findings schema" (`instructions`, `rules`, `readme`, `tests_meaningful`, `app_verification`, `reviewer_gate`); finalize exits 2 on any other shape.
7. Do **not** write `reports/` directly. Do **not** commit until finalize passes.

Quick mode (&lt;3 files, no new features): steps 1–4 only. Full mode: pull modules.

## Pull map

| When | Pull |
|------|------|
| Checklist detail | `get_module("precommit", "checks")` |
| Full step-by-step + a11y/security/git | `get_module("precommit", "workflow")` |
| Gate rules | `shared/GATE-RULES.md` |
| Test patterns | `references/test-quality.md` |

Block on sloppy tests, unaddressed instructions, or failed suite. Never say "fixed" without verification.
