# AI Agent Anti-Patterns

> Language-agnostic rules to prevent lazy code generation. These patterns are NOT caught by linters — they require judgment. Checked during /precommit (G-IMPL-6) and /evaluate.
>
> Sources: GitClear 211M-line study, IEEE Spectrum 2026, Snyk security research, Addy Osmani's 80% Problem analysis, Simon Willison's agentic engineering patterns.

---

## HARD BLOCKS (never ship these)

### 1. Kitchen-Sink Parameters

**Rule:** Never use `**kwargs`, `...args`, `any`, `object`, `interface{}`, or `map[string]interface{}` as function parameters unless implementing a decorator/middleware that must preserve an unknown signature.

**Why:** Hides the interface. No type safety, no autocompletion, no compile-time validation. Callers cannot know what is expected without reading the implementation.

**Instead:** Explicit named parameters with types. If polymorphism is needed, use generics with constraints or a typed options struct/interface.

**Exception:** Decorators, framework-required overrides (e.g., `__init_subclass__`), or when typed with `Unpack[TypedDict]` / equivalent.

---

### 2. Trivial Pass-Through Wrappers

**Rule:** Never create a function whose only job is calling another function with the same arguments.

**Why:** Adds indirection with zero value. Confuses readers about where logic lives. Increases maintenance surface.

**Instead:** Call the underlying function directly. Only wrap when adding behavior (logging, caching, validation, retry, transformation).

**Exception:** Facade patterns that simplify a complex subsystem interface (but must add simplification, not just rename).

---

### 3. Swallowed Errors

**Rule:** Never catch an error and do nothing with it. Never discard error returns (`_ = risky_operation()`).

**Why:** Silent failures corrupt data, lose transactions, and are impossible to debug in production.

**Instead:** Handle, propagate, log with context, or convert to a typed error. If genuinely safe to ignore, add a comment explaining why.

---

### 4. Hardcoded Returns / Magic Values

**Rule:** No bare numeric or string literals in logic. No functions that return a constant regardless of input.

**Why:** Cannot be configured, cannot be tested for correctness, hides assumptions.

**Instead:** Named constants with explanatory names. Functions must derive output from input.

---

### 5. Tests That Test the Mock

**Rule:** Never assert that a mock returns what you told it to return. Never write tests with no assertions or assertions that cannot fail (`is not None`, `toBeDefined()`).

**Why:** Zero bugs caught. False confidence in coverage metrics. The test suite becomes a rubber stamp.

**Instead:** Assert specific properties, values, and behaviors. Test boundaries: invalid input, missing data, empty collections, max values.

---

### 6. Shipped TODOs in Error Paths

**Rule:** Never ship `# TODO: handle error`, `// FIXME`, or incomplete error handling in any code path that can execute in production.

**Why:** "Works in happy path" is not shipped. The error path IS production — it's just the production you haven't seen yet.

**Instead:** Implement the handling now. If deferring, create a tracked issue and add the link.

---

### 7. Hardcoded Secrets

**Rule:** Never generate API keys, passwords, database URLs, or JWT secrets in source code — even as "examples."

**Why:** Gets committed, gets pushed, gets compromised. Once in git history, it's exposed forever.

**Instead:** Environment variables, secret managers, `.env` in `.gitignore`. Use obviously-fake placeholders: `YOUR_API_KEY_HERE`.

---

## SOFT BLOCKS (flag during review, fix before merge)

### 8. Defensive Over-Engineering

**Rule:** Do not validate types or add null-checks for internal function parameters that are already typed. Only validate at system boundaries.

**Why:** 10x code for inputs that cannot occur given the type signature. Masks upstream bugs that should fail fast.

**Instead:** Trust your types internally. Validate at API entry points, CLI args, file reads, and external service responses.

---

### 9. Boolean Flag Arguments

**Rule:** Do not add boolean parameters that split a function into two behaviors.

**Why:** Call sites are unreadable (`process(data, true, false, true)`). Each boolean doubles the function's behavior space.

**Instead:** Separate functions, enums, or named-parameter patterns.

---

### 10. Copy-Paste with Minor Variations

**Rule:** If you write the same logic 3+ times with only a value/string difference, parameterize it.

**Why:** Duplicated bugs, inconsistent fixes, maintenance burden. AI-era repos show copy-paste rose from 8% to 12% while refactoring dropped from 25% to <10%.

