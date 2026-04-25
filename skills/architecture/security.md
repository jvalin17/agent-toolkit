# Security Architecture

Decisions for the security layer of the system. Always relevant — every system has security concerns, even internal tools.

## Inputs

Read `requirements/<name>.md` and extract:
- **Security requirements** — authentication needs, authorization model, compliance constraints
- **Data sensitivity** — PII, financial data, health data, classified information
- **Regulatory requirements** — GDPR, HIPAA, SOC 2, PCI-DSS
- **User types** — internal vs external, trusted vs untrusted, admin vs regular
- **Integration requirements** — third-party services, SSO, API consumers

Also read the Quick Architecture from `architecture/<name>.md` for the chosen architecture pattern and tech stack.

**Must reference OWASP Top 10 (G-ARCH-2) throughout these decisions.**

## Decision Order

Decisions are presented in waterfall order. Each choice constrains the next.

---

### Decision 1: Authentication Strategy

**Context:** How users prove their identity. The foundational security decision.

**OWASP relevance:** A07:2021 — Identification and Authentication Failures.

**Options:**

| | Option A: Session-Based (Cookies) | Option B: JWT (Stateless Tokens) | Option C: OAuth2 / OIDC (Delegated Auth) | Option D: API Keys |
|---|---------|---------|---------|---------|
| What | Server stores session, client holds session ID in cookie | Self-contained signed tokens sent per request | Delegate auth to identity provider (Google, Auth0, Keycloak) | Static key per client, sent in header |
| Best for | Traditional web apps, server-rendered pages | SPAs, mobile apps, microservices | Apps needing social login, SSO, enterprise identity | Machine-to-machine, third-party API access |
| Trade-off | Requires session store, CSRF vulnerability (OWASP A01) | Token revocation is hard, token size, XSS risk (OWASP A07) | Complexity of OAuth2 flows, provider dependency | No user identity, harder to rotate, leak risk (OWASP A07) |
| Cost | Free (server-side session store) | Free (stateless) | Free (open source providers) to paid (Auth0: $23+/mo) | Free |
| SOLID/DRY check | ✅ Simple, well-understood | ✅ Stateless, scalable | ✅ Delegates responsibility (SRP) | ⚠️ Limited — no user context |

**Security considerations:**
- Session: CSRF protection required (SameSite cookies, CSRF tokens)
- JWT: Short expiry (15 min) + refresh tokens. Store in httpOnly cookie, NOT localStorage
- OAuth2: Validate tokens server-side, use PKCE for public clients
- API Key: Rate limit aggressively, rotate regularly, never embed in frontend code

**Consequence:** Shapes authorization model, session management, and multi-device support.

---

### Decision 2: Authorization Model

**Context:** Who can do what after authentication. Depends on authentication strategy (Decision 1).

