---
role: frontend
sources: 7
synthesized_at: 2026-08-17T00:41:51.248595
---

## [DRAFT — HUMAN REVIEW REQUIRED]

> Note: Source `airbnb-engineering` returned zero content (Cloudflare block) — excluded from synthesis. 6 usable sources.

## Role Summary
Frontend concerns extracted from 5 repos + 1 engineering blog: component libraries and design systems, accessible forms, data fetching/state management (TanStack Query patterns), Web Vitals measurement and optimization, monorepo-based UI package organization, and build/test tooling for UI code.

## Patterns Found (ranked by frequency)

### 1. Monorepo with shared UI/core package (5/6 — hoppscotch, shadcn-ui, tanstack-query, twenty, next.js)
Shared logic lives once; framework/app targets are thin consumers.
- **hoppscotch**: `hoppscotch-common` (Vue components/stores) consumed by web, desktop (Tauri), admin, agent
- **tanstack-query**: `query-core` (framework-agnostic state machine) + thin adapters (`react-query`, `svelte-query`, `vue-query`)
- **twenty**: `twenty-ui` design system separate from `twenty-front` app; individual component builds via `vite.config.individual.ts`
- **shadcn-ui**: `packages/*` publishable, `apps/*` consume — one-way dependency graph
- Task runners vary: Turborepo (shadcn, next.js), Nx (tanstack, twenty), pnpm workspaces (hoppscotch)

### 2. Workspace-level dependency pinning via pnpm overrides (3/6 — hoppscotch, shadcn-ui, tanstack)
```json
"pnpm": { "overrides": { "@types/react": "19.2.2" } }  // shadcn — prevents duplicate JSX.Element type errors
"vue": "3.5.40", "postcss@<=8.5.17": "8.5.18"          // hoppscotch — security pins
```
tanstack adds `sherif` tool for automated version-drift detection.

### 3. GraphQL codegen from standalone files (2/6 — hoppscotch, twenty)
- **hoppscotch**: one `.graphql` file per operation in `src/api/mutations/`, per-package `gql-codegen.yml`
- **twenty**: 3 separate codegen configs (`codegen.cjs`, `codegen-admin.cjs`, `codegen-metadata.cjs`) — one per API surface to prevent type collisions

### 4. Data-attribute + CSS conditional rendering (Vercel blog)
```js
document.documentElement.dataset.userDisplay = isLoggedIn ? "logged-in" : "logged-out";
```
```css
html[data-user-display="logged-in"] [data-user-display="logged-out"] { display: none !important; }
```
Auth-gated UI with zero hydration cost, no CLS. Same pattern for scroll state (`data-scrolled`).

### 5. FOUC-prevention via synchronous inline IIFE (Vercel blog)
Theme read from localStorage in `<head>` before paint; `prefers-color-scheme` fallback for "system"; silent `catch {}` on storage errors; sets `colorScheme` style for native UI.

### 6. Prettier as sole formatter + enforced import order (shadcn, tanstack, twenty)
- shadcn: `@ianvs/prettier-plugin-sort-imports` with explicit layer ordering (react → next → third-party → `@workspace` → `@/lib` → `@/components/ui` → `@/components`); `prettier-plugin-tailwindcss` with `tailwindFunctions: ["cn", "cva"]`
- tanstack/twenty: `singleQuote: true, trailingComma: 'all'`
- ESLint handles logic only (`eslint-config-prettier` disables format rules); twenty is migrating ESLint → Oxlint (Rust, faster)

## How Problems Are Solved

### PROBLEM: Optimistic updates without desync (tanstack-query)
Cancel → snapshot → update → rollback → always invalidate:
```typescript
onMutate: async (newTodo) => {
  await client.cancelQueries({ queryKey: ['todos'] })      // prevent race
  const previous = client.getQueryData<Todos>(['todos'])   // snapshot
  client.setQueryData<Todos>(['todos'], /* optimistic */)
  return { previous }
},
onError: (err, vars, ctx) => client.setQueryData(['todos'], ctx.previous),
onSettled: () => client.invalidateQueries({ queryKey: ['todos'] })  // resync always
```

### PROBLEM: Accessible form validation (shadcn-ui fixtures)
```tsx
aria-invalid={errors?.email ? true : undefined}  // undefined, NOT false — removes attr from DOM
aria-describedby="email-error"
// Focus recovery on server validation failure:
useEffect(() => { if (errors?.email) emailRef.current?.focus() }, [actionData])
<div id="email-error">{errors.email}</div>  // id matches aria-describedby
```
Also: `aria-errormessage` requires `aria-invalid="true"` to work; prefer `aria-describedby` (broader AT support). Use `autoComplete="new-password"` on registration vs `current-password` on login.

### PROBLEM: Pagination content flash (tanstack)
```typescript
useQuery({ queryKey: ['projects', page], placeholderData: keepPreviousData })
```
Infinite scroll: `useInfiniteQuery` + `getNextPageParam`; max-pages variant bounds cache memory.

