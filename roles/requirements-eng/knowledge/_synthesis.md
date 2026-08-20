---
role: requirements-eng
sources: 5
synthesized_at: 2026-08-17T02:24:32.114717
---

## [DRAFT — HUMAN REVIEW REQUIRED]

## Role Summary
This role covers translating specs into code structure decisions: i18n strategy selection, monorepo/package boundary definition, feature scoping (CE/EE, feature flags), spec-driven workflows, and tech selection for extensibility. Sources: two i18n libraries (next-intl, i18next) and three product apps (cal.com, documenso, plane) with heavy i18n and modular architecture concerns.

## Patterns Found (ranked by frequency)

**1. Monorepo with build orchestration (5/5)**
All repos: workspace-based monorepo. Turborepo in 4/5 (next-intl, cal.com, documenso, plane); i18next is single-package.
- Package managers vary: pnpm (next-intl, plane), Yarn 4 (cal.com), npm (documenso)
- Publishing: lerna-lite (next-intl); internal-only packages elsewhere

**2. Framework-agnostic core + framework wrapper (3/5)**
- next-intl: `use-intl` (core) wrapped by `next-intl` (Next.js layer)
- i18next: zero-dependency core + plugin ecosystem (`BackendModule`, `LoggerModule`, etc.)
- plane: `@plane/*` packages (`ui`, `i18n`, `services`, `types`) consumed by 4 apps
Requirements implication (noted in next-intl): specs must identify which layer a feature targets; core-layer changes break non-framework consumers.

**3. Pluggable strategy/transport pattern (3/5)**
- documenso: env-selected transports — signing (`local|gcloud-hsm|csc`), email (`smtp|resend|mailchannels`), storage (`database|s3`), jobs (`local|inngest|bullmq`)
- i18next: typed plugin registry via `use()`:
```typescript
export type ModuleType = 'backend' | 'logger' | 'languageDetector'
  | 'postProcessor' | 'i18nFormat' | 'formatter' | '3rdParty';
```
- cal.com: App Store pattern (`packages/app-store/<appname>/`) with CLI scaffolding

**4. Spec/RFC-driven development (2/5)**
- next-intl: `rfcs/001-message-extraction.md`, `rfcs/002-icu-message-precompilation.md` precede implementation
- cal.com: `specs/<feature>/` with templated `design.md`, `implementation.md`, `decisions.md`, `future-work.md`; plus `agents/rules/*.md` codifying architecture constraints for AI-assisted dev (e.g., `architecture-circular-dependencies.md`, `api-no-breaking-changes.md`)

**5. Validation-at-boundary (3/5)**
- documenso: Zod middleware — `.post('/authorize/google', sValidator('json', ZOAuthAuthorizeSchema), ...)`
- next-intl: locale allowlist guard — `if (!hasLocale(routing.locales, locale)) return new Response('Invalid locale', {status: 400})`
- cal.com: DTO boundaries enforced as agent rule (`data-dto-boundaries.md`)

**6. Edition/feature gating (3/5)**
- plane: CE/EE via route merging — `mergeRoutes(core, extended)`, deep merge by `file` key, extended overrides core
- documenso: `packages/ee/` physically isolated with separate LICENSE; PostHog runtime flags
- cal.com: DB-backed feature flags in Prisma (rule: `data-prisma-feature-flags.md`), not env vars

## How Problems Are Solved

**PROBLEM: i18n strategy selection** — four distinct stacks observed:
| Repo | Framework | Format | Extraction | Translator workflow |
|---|---|---|---|---|
| next-intl | next-intl/use-intl | JSON (ICU MessageFormat), optional PO | Rust/SWC plugin at build time | Crowdin (documented) |
| documenso | LinguiJS | PO, compiled to ES modules | `lingui extract --clean` | Crowdin (`crowdin.yml`) |
| cal.com | next-i18next (patched) | JSON in `packages/i18n/locales/` | n/a | `i18n-unused` for dead-key detection |
| i18next | (is the library) | any via BackendModule | consumer-side | plugin ecosystem |

**PROBLEM: dead/orphaned translation keys**
- cal.com: `i18n-unused` with regex matcher:
```js
translationKeyRegex = /(?<!\w)(?:t\(("[^"]*")(?:,\s*\{[^}]*\})?\)|i18nKey=".+"[^\w])/gi
```
- next-intl: compile-time type checks from message JSON (generated key types)
- i18next: `CustomTypeOptions` declaration merging for compile-time key enforcement:
```typescript
declare module 'i18next' {
  interface CustomTypeOptions { resources: { ns: { key: 'value' } } }
}
```

**PROBLEM: locale validation (spec-to-code mapping)**
- next-intl: `routing.locales` as single source of truth; `hasLocale()` type-safe check; URL segment `[locale]`
- i18next: fallback chains via `hasLoadedNamespace()` with injectable `precheck` callback

