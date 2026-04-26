# Code Quality Review
Keywords: quality, structure, SOLID, DRY, naming, patterns, architecture, conventions

For guardrails and principles, see main SKILL.md.

## Step 1: Architecture Compliance

Read upstream docs (`requirements/$TOPIC.md`, `architecture/$TOPIC.md`) if they exist. Check:

- Does the code follow architecture decisions (patterns, layers, data flow)?
- Are files in the right places per project structure?
- Does naming match project conventions (files, classes, functions, variables)?
- Are there files that belong in a different module/layer?

Report deviations with file:line references and the upstream decision they violate.

## Step 2: Structure and Design

For each file in the target, check:

### SOLID Principles
- **Single Responsibility:** Does each class/module do one thing? Flag files over 300 lines or classes with 10+ methods.
- **Open/Closed:** Can behavior be extended without modifying existing code? Flag switch/if chains that grow with new features.
- **Liskov Substitution:** Do subclasses honor the base contract? Flag overrides that change semantics.
- **Interface Segregation:** Are interfaces focused? Flag interfaces with methods most implementors don't use.
- **Dependency Inversion:** Do high-level modules depend on abstractions? Flag direct imports of concrete implementations in business logic.

### DRY / KISS / YAGNI
- **DRY:** Search for duplicated logic (not just duplicated text). Flag copy-paste code with minor variations.
- **KISS:** Flag over-engineered solutions. A 200-line abstraction for something used once is a finding.
- **YAGNI:** Flag unused code, dead branches, features half-built with no tests or consumers.

## Step 3: Naming and Readability

- Function names describe what they do (verb + noun): `calculateTotal`, not `process`.
- Variable names are specific: `userEmail`, not `data` or `val`.
- Boolean names read as questions: `isActive`, `hasPermission`, not `flag` or `status`.
- No magic numbers — named constants with units: `MAX_RETRY_COUNT = 3`, not bare `3`.
- Comments explain WHY, not WHAT. Flag comments that restate the code.
- No commented-out code blocks. Flag them for removal.

## Step 4: Security Review (OWASP)

Check for common vulnerabilities:

| Category | What to find | Severity |
|----------|-------------|----------|
| Injection | SQL string concat, unsanitized shell commands, eval() | Critical |
| Auth | Hardcoded secrets, weak password rules, missing rate limits | Critical |
| XSS | Unescaped user input in HTML/templates | High |
| CSRF | Missing CSRF tokens on state-changing endpoints | High |
| Exposure | Stack traces in responses, verbose error messages, PII in logs | Medium |
| Config | Debug mode in production config, permissive CORS, missing security headers | Medium |
| Dependencies | Known CVEs in dependencies (check with `npm audit` / `pip audit` / equivalent) | Varies |

Run the project's security audit tool if available. Report output.

## Step 5: Import and Dependency Validity

- Every import resolves to an existing file or installed package.
- No circular imports (A imports B imports A).
- No unused imports.
- No wildcard imports (`from x import *`, `import * from`).
- Dependencies used in code exist in the package manager file.
- No dev dependencies imported in production code.

## Step 6: Test Impact

Without running tests, assess:

- Would these code patterns break existing tests? (e.g., changed function signatures, renamed exports)
- Are there untested public methods? (cross-reference with test files)
- Are there complex branches with no test coverage? (nested conditionals, error handlers)

Flag high-risk untested code for the Tests review area.

## Output Format

Present findings grouped by category:

> **Code Quality Review for [target]**
>
> | # | Category | Severity | File:Line | Finding | Fix |
> |---|----------|----------|-----------|---------|-----|
> | 1 | Security | Critical | db.py:23 | SQL concat with user input | Use parameterized query |
> | 2 | SOLID | Medium | service.py:1-280 | 280-line file, 3 responsibilities | Split into UserService, AuthService, NotificationService |
> | 3 | Naming | Low | utils.py:45 | Function `do_thing()` | Rename to `send_welcome_email()` |
>
> **Summary:** [1-2 sentences — overall code health, biggest risks]
