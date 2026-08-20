---
role: security
sources: 7
synthesized_at: 2026-08-17T00:59:19.403747
---

## [DRAFT — HUMAN REVIEW REQUIRED]

## Role Summary
Security knowledge synthesized from 7 sources: two auth/secrets platforms (Vaultwarden, Infisical), one auth library (Lucia), one security-header library (Helmet), the OWASP CheatSheetSeries knowledge base, and two rendered blog pages (Cloudflare, GitHub Blog). Coverage spans auth design, session/JWT management, CSP, supply chain hardening, secrets management, rate limiting, and compliance patterns.

## Patterns Found (ranked by frequency across repos)

**1. Secrets via environment variables only (3 repos: Infisical, Vaultwarden, implied Lucia-consumer)**
```
# Infisical .env.example — sample keys explicitly marked unsafe
# THIS IS A SAMPLE ENCRYPTION KEY AND SHOULD NEVER BE USED FOR PRODUCTION
ENCRYPTION_KEY=f13dbc92aaaf86fa7cb0ed8ac3265f47
```
Vaultwarden: all config via env vars + `dotenvy`; Infisical uses namespaced prefixes (`INF_APP_CONNECTION_[PROVIDER]_[KEY]`).

**2. Prototype pollution defense (2 repos: Helmet, Cloudflare/Astro)**
- Astro island hydration blocklist: `new Set(["__proto__", "constructor", "prototype"])` — throws on match
- Helmet: `hasOwn` checks on CSP directives; tested with `Object.create(null)` input and inherited-property rejection

**3. Hash-based CSP for static sites (2 sources: Cloudflare blog, Helmet defaults)**
- Cloudflare: inline scripts CSP-hashed at build; source comment: *"Keep this file free of imports. Any content change changes the CSP hash."* Chosen over nonces because SSG can't inject per-request nonces.
- Helmet default CSP: `default-src 'self'; object-src 'none'; script-src-attr 'none'; upgrade-insecure-requests` — note `style-src` includes `'unsafe-inline'` by default (pragmatic compat choice)

**4. Config-time validation, fail-fast at startup (2 repos: Helmet, Vaultwarden)**
- Helmet validates options in factory, throws before requests flow; runtime CSP-function errors → `next(err)` and header **not set** (fail-closed)
- Vaultwarden: RSA key init failure = `exit(1)`

**5. Docker supply-chain hardening (2 repos: Vaultwarden, Infisical; counter-example: OWASP)**
```dockerfile
# Vaultwarden — SHA256 digest pinning, multistage
FROM docker.io/vaultwarden/web-vault@sha256:ba8bab66d4... AS vault
COPY --from=build /app/target/final/vaultwarden .
```
OWASP CheatSheetSeries counter-example: `FROM python:3.14-slim` (pre-release), single-stage, no `USER`, no HEALTHCHECK, no `.dockerignore`.

**6. Dependency pinning/overrides for CVEs (3 repos)**
- Infisical `package.json` overrides: `"minimatch": "^3.1.3", "js-yaml": "^4.1.1"` (historical CVE pins)
- Helmet: **zero runtime dependencies**; `allowScripts` allowlist for postinstall scripts of specific pinned versions
- OWASP: devDependencies only + `package-lock.json`

**7. Enterprise/draft content physically separated (2 repos)**
- Infisical: `ee/` directories in both backends (open-core isolation)
- OWASP: `cheatsheets_draft/` vs `cheatsheets/` — hard filesystem gate prevents tooling from endorsing draft guidance

## How Problems Are Solved

**PROBLEM: Admin/password credential storage**
Vaultwarden: Argon2id PHC hash for admin token, two presets — `bitwarden` (64MiB/3iter/4thread) vs `owasp` (19MiB/2iter/1thread). Argon2 compiled at opt-level 3 even in dev builds.

**PROBLEM: Session strategy — stateful vs JWT**
- Lucia: stateful DB sessions → immediate revocation, no token replay window; sliding dual-period expiry (active/idle). Flag: verify max lifetime cap exists.
- Vaultwarden: JWT via `jsonwebtoken` with `rust_crypto` backend (pure Rust, not OpenSSL); RSA keys generated at startup.
- Cookie hygiene (Lucia expected pattern): `httpOnly: true, secure: true, sameSite: "lax"` — SameSite=Lax as baseline CSRF mitigation.

**PROBLEM: MFA / WebAuthn**
Vaultwarden: `webauthn-rs` with `danger-allow-state-serialisation` (challenge state persisted to DB for stateless serving) + `danger-credential-internals` (U2F→WebAuthn migration). Startup migrations: `migrate_u2f_to_webauthn`, `migrate_credential_to_passkey`. TOTP via `totp-lite`; YubiKey via `yubico_ng`.

**PROBLEM: SSO/OIDC integration**
- Vaultwarden: `openidconnect` crate, state/nonce cached in `moka`; opt-in relaxed parsing flags for non-compliant IdPs (`oidc-accept-rfc3339-timestamps`)
- Infisical: SAML, SCIM, OIDC, LDAP, Kerberos/AD, machine auth (AWS/Azure/GCP/K8s); E2E tests specifically for **SAML rejection** and **SCIM deactivation** (deprovisioned users lose access)