**PROBLEM: scope/change propagation control**
- cal.com: `api-no-breaking-changes.md` rule + versioned API (`apps/api/v2/`); `architecture-circular-dependencies.md`
- documenso: two API surfaces — tRPC (internal) + ts-rest/OpenAPI (external, versioned `packages/api/v1/`)
- i18next: compatibility test suites for v1 and v4 APIs (`test/compatibility/`)

**PROBLEM: env/config as spec**
- documenso: `.env.example` as canonical reference with inline `REQUIRED:`/`OPTIONAL:` annotations; `NEXT_PUBLIC_*` vs `NEXT_PRIVATE_*` naming
- plane: deprecated vars kept in `.env.example` with `# deprecated` comments rather than removed
- cal.com: `dotenv-checker` validates `.env` against `.env.example`

## Architecture Decisions Seen

**Router migration coexistence**: cal.com runs App Router + Pages Router simultaneously (in-progress migration); next-intl supports both with a dedicated migration example (`example-app-router-migration`); plane chose React Router v7 framework mode over Next.js. Tradeoff: dual-router support doubles test surface.

**Dual module system**: i18next ships CJS + ESM + UMD + UMD-min from separate entries (`index.cjs` collapses named exports); next-intl uses per-concern `.d.ts` entry points (`server.d.ts`, `middleware.d.ts`, `navigation.d.ts`) to prevent server code leaking to client bundles.

**Compile-time vs runtime i18n optimization**: next-intl makes ICU pre-compilation opt-in (`icu-minify`, RFC 002) — specs must account for both raw-JSON and precompiled paths. Rust/SWC extraction plugin excluded from main build pipeline.

**Multi-app deployment split**: plane deploys 4 frontends (web/admin/space/live) + entrypoint-differentiated workers (single Docker image, different entrypoint scripts for api/worker/beat/migrator).

**Types as spec**: i18next hand-authors `.d.ts` files (not generated) — TypeScript declarations function as the authoritative behavioral contract.

## Testing Approaches

- **Scenario-per-directory e2e** (next-intl): `e2e/extracted-json/`, `e2e/extracted-po/`, `e2e/no-js/`, `e2e/extracted-monorepo-app/` — each integration scenario is its own Playwright app
- **Mode-switched test suites** (cal.com): `VITEST_MODE` selects integration/timezone/embed/default; file suffixes encode intent (`*.integration-test.ts`, `*.timezone.test.ts`)
- **Type-level testing** (i18next): `@arktype/attest` for assertions on TypeScript types; separate `test/typescript/` tree
- **Compatibility suites** (i18next): v1/v4 API compat tests as regression contract
- **`cimode` escape hatch** (i18next): setting lng to `'cimode'` makes `t()` return keys — spec-level test bypass
- **Isolated test environments** (plane): `docker-compose-test.yml` separate from dev compose
- Playwright universal (4/5 for e2e); Vitest dominant for unit (4/5)

## Deployment & Production

- **Publishing**: next-intl uses `lerna publish` + conventional commits changelogs
- **Migration isolation** (plane): dedicated `migrator` container with `restart: no` — runs once, prevents re-migration races
- **Proxy-level enforcement** (plane): file size limits enforced at Caddy proxy, not app layer
- **Translation CI**: documenso requires `lingui compile` before dev; Crowdin sync in both documenso and next-intl
- **Observability**: Sentry + Checkly synthetic monitoring (cal.com); pino + Datadog pprof (documenso)
- **Patched dependencies as production strategy**: cal.com patches next-i18next and dayjs via yarn patches; next-intl patches nextra via pnpm `patchedDependencies` — vendored fixes tracked in-repo

## Open Questions (for reviewer)

1. **i18n framework choice conflicts**: JSON+ICU (next-intl) vs PO+Lingui (documenso) vs next-i18next (cal.com). Which should be the recommended default for new projects?
2. **Message extraction timing**: build-time Rust/SWC plugin (next-intl) vs CLI extraction step (documenso/Lingui) vs no extraction + dead-key scanning (cal.com). Different maintenance/CI costs.
3. **Feature gating mechanism**: route merging (plane) vs isolated EE package (documenso) vs DB-backed flags (cal.com). Route merging is build-time; flags are runtime — different spec implications.
4. **Spec workflow formality**: RFC docs for library features (next-intl) vs full spec-template directories + AI agent rules (cal.com). Should agent-rule files (`agents/rules/*.md`) be adopted as a requirements-traceability mechanism?
5. **Type-safety source of truth**: generated types from message files (next-intl) vs consumer declaration merging (i18next) vs regex scanning (cal.com) — compile-time vs lint-time gap detection.
6. **Config-as-spec**: is `.env.example` with REQUIRED/OPTIONAL annotations (documenso) sufficient as configuration requirements documentation, or should deprecation markers (plane style) also be mandated?
