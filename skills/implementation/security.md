# Security Implementation
Keywords: auth, authorization, validation, XSS, CSRF, secrets, encryption, security

Security is stitched into feature slabs, not a standalone phase. Activates as step 2 of the per-slab cycle (before business logic) whenever a slab touches auth, user data, or external APIs.

## When Security Mode Activates Within a Slab

| Slab Type | Security Focus |
|-----------|---------------|
| Auth slab | Full auth security: password hashing, token handling, session management |
| Any API slab | Input validation, rate limiting, CORS |
| LLM slab | Prompt injection defense, PII filtering, output validation (cross-reference G9) |
| Payment slab | PCI compliance, transaction validation |
| File upload slab | File type validation, size limits, malware scanning |
| Data export slab | Authorization checks, PII redaction |

## Inputs

Read from upstream docs:
- **Requirements doc:** auth requirements, data sensitivity, compliance needs
- **Architecture doc:** auth architecture, security layers, API design, secrets management approach
- **Guardrails:** G-IMPL-1 (parameterized queries), G-IMPL-2 (no hardcoded secrets), G9 (LLM data security)

## TDD Pattern: Threat Model, Attack Tests, Defenses

Write the attack test first, then implement the defense. The test simulates the attack. The code blocks it.

```
1. THREAT MODEL — What can go wrong in THIS slab?
2. ATTACK TESTS — Write tests that simulate each attack
3. IMPLEMENT DEFENSE — Write code that makes attack tests pass
4. VERIFY — Run tests, confirm defenses work
5. CONTINUE — Move to the TDD loop for business logic
```

For guardrails and core principles, see the main `SKILL.md`.
