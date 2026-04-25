# LLM Integration Implementation

Implement prompt logic, response handling, and safety layers for LLM-powered features using TDD.

## Inputs

Read from upstream docs before writing any code. Follow upstream decisions exactly:
- **Provider + SDK** (from requirements/architecture): Use the specified provider (Anthropic, OpenAI, etc.) and integration approach (direct SDK, abstraction layer, agent framework). Do not suggest a different provider.
- **Prompt management** (from architecture doc): Follow the decided approach — inline, template files, or platform.
- **Response handling** (from architecture doc): Follow streaming vs batch, structured output approach, caching strategy.
- **Safety** (from architecture doc): Implement the specified defenses — input sanitization, output filtering, rate limiting, audit logging.
- **Use cases** (from requirements doc): Implement for the specific LLM use cases listed (chat, extraction, classification, etc.).

If upstream docs exist, follow them exactly. If they do not exist, ask the user what they need.

## Where LLM Integration Lives

LLM integration is stitched into feature slabs that use AI. The SDK setup and config happen in the skeleton or slab setup (no TDD). The prompt logic, response validation, and safety are business logic — use TDD.

## TDD Pattern: Prompt Behavior First, Then Integration

```
1. PROMPT TEST — Define expected behavior: given this input, the LLM response should [contain X / match schema Y / not contain Z]
2. IMPLEMENT PROMPT — Write the prompt/system message that produces the expected behavior
3. INTEGRATION TEST — SDK call works: auth, request, response parsing, error handling
4. SAFETY TEST — Prompt injection attempts are handled, PII is filtered, output is validated
5. END-TO-END TEST — Full flow: user input -> prompt assembly -> LLM call -> response processing -> output
```

## What to Test

- [ ] SDK client initializes correctly (API key from env, correct model specified)
- [ ] Prompts produce expected output shape (structured output validates against schema)
- [ ] Streaming works end-to-end (if specified in architecture)
- [ ] Error handling: API errors, rate limits, timeouts, malformed responses
- [ ] Safety: prompt injection inputs are sanitized or rejected
- [ ] Cost: token usage is within expected bounds for typical inputs
- [ ] Fallback: if a fallback provider is specified, it activates on primary failure

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
