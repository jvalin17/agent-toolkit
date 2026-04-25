# Report Format — Shared Across All Skills

> All skills must generate a report. This file defines the format and rules.

## Rules

1. **Create report at the START of the skill run**, not just the end. Update it progressively.
2. **Report lives in the project repo**, not agent-toolkit: `reports/<skill-name>/`
3. **UUID suffix** on every report file to avoid collisions: `<prefix>_<topic>_<8-char-uuid>.md`
4. **Check for existing reports** before starting. If a previous report exists for the same topic, link to it in "Previous Reports" section.
5. **Status must always be accurate**: `in-progress` while working, `completed` when done, `incomplete` if stopped early (with reason).
6. **If the skill stops for ANY reason** (user cancels, error, scope too large, ran out of context), the report must reflect where it stopped and what remains.

## File Naming

```
reports/
├── requirements/
│   └── req_<topic>_<uuid8>.md
├── architecture/
│   └── arch_<topic>_<uuid8>.md
└── implementation/
    └── impl_<topic>_<uuid8>.md
```

UUID: Generate 8 hex characters. E.g., `req_job-agent_a1b2c3d4.md`

## Report Header (all skills)

```markdown
# [Skill Name] Report: [Topic]

| Field | Value |
|-------|-------|
| **Report ID** | <uuid8> |
| **Skill** | requirements / architecture / implementation |
| **Topic** | <what was worked on> |
| **Status** | in-progress / completed / incomplete |
| **Started** | <timestamp> |
| **Completed** | <timestamp or "—"> |
| **Duration** | <how long> |
| **Previous Reports** | <links to prior reports on same topic, or "none"> |
| **Output File** | <path to generated artifact, e.g., requirements/job-agent.md> |
```

## Progress Section (updated as skill works)

```markdown
## Progress

### Completed Steps
- [x] Step 1: <what was done>
- [x] Step 2: <what was done>

### Current Step
- [ ] Step 3: <what is in progress>

### Remaining Steps
- [ ] Step 4: <what's left>
- [ ] Step 5: <what's left>
```

## Skill-Specific Sections

Each skill adds its own sections after the header and progress:

### /requirements report adds:
- Mode detected (quick / standard / system-design)
- User level (1 / 2 / 3)
- Questions asked and key answers
- Assumptions made (with reasoning)
- Items parked (out of scope)

### /architecture report adds:
- Decisions made (with chosen option and rationale)
- Decisions pending (not yet reached)
- Trade-offs accepted
- Principles check summary

### /implementation report adds:
- Mode (backend / frontend / security / ML / pipeline)
- Test approach (TDD / implement-then-test / no tests / write-tests-only)
- Files created / modified
- Tests written (count by type)
- Tests passing / failing
- Coverage summary
- Warnings / issues found

## Incomplete Report

If the skill doesn't finish, update status to `incomplete` and add:

```markdown
## Incomplete — Reason

**Stopped at:** Step [N] — [description of where it stopped]
**Reason:** [user cancelled / error / scope too large / context limit / other]
**What was completed:** [summary of done work]
**What remains:** [summary of remaining work]
**How to resume:** Run `/[skill] [topic]` again. The skill will find this report and offer to continue.
```
