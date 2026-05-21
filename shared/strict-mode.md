# Strict Mode — Rules Reference

> Read by skills when `"mode": "strict"` is set in gates.json or `AGENT_TOOLKIT_MODE=strict`.
> Normal mode sessions never load this file.

## What Strict Mode Enforces

### 1. Ground Truth (G-IMPL-7)

Test fixtures must cite their data source. Valid: query output, user sample, spec/contract, factory/faker. Invalid: "I read the code", "the model suggests", inference from schema.

### 2. Mandatory DATA Step in Slab Cycle

Between SETUP and TDD, every slab must:
- Query the real system (SELECT, curl, API call) if one exists
- Paste the output as evidence
- Derive test fixtures FROM that output
- If no real system: state explicitly "fixtures are synthetic (factory)" or "user-provided sample"
- "I read the schema/model" is NOT sufficient

### 3. Drift Detection

The session monitor tracks:
- `exchanges_since_query` — exchanges since last real-system contact
- `patch_forward_count` — times test failed then source edited with no investigation
- `slabs_without_data` — consecutive slabs with zero data queries

Thresholds trigger warnings, slab blocks, or session restart.

### 4. /evaluate Required Before Commit

Normal mode: only /precommit required.
Strict mode: both /precommit AND /evaluate required before commit.

### 5. Periodic Integrity Checks

Every 15 exchanges, the session monitor injects a drift audit. This is not optional — it checks counters and computes a drift score. High drift triggers session restart.

## What Strict Mode Does NOT Change

- Skill workflows — same, just stricter enforcement
- Gate mechanism (legacy/signed) — same, just requires /evaluate too
- Auto-continuation — same, but drift can trigger restart
- Normal sessions — completely unaffected