### PROBLEM: SSR hydration mismatch with queries (tanstack)
```typescript
new QueryClient({ defaultOptions: { queries: { enabled: browser } } })
```

### PROBLEM: Measuring real navigation performance (Vercel blog)
```js
performance.measure("content visible", {
  end: performance.now(),
  detail: { vercelNavigation: { isHardNavigation: true, phase: "content", label: "MarketingPageWrapper" } }
});
```
User Timing L3 with `detail`; deduplication via `globalThis` Map; per-component labels. Article's key claim: **Google ranking uses only CrUX field data (LCP/INP/CLS) — Lighthouse score has zero ranking impact**; lab TBT ≠ real INP.

### PROBLEM: Error boundary handling (shadcn fixtures / Remix)
Three-tier: `error instanceof Error` → `!isRouteErrorResponse(error)` → `error.status === 404` gets friendly copy, rest get generic fallback.

### PROBLEM: Nav active state
Router-provided `isActive` render prop (`<NavLink className={({isActive}) => ...}>`) — no useState/useEffect tracking (shadcn fixtures).

### PROBLEM: Client state management hierarchy (next.js examples, proposed fix for inconsistency)
1. Server state → Server Components (no useState)
2. URL state → `useSearchParams` / nuqs
3. Ephemeral UI → `useState` in Client Components
4. Cross-component → Context/Zustand only when needed

### PROBLEM: Query key hygiene (tanstack)
Structured keys `[entity, params]` enable hierarchical invalidation. Options as factory function `() => ({...})` for reactivity. Enforced by ESLint plugin (`exhaustive-deps`, `no-unstable-deps`, `stable-query-client`).

## Architecture Decisions Seen

| Decision | Chosen | Tradeoff |
|---|---|---|
| Component distribution (shadcn) | Registry + copy-paste via CLI, not npm dep | Users own code, no upgrade lock-in ↔ no automatic updates |
| Devtools (tanstack) | Separate opt-in packages per framework | Zero prod bundle cost ↔ more packages |
| A/B variants (Vercel) | Static paths `/precomputed/[experimentCode]/blog/[slug]` | Max CDN cacheability ↔ variants fixed at build time |
| i18n (twenty) | Lingui compile-time extraction | Smaller bundles, type-safe IDs ↔ vs runtime react-intl |
| i18n (hoppscotch) | `locales/` dirs + `languages.json` per package | — |
| Styling (twenty website) | wyw-in-js zero-runtime CSS-in-JS | No runtime cost ↔ vs Tailwind (hoppscotch/shadcn/next.js examples use Tailwind with shared presets) |
| Test runners (twenty) | Jest + Vitest coexist | Incremental migration, avoids big-bang risk |
| CMS examples (next.js) | Full example per CMS (12+) | Isolation ↔ massive UI duplication, drift risk |
| Theme (Vercel) | Sync inline script | No FOUC ↔ small parse-blocking script |

## Testing Approaches
- **Vitest dominant** (hoppscotch, shadcn, tanstack, twenty-frontend packages); jsdom for DOM; separate `test-setup.ts` per package
- **Type tests**: `*.test-d.ts` with `expectTypeOf` (tanstack) — TS inference regressions treated as bugs
- **Real fixtures over mocks**: shadcn CLI tested against complete Remix/Next.js apps
- **Browser vs Node split configs**: `vitest.browser.config.ts` for DOM tests, plain config for utilities (shadcn)
- **Storybook-driven tests**: `vitest.storybook.config.ts` runs Vitest against stories (twenty)
- **E2E**: Playwright with custom reporters (twenty)
- **Fresh builds before integration tests**: `pnpm registry:build && start-server-and-test dev http://localhost:4000 test:dev` (shadcn) — never test stale artifacts
- **CI gates**: `size-limit` bundle budget, `knip` dead code, `sherif` version drift (tanstack); typecheck in pre-commit hooks (hoppscotch)
- **Enforced test style**: `vitest/consistent-test-it` — always `it()`, never `test()` (tanstack)
- **A11y gap noted** (next.js): benchmark UIs lack axe/a11y coverage; eval agents check `next/image` usage but not actual Web Vitals outcomes (`fetchpriority="high"` on LCP image, `font-display: swap|optional`)

## Deployment & Production
- **Static serving**: Caddy per package with subpath vs multi-port configs feature-flagged (hoppscotch); OpenNext → Cloudflare Workers (twenty website); immutable content-hashed chunks with `max-age=31536000` (Vercel)
- **Observability**: OpenTelemetry collector + Grafana dashboards (twenty); `performance.measure` RUM → Speed Insights (Vercel)
- **Healthcheck**: parallel DB + HTTP self-check via `Promise.all` (shadcn fixture) — catches routing failures a DB-only ping misses
- **Error recovery**: silent catch for non-critical UI scripts (theme/avatar), console.error + non-blocking for infra scripts (Vercel)
- **Node/tooling pinning**: `engines.
