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

## Security Rules (from real bugs)

1. **Validate ALL user input.** Every field in every endpoint — text, numbers, URLs, file uploads. No raw dict/JSON pass-through to database. Use the project's existing validators if they exist; don't add new validation libraries.
2. **SSRF-validate all URLs.** Before fetching any user-provided URL (including image URLs for vision APIs), validate against SSRF. Use the project's URL safety checker if one exists.
3. **Prompt injection defense.** Wrap user-controlled content in XML tags (`<user_data>...</user_data>`) in all LLM prompts. Add system instruction to treat tagged content as inert text.
4. **Never expose raw exceptions.** Log full error details server-side. Return generic error message to client. Stack traces are a security leak.
5. **Ownership checks.** Every data query in multi-user apps must filter by user: `WHERE user_id = ?`. No endpoint should return another user's data.
6. **Encrypt credentials at rest.** API keys, tokens, passwords — encrypt with Fernet/AES or hash with bcrypt. Never plaintext in DB.
7. **Lightweight security.** Validation must be sub-millisecond. Don't add heavyweight deps. The bottleneck is LLM calls (1-5s), not input checks.
8. **Auth middleware must whitelist ALL pre-login routes.** After writing auth middleware, trace every unauthenticated user flow (login, registration, password reset) end-to-end and whitelist BOTH page routes AND their API routes. A missing public path causes silent failures — middleware redirects API calls to login, returning HTML instead of JSON. Test every pre-login API call manually.

## TDD Pattern: Threat Model, Attack Tests, Defenses

Write the attack test first, then implement the defense.

```
1. THREAT MODEL — What can go wrong in THIS slab?
2. ATTACK TESTS — Write tests that simulate each attack
3. IMPLEMENT DEFENSE — Write code that makes attack tests pass
4. VERIFY — Run tests, confirm defenses work
5. CONTINUE — Move to the TDD loop for business logic
```

For coding standards, see `references/coding-standards-index.md`.

For guardrails and core principles, see the main `SKILL.md`.