**OWASP relevance:** A01:2021 — Broken Access Control (the #1 risk).

**Options:**

| | Option A: Simple Role Check | Option B: RBAC (Role-Based Access Control) | Option C: ABAC (Attribute-Based Access Control) | Option D (local/cheap): Owner-Based |
|---|---------|---------|---------|---------|
| What | Hardcoded `if (user.role === 'admin')` checks | Roles mapped to permissions, checked via middleware | Policies based on user attributes, resource attributes, and context | Only the resource creator can modify it |
| Best for | Small apps with 2-3 roles | Medium apps with clear role hierarchy | Complex multi-tenant, fine-grained access | Single-user apps, simple ownership models |
| Trade-off | Scattered checks, hard to audit (OWASP A01) | Must maintain role-permission mappings | Policy engine complexity, harder to debug | No shared access, no delegation |
| Cost | Free | Free (implement or use library) | Free (OPA, Casbin) to paid (commercial policy engines) | Free |
| SOLID/DRY check | ⚠️ Violates DRY — checks everywhere | ✅ Centralized permission logic | ✅ Policy-as-code, single source of truth | ✅ Simple ownership rule |

**Implementation guidance:**
- Always enforce server-side, never trust client-side checks
- Use middleware/decorators to enforce consistently — don't repeat checks in every handler
- Test authorization: "Can user A access user B's data?" should be an explicit test case (IDOR testing)
- Log authorization failures for security monitoring

**Consequence:** Affects API middleware, database query scoping, and UI element visibility.

---

### Decision 3: Data Protection

**Context:** How sensitive data is protected at rest and in transit. Depends on data sensitivity from requirements.

**OWASP relevance:** A02:2021 — Cryptographic Failures.

**Options for encryption at rest:**

| | Option A: Database-Level Encryption | Option B: Application-Level Encryption | Option C: Field-Level Encryption |
|---|---------|---------|---------|
| What | Database engine encrypts all data on disk (TDE) | Application encrypts specific data before storing | Individual fields encrypted with different keys |
| Best for | Compliance checkbox, broad protection | Sensitive fields (SSN, credit card) with key control | Multi-tenant with per-tenant keys, need-to-know access |
| Trade-off | No protection against SQL injection reading data | Key management complexity, can't query encrypted fields | Most complex, highest key management overhead |
| Cost | Often included in managed DB | Free (libraries) + key management | Free (libraries) + key management |
| SOLID/DRY check | ✅ Transparent to app code | ✅ Explicit control over what's protected | ✅ Fine-grained but complex |

**Encryption in transit:** Always enforce TLS 1.2+ (OWASP A02). Use HSTS headers. Pin certificates for mobile apps.

**Additional data protection decisions:**
- **Password hashing:** bcrypt or Argon2 (never MD5/SHA)
- **Sensitive data in logs:** Strip PII from log output
- **Data retention:** Define how long each data type is kept, automated deletion
- **Backup encryption:** Backups must be encrypted at rest with separate keys

**Consequence:** Affects database query patterns, backup encryption, and key rotation processes.

---

### Decision 4: Input Validation & OWASP Top 10

**Context:** Defending against common attacks. Applies at every boundary — API, forms, file uploads, webhooks. **Directly addresses OWASP Top 10 (G-ARCH-2).**

**Validation strategy by OWASP risk:**

| OWASP Risk | Defense | Implementation |
|------------|---------|----------------|
| A01: Broken Access Control | Server-side authz checks on every endpoint | Middleware + per-resource ownership checks |
| A02: Cryptographic Failures | TLS everywhere, strong hashing (bcrypt/argon2), no secrets in code | Config-driven, audited regularly |
| A03: Injection | Parameterized queries, ORM usage, input sanitization | Never concatenate user input into queries/commands |
| A04: Insecure Design | Threat modeling, abuse case testing | Security review in design phase |
| A05: Security Misconfiguration | Hardened defaults, no debug in production, least privilege | Automated config checks in CI |
| A06: Vulnerable Components | Dependency scanning, automated updates | `npm audit`, Dependabot, Snyk |
| A07: Auth Failures | Rate limiting, MFA, strong passwords | See Decision 1 |
| A08: Software/Data Integrity | Signed deployments, integrity checks on dependencies | CI/CD pipeline verification |
| A09: Logging Failures | Security event logging, tamper-proof audit trail | See Decision 6 |
| A10: SSRF | Allowlist outbound URLs, validate/sanitize URLs | Network-level + application-level controls |

**Options for validation approach:**

| | Option A: Schema Validation (Zod/Joi/Pydantic) | Option B: Manual Validation | Option C: Framework Built-In |
|---|---------|---------|---------|
| What | Declare input schema, validate automatically | Hand-written validation logic per endpoint | Use framework's built-in validation (Django forms, Rails strong params) |
| Best for | Type-safe APIs, contract-first development | Simple apps with few endpoints | Apps using full-stack frameworks |
| Trade-off | Schema maintenance, learning curve | Inconsistent, easy to miss edge cases | Framework-specific, less portable |
| SOLID/DRY check | ✅ DRY — schema is single source of truth | ⚠️ Violates DRY — validation scattered | ✅ Framework-enforced consistency |

**Consequence:** Affects error handling, API contract design, and security testing requirements.

---

### Decision 5: Secret Management

**Context:** How secrets (API keys, database credentials, signing keys) are stored and accessed. Never hardcode secrets (OWASP A02).

**OWASP relevance:** A07:2021 — Identification and Authentication Failures (hardcoded credentials).

**Options:**

| | Option A: Environment Variables (.env) | Option B: Cloud Secrets Manager | Option C: HashiCorp Vault | Option D (local/cheap): Encrypted .env + Git-Ignored |
|---|---------|---------|---------|---------|
| What | Secrets in `.env` file, loaded at runtime | Cloud-managed secret storage with rotation (AWS Secrets Manager, GCP Secret Manager) | Self-hosted secret management with dynamic secrets | `.env` file encrypted with age/sops, never committed |
| Best for | Local development, small deployments | Cloud-native apps, teams needing rotation | Multi-cloud, dynamic database credentials, PKI | Solo developers, early-stage projects |
| Trade-off | No rotation, no audit trail, leak risk if committed | Cloud vendor lock-in, API latency for secret access | Operational complexity, must manage Vault itself | Manual rotation, no audit trail |
| Cost | Free | $0.40/secret/month (AWS) | Free (open source) + infrastructure | Free |
| SOLID/DRY check | ✅ Simple, universal | ✅ Centralized, auditable | ✅ Full lifecycle management | ✅ Simple with encryption |

**Non-negotiable practices (all options):**
- `.env` files are ALWAYS in `.gitignore`
- Secrets are NEVER logged, even at debug level
- Rotate secrets on any suspected compromise
- Use different secrets per environment (dev/staging/prod)
- Use least-privilege: each service gets only the secrets it needs

**Consequence:** Affects deployment process, CI/CD configuration, and onboarding documentation.

---

### Decision 6: Security Monitoring & Audit

**Context:** Detecting and responding to security incidents. Addresses OWASP A09 (Security Logging and Monitoring Failures).

**Options:**

| | Option A: Application Logging Only | Option B: Structured Security Events | Option C: SIEM Integration |
|---|---------|---------|---------|
| What | Log security events in application logs | Dedicated security event stream with structured format | Forward events to Security Information and Event Management system |
| Best for | Small apps, early stage | Production apps needing incident investigation | Enterprise, regulated industries, SOC teams |
| Trade-off | Hard to search, mixed with app logs | Must define event schema, storage cost | Complex integration, cost, alert fatigue |
| Cost | Free (part of app logging) | Moderate (structured logging infra) | High ($100-10,000+/mo for SIEM) |
| SOLID/DRY check | ⚠️ Security events mixed with app events | ✅ Clear separation of security concerns | ✅ Centralized security monitoring |

**Events to log (minimum):**
- Authentication attempts (success and failure)
- Authorization failures
- Input validation failures
- Admin actions
- Data export/bulk access

**Consequence:** Affects log infrastructure, retention policies, and incident response playbooks.

---

## Decision Format Reference

Each decision above follows the standard format from the base SKILL.md. For guardrails (G-ARCH-1 through G-ARCH-4, G1-G9), see `shared/guardrails.md` — they are not duplicated here. G-ARCH-2 (OWASP Top 10 reference) is directly addressed throughout, particularly in Decision 4.
