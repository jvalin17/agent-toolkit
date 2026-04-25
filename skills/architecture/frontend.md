# Frontend Architecture

Decisions for the frontend layer of the system. Only relevant when requirements include a UI.

## Inputs

Read `requirements/<name>.md` and extract:
- **UI/UX Requirements** section — design direction, target platforms, responsiveness needs
- **Design Direction** — visual style, component library preferences
- **Performance targets** — load time, bundle size, Core Web Vitals
- **Accessibility requirements** — WCAG level (A, AA, AAA)
- **User types** — affects complexity of routing, state, and a11y needs

Also read the Quick Architecture from `architecture/<name>.md` for the chosen architecture pattern and tech stack baseline.

## Decision Order

Decisions are presented in waterfall order. Each choice constrains the next.

---

### Decision 1: Frontend Framework

**Context:** The foundational choice. Everything else builds on this.

**Options:**

| | Option A: React/Next.js | Option B: Vue/Nuxt | Option C: Svelte/SvelteKit | Option D (local/cheap): Plain HTML/CSS/JS or Preact/Alpine.js |
|---|---------|---------|---------|----------------------|
| What | Full-featured React ecosystem with optional SSR via Next.js | Progressive framework with optional SSR via Nuxt | Compiler-based framework with built-in SSR via SvelteKit | No framework or ultra-lightweight alternative |
| Best for | Large teams, complex UIs, vast ecosystem | Medium teams, gentle learning curve, good DX | Small-medium teams wanting minimal JS bundle | Prototypes, static sites, very simple UIs |
| Trade-off | Large ecosystem but heavy bundle, complex tooling | Smaller ecosystem than React, fewer jobs | Smallest community, fewer third-party components | Limited structure, harder to scale, no component model (plain JS) |
| Cost | Free (open source) | Free (open source) | Free (open source) | Free, zero dependencies |
| SOLID/DRY check | ✅ Component model supports SRP/OCP | ✅ Component model supports SRP/OCP | ✅ Compiler enforces clean boundaries | ⚠️ No built-in structure — discipline required |

**Example:** "For a dashboard with 20+ interactive views and a 3-person team that knows React, Next.js gives you SSR for SEO pages and CSR for the dashboard — best of both."

**Consequence:** Picking a framework determines available component libraries, routing options, and state management tools.

Consider: team familiarity, ecosystem needs, bundle size constraints, SSR requirements. Launch `tech-stack-advisor` if the user is unsure.

---

### Decision 2: Component Architecture

**Context:** How components are organized. Depends on framework choice (Decision 1) and app complexity.

**Options:**

| | Option A: Flat Components | Option B: Atomic Design | Option C: Feature-Based |
|---|---------|---------|---------|
| What | All components in one directory, no hierarchy | Atoms → Molecules → Organisms → Templates → Pages | Components grouped by feature/domain |
| Best for | Small apps (< 20 components) | Design-system-driven teams, large apps | Product teams organized by feature |
| Trade-off | Simple but becomes chaotic at scale | Clear hierarchy but can feel over-structured for small apps | Good isolation but can lead to duplication across features |
| Cost | Zero overhead | Moderate setup cost for classification | Moderate — need clear feature boundaries |
| SOLID/DRY check | ⚠️ No enforced SRP | ✅ Natural SRP by level | ✅ Good SRP per feature, watch for DRY violations |

**Example:** "Atomic design means: `Button` (atom) → `SearchBar` (molecule) → `Header` (organism) → `PageLayout` (template) → `HomePage` (page). Each level composes the previous."

**Consequence:** Shapes how shared components are discovered and reused. Affects design-system alignment.

---

### Decision 3: State Management

**Context:** How data flows through the app. Depends on component architecture (Decision 2) and app complexity.

**Options:**

