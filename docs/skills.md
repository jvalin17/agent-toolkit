# Skills reference

13 workflow skills. Invoke with `/skill-name` in Claude Code, or describe the same intent in natural language.

Append **`auto`** to chain skills without stopping: `/requirements auto my-app`. Protocol: [orchestrator.md](../shared/orchestrator.md).

| Skill | Purpose |
|-------|---------|
| `/explore` | Understand a codebase — recon, architecture, conventions, issues |
| `/requirements` | Gather and validate requirements |
| `/architecture` | Design with trade-offs and user journey |
| `/implementation` | TDD — skeleton → slabs; fix, refactor, demo modes |
| `/debug` | Hypothesis-driven debugging with reproduction tests |
| `/assess` | Architecture fitness audit |
| `/verify` | Output quality check — is it useful, not just correct? |
| `/precommit` | Pre-commit quality gate (required before commit by default) |
| `/reviewer` | Deep audit — code, tests, a11y, deps, UI |
| `/evaluate` | 5-dimension quality score (not lenient) |
| `/setup` | Install scripts, Docker, Makefile, README |
| `/status` | Project dashboard — done, next, blockers |
| `/updater` | Toolkit health — links, freshness, standards |

## Gated skills

These unlock git operations when combined with `finalize_report.py`:

| Skill | Gate flag | Pass condition |
|-------|-----------|----------------|
| `/precommit` | `.gates/precommit-passed` | Mechanical checks + findings |
| `/evaluate` | `.gates/evaluate-passed` | Score ≥ `eval_threshold` (default 95) |
| `/reviewer` | `.gates/reviewer-passed` | `findings.high == 0` |
| `/assess` | `.gates/assess-passed` | `findings.fix_now == 0` |

Skill definitions live in `skills/*/SKILL.md`.

## Skill tool errors

If `/debug` (or another skill) errors with `disable-model-invocation`:

```
Read skills/debug/SKILL.md and follow it
```

Or use natural language: "debug the failing test in …"