**PROBLEM: SSRF on outbound fetches (favicons)**
Vaultwarden: `svg-hush` (SVG sanitization), dedicated `src/http_client.rs`, `hickory-resolver` DNS, `ipnet` for trusted-proxy CIDR validation.

**PROBLEM: Rate limiting / brute force**
Vaultwarden: `governor` token-bucket in `src/ratelimit.rs`. Infisical: CAPTCHA on auth flows (`CAPTCHA_SECRET`). Lucia: explicitly delegates to consumer (documented gap).

**PROBLEM: Key hierarchy & recovery**
Infisical: platform `ENCRYPTION_KEY` + JWT `AUTH_SECRET` + `keystore/` module + Shamir's Secret Sharing (`secrets.js-grempe`) for threshold key recovery. HSM via PKCS#11 (SoftHSM2 in dev). FIPS-mode dual Docker builds (`nodejs.fips.cnf` OpenSSL FIPS provider).

**PROBLEM: Exfiltration detection**
Infisical: honey-token pipeline (CloudFormation canary secrets) + CLI secret scanning.

**PROBLEM: Timing attacks**
Vaultwarden: `subtle` crate for constant-time comparison. Lucia: flagged for manual verification (must not use `===` on session IDs).

**PROBLEM: Compliance traceability**
OWASP: index files mapping cheat sheets to ASVS v4/v5, MASVS, Top 10, Proactive Controls. Note: OAuth cheat sheet still in draft — no canonical published version.

## Architecture Decisions Seen

| Decision | Choice | Tradeoff |
|---|---|---|
| Auth session model | Lucia: stateful sessions vs JWT | Revocation + no token leakage vs per-request DB lookup |
| Auth distribution | Lucia: library vs hosted service | Data sovereignty vs consumer bears misconfiguration risk |
| CSP mechanism | Cloudflare: hashes vs nonces | SSG-compatible vs redeploy on any inline-script change |
| Memory safety | Vaultwarden: `unsafe_code = "forbid"` workspace-wide; `warnings = "deny"` | Strict but forecloses low-level optimization |
| COEP default | Helmet: **opt-in** (unlike all other headers) | Breaks non-isolated contexts if on by default |
| Legacy XSS auditor | Helmet: `X-XSS-Protection: 0` | Disables broken browser filter that itself introduced vulns |
| TLS termination | Vaultwarden: app-layer (Rocket TLS); Infisical: Nginx proxy (internal traffic unencrypted) | Simplicity vs internal encryption |
| Third-party fonts/CDN | Cloudflare: self-hosted woff2 | Avoids IP leak to Google, simplifies `font-src` CSP |
| Consent management | Cloudflare: `OptanonWrapper` stubbed empty | Flagged: verify GDPR Art. 7/CCPA consent flow completeness |
| Crypto stack | Vaultwarden: dual `ring`/`rustls` + legacy `openssl` (U2F, libpq) | Modern default with legacy compat surface |
| Audit logs | Infisical: ClickHouse (opt-in) separate from Postgres | Scale vs operational complexity |

## Testing Approaches

- **Full IdP stacks in Docker Compose for auth E2E** (2 repos): Vaultwarden runs Keycloak + Playwright (`sso_login.spec.ts`, `sso_organization.spec.ts`); Infisical runs Keycloak, PingFederate, OpenLDAP, Samba AD, MailHog
- **Negative auth tests**: Infisical `saml-rejection.spec.ts`, `scim-deactivation.spec.ts` — explicit deprovisioning/rejection coverage
- **Fail-closed verification**: Helmet tests assert CSP header is *absent* when dynamic directive functions throw, and subsequent functions aren't called
- **CSP keyword quoting tests**: Helmet `shouldBeQuoted` array — unquoted `self` is a host match, not the keyword
- **No mocking of HTTP**: Helmet uses real servers via `supertest` + `node:test`
- **ACME/cert lifecycle**: Infisical BDD tests against Pebble ACME server + Technitium DNS
- **Module-system compat matrix**: Helmet tests 8 CJS/ESM/TS project setups
- **Gap**: Lucia snapshot had no visible tests or `package.json` — dependency audit blocked

## Deployment & Production

- **Digest-pinned multistage Docker + healthchecks**: Vaultwarden (`HEALTHCHECK --interval=60s`, runtime image contains only binary)
- **FIPS-compliant parallel builds**: Infisical (same codebase, two security postures)
- **Observability**: Infisical — OpenTelemetry (Prometheus port 9464), Sentry, Datadog APM; Vaultwarden — `fern` + syslog, log rotation via signal, `SIGUSR1` backup trigger
- **Static-site attack surface reduction**: Cloudflare blog (Astro SSG, no server rendering), OWASP (mkdocs) — though OWASP container runs as root on mkdocs dev server (not production-hardened)
- **Graceful degradation**: Cloudflare search component