| | Option A: Local State Only | Option B: Lifted State + Context | Option C: Global Store (Redux/Zustand/Pinia) |
|---|---------|---------|---------|
| What | Each component manages its own state | State lifted to common ancestors, shared via context/provide-inject | Centralized store accessible from anywhere |
| Best for | Simple apps where components are independent | Medium apps with 2-3 components sharing state | Complex apps with many cross-cutting state needs |
| Trade-off | No shared state complexity, but duplicates state if needed | Moderate complexity, can cause re-render issues in React | Powerful but adds boilerplate and indirection |
| Cost | Zero overhead | Minimal | Library dependency + learning curve |
| SOLID/DRY check | ✅ SRP per component | ✅ Good if context boundaries are clean | ⚠️ Can violate SRP if store becomes a god object |

**Decision tree:** "If most state is local to a component → local state. If 2-3 components share state → lift it. If many components across the tree need the same data → global store."

**Local/cheap alternative:** React Context or prop drilling for small apps. Svelte stores are built-in and free.

**Consequence:** Affects data fetching strategy and how server state integrates with client state.

---

### Decision 4: Styling Approach

**Context:** How the app looks. Should match the Design Direction from requirements. Depends on framework (Decision 1).

**Options:**

| | Option A: CSS Modules | Option B: CSS-in-JS (styled-components/Emotion) | Option C: Utility-First (Tailwind) | Option D: Component Library (shadcn/ui, Material UI) |
|---|---------|---------|---------|---------|
| What | Scoped CSS files per component | CSS written in JavaScript, scoped by default | Utility classes composed in markup | Pre-built, themed component set |
| Best for | Teams that know CSS, want separation | Dynamic styling based on props/state | Rapid prototyping, consistent spacing/colors | Fast MVP, consistent design without a designer |
| Trade-off | Separate files, no dynamic styling | Runtime cost, JS bundle increase | Verbose markup, learning curve for class names | Less control, fights against customization |
| Cost | Zero runtime cost | Runtime overhead (small) | Zero runtime cost (purged CSS) | Free (open source), but upgrade coupling |
| SOLID/DRY check | ✅ Separation of concerns | ⚠️ Mixes style and logic | ✅ DRY via utility composition | ✅ DRY via pre-built components |

**Local/cheap alternative:** Plain CSS or Tailwind — both free, no runtime cost.

**Consequence:** Affects build tooling and how designers/developers collaborate.

---

### Decision 5: Routing Strategy

**Context:** How users navigate between pages/views. Directly depends on framework choice (Decision 1).

**Options:**

| | Option A: File-Based (Next.js/SvelteKit/Nuxt) | Option B: Config-Based (React Router/Vue Router) | Option C: No Router (SPA with hash/simple) |
|---|---------|---------|---------|
| What | File system structure defines routes automatically | Routes declared in a config file or code | Single page with conditional rendering or hash-based navigation |
| Best for | Convention-over-configuration teams, SSR apps | Full control over route structure, complex nested routes | Very simple apps with 1-3 views |
| Trade-off | Less control, must follow file conventions | More boilerplate, manual maintenance | No deep linking, no SSR, poor for complex navigation |
| Cost | Built into framework | Library dependency | Zero |
| SOLID/DRY check | ✅ Convention enforces consistency | ✅ Explicit is good, but watch for duplication | ⚠️ Conditional rendering can violate SRP |

**Consequence:** Affects how code splitting works, how data is loaded per route, and how navigation guards are implemented.

---

### Decision 6: Data Fetching

**Context:** How the frontend gets data from the backend. Must align with API Design decisions from the backend architecture. Depends on framework (Decision 1) and routing (Decision 5).

**Options:**

| | Option A: REST Client (fetch/axios) | Option B: GraphQL Client (Apollo/urql) | Option C: Server Components / Loaders | Option D: tRPC |
|---|---------|---------|---------|---------|
| What | Standard HTTP requests to REST endpoints | GraphQL queries with client-side caching | Data loaded on the server before rendering | End-to-end type-safe RPC calls |
| Best for | Simple CRUD, well-defined endpoints | Complex data needs, multiple related resources | SSR-first apps (Next.js, Remix, SvelteKit) | Full-stack TypeScript monorepos |
| Trade-off | Over/under-fetching, many endpoints | Complex caching, learning curve | Tied to framework, less client-side flexibility | Tight coupling between front and back |
| Cost | Minimal | Apollo is heavy; urql is lighter | Built into framework | Zero runtime cost, build-time only |
| SOLID/DRY check | ✅ Simple and explicit | ⚠️ Can lead to complex cache management | ✅ Clear data-loading boundaries | ✅ Type safety prevents interface drift |

