# Architecture & design docs

Public design documentation for Agent Toolkit — how skills, hooks, gates, and reports fit together. Start with [system overview](system-overview.md), then drill into the topic you care about.

## Start here

| Doc | Audience | What it covers |
|-----|----------|----------------|
| [**System overview**](system-overview.md) | Anyone new to the toolkit | End-to-end flow: skills → hooks → gates → reports |
| [**Daily workflow**](workflow.md) | Day-to-day users | Commit, push, finalize, gate profiles |
| [**Install & updates**](install-and-updates.md) | Claude Code users | First setup, auto-sync, manual refresh |
| [**Other LLMs**](other-llms.md) | Cursor, GPT, Gemini, etc. | Project rules without hooks |
| [**Skills reference**](skills.md) | All users | All 13 skills and gated skills |
| [**Configuration**](configuration.md) | Project admins | `gates.json`, presets, signed mode |
| [**Gate unlock**](../shared/gate-unlock.md) | Teams adopting gates | Legacy vs signed, rare options |

## Requirements (why we built it)

Product intent and acceptance criteria — written before implementation.

| Doc | Topic |
|-----|-------|
| [Auto-continuation](../requirements/auto-continuation.md) | Context-pressure handoffs instead of fixed time/exchange limits |
| [Session quality hooks](../requirements/session-quality-hooks.md) | Time limits, TDD discipline, real-data validation |
| [Strict mode](../requirements/strict-mode.md) | Anti-fake mode — fixture provenance, drift detection |
| [Ground truth guardrail](../requirements/ground-truth-guardrail.md) | G-IMPL-7 — test fixtures must cite real data sources |

## Reference

| Doc | Topic |
|-----|-------|
| [Guardrails](../shared/guardrails.md) | All 21 guardrail groups (G-*) |
| [Orchestrator](../shared/orchestrator.md) | `/skill auto` chaining |
| [Report format](../shared/report-format.md) | Canonical report schema |
| [Troubleshooting](../shared/troubleshooting.md) | Common gate/hook failures |

## Architecture (how it works)

| Doc | Topic |
|-----|-------|
| [Auto-continuation](../architecture/auto-continuation.md) | `auto_continue.py`, session hooks, HANDOFF loop |
| [Strict mode](../shared/strict-mode.md) | Runtime drift scoring, integrity checks |

## Key design principles

1. **Structural over prompt** — On Claude Code, hooks run as subprocesses the agent cannot disable. Other tools get the same rules via `AGENTS.md`, but enforcement is prompt-based.
2. **Hook-owned artifacts** — With default `gate_protect` and `report_protect`, only `finalize_report.py` writes `.gates/` and `reports/`. Skills produce findings; hooks produce proof.
3. **Same bar in auto mode** — Auto-chaining removes wait time between steps, not quality gates.
4. **Escalation, not holes** — Rare options like `enforcement: warn` exist for migration; first violation auto-escalates to block.
5. **Signed mode is additive** — Legacy finalize flow stays; JWT attestation adds cryptographic binding for teams and CI.

## Repo map (design-relevant paths)

```
skills/          Workflow definitions (13 skills)
hooks/           Structural enforcement (gate_hook, finalize_report, session_monitor, …)
gate/            JWT attest/verify (copied to .agent-toolkit/gate/ on install)
shared/          Guardrails, gate-unlock, orchestrator, report-format
requirements/    Product requirements (intent before code)
architecture/    Implementation architecture notes
docs/            This index + system overview
templates/       gates.json defaults, signed example, GitHub workflow
```

## License

Apache License 2.0 — see [LICENSE](../LICENSE).
