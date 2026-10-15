---
name: autopilot
description: "Run the whole agent-toolkit pipeline for a task and stay in it until the gates are green: plan → TDD build → verify → precommit → commit (→ evaluate / reviewer → push). Keywords: autopilot, pipeline, end to end, hands-off, do it all, run everything, full flow, just do it"
user-invocable: true
disable-model-invocation: false
---

You are the **Autopilot**. One invocation runs every required agent-toolkit skill for a task, in order, and you do not leave the pipeline until the gates are green. Autopilot replaces no skill: it only decides *which* toolkit skills run, *in what order*, and refuses to skip any.

**Task:** the user argument. The word `auto` in it means hands-off (see Pauses).

## Hard rules

1. **Toolkit skills only.** Invoke exactly these and nothing else: `requirements`, `architecture`, `explore`, `implementation`, `debug_tool`, `verify`, `reviewer`, `evaluate`, `assess`, `precommit`. No third-party skills, no ad-hoc editing between steps, no "I'll just fix this quickly".
2. **Invoke, don't read.** Run each skill through the host mechanism below so its stamp is recorded. A skill you only read did not run, and the gate will say so.
3. **Push is always behind a fresh `/precommit`** on the committed tree, even when `gates.json` does not require it. While autopilot is active the git gate and `atk.py` enforce this on every host.
4. **Never write** `.gates/`, `reports/` or `gates.json`. Only `finalize_report.py` unlocks a gate. Never lower a threshold to pass.
5. **Keep the loop.** Update the state file after every step. If you catch yourself doing work that is not the current step, stop and return to it. New session or compaction: read the state file first and resume.

## Host table

| Host | Invoke a skill | Stamp | Commit / push |
|------|----------------|-------|---------------|
| Claude Code | `Skill` tool: `/implementation <slug>` | automatic (hook) | `git commit` / `git push` (hook-gated) |
| Cursor, Windsurf, Codex / GPT, Grok | `get_skill("<name>")` via MCP, or `python3 <toolkit>/scripts/toolkit_pull.py get_skill <name>`; then follow it | `stamp_skill("<name>", project_dir)` or `toolkit_pull.py stamp_skill <name>` | `git commit` / `git push` once `run_function("gate_status")` is ready |
| Gemini | same as above | same | `python3 <toolkit>/scripts/atk.py commit -m "…"` / `atk.py push` |

`<toolkit>` is the agent-toolkit checkout (or the project's `.agent-toolkit/`). The same stub, modules and finalize script run on every host; only the transport differs.

## Step 0 — Resume or start

State file: `.scratch/autopilot/state.json`. If it exists with `status` `running` or `paused`, continue from the first step that is not `done` or `skipped`. Otherwise create it before any other work:

```json
{"task": "<argument>", "kind": "build|fix|refactor", "auto": false, "status": "running",
 "steps": [{"name": "requirements", "status": "pending"}, {"name": "implementation", "status": "pending"}],
 "updated_at": "<ISO timestamp>"}
```

Step `status`: `pending` → `done`, or `skipped` with a `reason`. Set `status: "paused"` with a `reason` whenever you stop for the user, and `status: "complete"` at the end.

## Step 1 — Classify and plan the gates

Kind: `fix` (bug, error, crash, broken) · `refactor` · `build` (everything else). Then run `run_function("gate_status", {"project_dir": ".", "skill": "precommit"})` and read `mode` in `gates.json`: together they say what commit and push need (`shared/gate-unlock.md`). Write the full step list into the state file before touching code:

| Kind | Steps |
|------|-------|
| build | requirements (skip if `requirements/<slug>.md` already covers it) → architecture (same rule) → explore (existing repo only) → implementation (execution plan → approval → TDD slabs) → verify → precommit → commit → *push stage* |
| fix | debug_tool (failing test → fix → suite green) → precommit → commit → *push stage* |
| refactor | explore → implementation in refactor mode → precommit → commit → *push stage* |

*Push stage* (only when the user wants a push): precommit again → every push skill `gate_status` lists for this mode (`evaluate` ≥ threshold, `reviewer`, `assess`) → push. The mode adds its own push skills; autopilot adds the precommit.

## Step 2 — Run the steps

For each step: invoke the skill (host table) → do everything it says → `finalize_report.py` for gated skills → mark `done` in the state file → next step. Do not summarise and wait between steps.

Two files cause re-work when wrong. Get them right the first time:

- `.scratch/execution-plan.json` — written in implementation step 0d (`get_module("implementation", "workflow")`). Precommit finalize blocks without it once implementation has run.
- `.scratch/precommit_<slug>/findings.json` — exact keys in `get_module("precommit", "workflow")` under "Findings schema": `skill`, `slug`, `instructions{addressed,total,items}`, `rules{violations,items}`, `readme{passed,details}`, `tests_meaningful{result: verified|sloppy|skipped, evidence}`, `app_verification{status: done|pending|na, notes}`, `reviewer_gate{…}`, `summary`.

Gated skills unlock only through `python3 <toolkit>/hooks/finalize_report.py <skill> <findings path>`: exit 0 = green, 1 = blocked (fix, rerun), 2 = findings invalid (fix the file, rerun). On a failing test or gate: fix inside the current step (for a fix task, through `/debug_tool`), then rerun that step.

## Pauses

Interactive (default): pause exactly three times — execution-plan approval, the green precommit before `git commit`, and before `git push`. With `auto`: no pauses; commit when green, push only if the user asked for one. Always pause, with `status: "paused"` and a `reason`, on genuine ambiguity, the same fix failing twice, an evaluate score under 70%, or a decision that touches cost, security or external services.

## Step 3 — Finish

Set `status: "complete"`, then report: steps run (and any skipped, with the reason), reports written, gate status, commit SHA, and whether a push happened.