**Caching layer:** Consider React Query / TanStack Query or SWR on top of REST for smart caching, deduplication, and background refetching.

**Cross-reference:** Must align with API style decision in the backend architecture. REST API → REST client. GraphQL API → GraphQL client.

**Consequence:** Shapes error handling, loading states, and optimistic UI patterns.

---

### Decision 7: Frontend Performance

**Context:** How the app stays fast as it grows. Only go deep if requirements mention performance targets or large scale. Depends on framework (Decision 1), routing (Decision 5), and data fetching (Decision 6).

**Options:**

| | Option A: Route-Based Code Splitting | Option B: Component-Based Lazy Loading | Option C: SSR / SSG / ISR |
|---|---------|---------|---------|
| What | Each route loads its own JS bundle | Heavy components loaded on demand (modals, charts, editors) | Pages pre-rendered on server or at build time |
| Best for | Multi-page apps with distinct sections | Apps with heavy optional features | Content sites, SEO-critical pages, slow APIs |
| Trade-off | Navigation delay on first visit to each route | Complexity in managing loading states | Server cost, hydration complexity |
| Cost | Built into most frameworks | Minimal | Server/CDN cost for SSR/SSG |
| SOLID/DRY check | ✅ Natural boundary per route | ✅ Lazy boundaries align with SRP | ✅ Clear rendering strategy per page |

**Additional performance decisions:**
- **Image optimization:** Use framework-provided image components (next/image, @sveltejs/enhanced-img) or lazy loading with Intersection Observer
- **Bundle analysis:** Run bundle analyzer to identify large dependencies; consider lighter alternatives
- **Core Web Vitals:** Target LCP < 2.5s, FID < 100ms, CLS < 0.1

**Local/cheap alternative:** Static site generation (SSG) is free to host on Vercel/Netlify/GitHub Pages.

**Consequence:** Performance choices affect hosting requirements and deployment strategy.

---

### Decision 8: Accessibility Architecture

**Context:** How accessibility is enforced structurally, not just "follow WCAG." Depends on framework (Decision 1) and component architecture (Decision 2). Match to WCAG level from requirements.

**Options:**

| | Option A: Lint-Time Enforcement | Option B: Test-Time Enforcement | Option C: Runtime Monitoring |
|---|---------|---------|---------|
| What | ESLint plugin (eslint-plugin-jsx-a11y) catches issues in editor/CI | Automated a11y tests (axe-core, Playwright a11y) run in test suite | Live a11y audits in dev tools or production monitoring |
| Best for | Catching common issues early (missing alt text, bad ARIA) | Validating rendered DOM for real a11y violations | Catching issues that only appear with real data/interactions |
| Trade-off | Only catches static issues, many false negatives | Slower feedback loop, but catches real issues | Only catches what you test, runtime overhead |
| Cost | Free | Free (axe-core is open source) | Free for dev tools; paid for production monitoring |
| SOLID/DRY check | ✅ Shift-left approach | ✅ Tests enforce contracts | ⚠️ Late detection, harder to fix |

**Recommendation:** Use all three layers — lint catches the easy stuff, tests catch real violations, monitoring catches regressions in production.

**Focus management strategy for SPAs:**
- Route changes: announce new page to screen readers, move focus to main content
- Modals: trap focus inside, return focus on close
- Dynamic content: use ARIA live regions for updates (toasts, notifications, loading states)

**Consequence:** Accessibility architecture affects component API design (every interactive component needs keyboard and ARIA support).

---

## Decision Format Reference

Each decision above follows the standard format from the base SKILL.md. For guardrails (G-ARCH-1 through G-ARCH-4, G1-G9), see `shared/guardrails.md` — they are not duplicated here.