**Instead:** Parameterize the difference. Use table-driven patterns, parameterized tests, or a single function with the variant as an argument.

---

### 11. Premature/Speculative Abstraction

**Rule:** Do not create Strategy/Factory/Builder/Observer patterns for fewer than 3 concrete implementations. Do not add configuration for hypothetical future requirements.

**Why:** AI is trained on enterprise code and applies heavyweight patterns indiscriminately. Creates "comprehension debt" — code generated faster than you can understand it.

**Instead:** Start concrete. Abstract after the third case. The simplest implementation that works IS the correct architecture.

---

### 12. Options-Bag With All Optional Fields

**Rule:** Do not pass a config/options object where every field is optional and the function silently uses defaults for missing ones.

**Why:** Compiler cannot enforce completeness. Callers can pass empty objects. Runtime errors from missing required data.

**Instead:** Required parameters as explicit args. Only truly optional config in an options object. Use builders with compile-time completeness.

---

### 13. God Functions / Mixed Concerns

**Rule:** A single function must not fetch + transform + validate + format + produce side effects.

**Why:** Untestable in isolation, impossible to reuse parts, violates SRP. Changes to presentation break data access.

**Instead:** Separate layers. Each function does one thing and is independently testable.

---

### 14. Vacuous Variable Names

**Rule:** No `data`, `result`, `temp`, `obj`, `items`, `response` as variable names unless the scope is <3 lines.

**Why:** Forces readers to trace the full data flow to understand what a variable holds.

**Instead:** `user_profiles`, `validated_orders`, `raw_api_response`, `pending_invoices`.

---

### 15. Apologetic / Hedging Comments

**Rule:** Never ship comments like "This might not be the best approach" or "I'm not sure if this handles all edge cases."

**Why:** Signals uncertainty shipped as code. The correct response to uncertainty is fixing the code, not annotating the doubt.

**Instead:** Either fix the concern or add a specific technical note: `# Linear scan acceptable for <100 items. Revisit at scale.`

---

### 16. Ignoring Existing Codebase Patterns

**Rule:** Before generating new code, search for existing implementations of the same pattern in the codebase. Match conventions: naming, error handling, validation approach, module structure.

**Why:** Each prompt is fresh context. Without this rule, the codebase accumulates 3 validation libraries, 2 naming conventions, and inconsistent error handling.

**Instead:** Search first. Match what exists. If the existing pattern is wrong, fix it everywhere — don't add a third variant.

---

### 17. Unnecessary Dependencies

**Rule:** Do not add a library for functionality available in the standard library or already present in existing dependencies.

**Why:** Supply chain risk, bundle size, maintenance burden. AI defaults to the most common Stack Overflow answer (which involves `npm install`).

**Instead:** Use native APIs first (`crypto.randomUUID()` not `uuid`, `Array.padStart()` not `left-pad`). Only add deps that provide substantial value.

---

### 18. No Observability

**Rule:** Any function that calls an external service, processes payments, or modifies persistent state must have structured logging with context.

**Why:** Every AI-generated project in production studies had zero error monitoring. When things fail, you have no visibility.

**Instead:** Structured logging with correlation IDs at integration points. Error monitoring. Health checks.

---

### 19. Type Assertions Without Validation

**Rule:** Never cast external input to an internal type without runtime validation (`as Type`, forced unwrap, unchecked downcast).

**Why:** Types are erased at runtime in many languages. External input can be anything. Unvalidated casts lead to corruption and injection.

**Instead:** Validate structure and types at system boundaries. Parse, don't type-assert.

---

### 20. Generating Without Searching

**Rule:** Before creating a new utility, helper, or pattern — search the codebase for existing implementations.

**Why:** AI agents generate confidently without checking what exists. Results in duplicate implementations with different behavior.

**Instead:** `grep`/search first. Reuse or extend what exists. Only create new when nothing fits.

---

## How to Enforce

| Layer | What it catches | Tool |
|-------|----------------|------|
| Linter | Magic numbers, bare except, unused imports, type issues | ruff, eslint, clippy, golangci-lint |
| Type checker | Untyped kwargs, any-types, missing validation | mypy --strict, tsc --strict |
| Custom rules | kwargs in definitions, trivial wrappers | semgrep, ast-grep |
| Instructions | Judgment calls: premature abstraction, mixed concerns, defensive over-engineering | CLAUDE.md / this file |
| Precommit | All of the above | /precommit G-IMPL-6 |

The linter catches what it can. This file covers everything else.
