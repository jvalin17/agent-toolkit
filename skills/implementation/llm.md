# LLM Integration Implementation
Keywords: LLM, prompt, response handling, safety, provider, SDK, structured output

Implement prompt logic, response handling, and safety layers for LLM-powered features using TDD.

## Inputs

Read from upstream docs before writing any code. Follow upstream decisions exactly:
- **Provider + SDK** (from requirements/architecture): use the specified provider and integration approach. Do not suggest a different provider.
- **Prompt management** (from architecture doc): follow the decided approach.
- **Response handling** (from architecture doc): follow streaming vs batch, structured output, caching strategy.
- **Safety** (from architecture doc): implement the specified defenses.
- **Use cases** (from requirements doc): implement for the specific LLM use cases listed.

If upstream docs exist, follow them exactly. If they do not exist, ask the user.

## Checklist Per Block

- [ ] API key loaded from environment variable (never hardcoded — G-IMPL-2)
- [ ] Prompt templates stored per architecture decision (inline / files / platform)
- [ ] Response parsed and validated before use
- [ ] Errors surface helpful messages (not raw API errors)
- [ ] Rate limiting / token budgets enforced if specified
- [ ] Audit logging if specified in architecture

## LLM Data Security (G9)

When writing code that sends data to external LLMs, enforce file-type filters, sanitize inputs, and mark data exit points. See guardrail G9 in `shared/guardrails.md` for full requirements.

For guardrails and core principles, see the main `SKILL.md`.
