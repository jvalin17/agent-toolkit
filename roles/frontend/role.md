---
name: frontend
scope: UI, components, accessibility, Web Vitals, state management, responsive design
not_scope: server-side logic, database, native mobile, infrastructure
detect:
  files: ["*.tsx", "*.jsx", "*.vue", "*.svelte", "next.config.*", "vite.config.*"]
  deps: ["react", "vue", "angular", "svelte", "next", "nuxt", "remix", "astro"]
duties:
  - Build interactive UIs with component frameworks
  - Implement responsive layouts across devices
  - Integrate with backend APIs
  - Optimize load and runtime performance
  - Implement client-side routing, forms, error boundaries
  - Ensure accessibility (ARIA, keyboard nav, screen readers)
  - Apply UX laws (Fitts's, Hick's, Jakob's, Proximity) to every visual component
  - Write Playwright specs before building visual components (TDD)
  - Generate HTML wireframe for user approval before component implementation
skills:
  primary: ["/implementation", "/debug_tool"]
  secondary: ["/explore", "/precommit"]
  evaluation: ["/reviewer", "/evaluate"]
invokes:
  for_api_contracts: ["backend"]
  for_evaluation: ["security", "qa", "production"]
cost_guidance:
  cheap: ["lint", "format", "component-scaffolding"]
  mid: ["component-building", "test-writing", "styling"]
  expensive: ["performance-review", "accessibility-audit", "architecture-decision"]
knowledge: "roles/frontend/knowledge/_synthesis.md"
health_check:
  freshness_threshold_days: 90
  required_sections: ["advisory", "anti_patterns", "quality_checks", "bug_fixes"]
---

## Advisory Context

You are working on a frontend project. Apply these principles:

- **UX Laws are mandatory.** Read `skills/reviewer/references/ux-laws.md` before building any visual component. Apply Fitts's, Hick's, Jakob's, and Proximity laws. They produce testable requirements verified by Playwright.
- **Playwright TDD for visual components.** Write the `.spec.ts` first, then generate an HTML wireframe for user approval, then build the component to pass the spec.
- Never compute data synchronously on page load — defer, lazy-load, or use Web Workers for tasks >50ms
- Lazy-load below-fold components but NEVER lazy-load the LCP image
- Code-split per route; don't bundle the entire app
- Validate Core Web Vitals: LCP < 2.5s, INP < 200ms, CLS < 0.1
- Server state and client state are different — use separate tools
- Use URL state for shareable views (search params)
- Local state > global state unless truly shared across components

## Cross-Platform & PWA

- PWA: add manifest.json, service worker, offline support → installable on any device
- Capacitor: wrap existing frontend in native shell → deploy to iOS/Android app stores
- React Native Web: share components between web + mobile via react-native-web
- Responsive ≠ mobile app: responsive layout is step 1, Capacitor wrapper is step 2
- Test on real mobile devices — emulators miss touch/scroll/performance issues

## Anti-Patterns (flag these)

- Heavy computation in component mount/render (useEffect with sync work)
- `document.write()`, `eval()`, `innerHTML` with user data — XSS vectors
- Images without explicit width/height — causes layout shift (CLS)
- All data fetched on page load instead of on-demand/lazy
- Lazy-loading the LCP image — delays the most important paint
- Global state for everything (use local state when possible)
- Missing error boundaries — one component crash kills the whole app
- No loading/skeleton states — users see blank page during fetch
- **Fitts's Law:** touch target < 44x44px, destructive button same size/position as primary action
- **Hick's Law:** dropdown > 15 items without search, nav > 7 ungrouped items, form > 6 fields without progressive disclosure
- **Jakob's Law:** modal without Escape/overlay close, custom scroll overriding native, non-standard form patterns
- **Proximity:** uniform spacing with no visual grouping, label > 12px from its input, related actions separated by unrelated content
- Visual component built without Playwright spec first (TDD violation)
- Component implemented without user-approved HTML wireframe

## UX Laws (mandatory for every visual component)

Read `skills/reviewer/references/ux-laws.md` when building or reviewing any visual component. These laws produce measurable, testable requirements — not subjective opinions.

| Law | Core rule | Verify with |
|-----|-----------|-------------|
| Fitts's | Targets >= 44x44px, primary CTA largest | Playwright `boundingBox()` |
| Hick's | Max 7 nav items, search on 10+ dropdown items | Playwright option count |
| Jakob's | Standard patterns (Escape closes modal, logo → home) | Playwright keyboard/click |
| Proximity | Related items grouped (< 12px), groups separated (24px+) | Playwright `boundingBox()` gap |

## Quality Checks

- [ ] No heavy computation on page load or component mount
- [ ] Images have width/height and use modern formats (WebP/AVIF)
- [ ] Below-fold content is lazy-loaded
- [ ] LCP image is NOT lazy-loaded
- [ ] No XSS vectors (innerHTML, eval, dangerouslySetInnerHTML without sanitization)
- [ ] Error boundaries wrap major sections
- [ ] Loading and error states for all async operations
- [ ] Responsive layout works on mobile, tablet, desktop
- [ ] **Fitts's Law:** all interactive targets >= 44x44px, destructive actions small and away from primary
- [ ] **Hick's Law:** dropdowns with 10+ items have search, nav has <= 7 top-level items
- [ ] **Jakob's Law:** modals close on Escape + overlay click, standard patterns used
- [ ] **Proximity:** related elements grouped with tight spacing, groups separated with 2-3x gap
- [ ] Playwright spec written BEFORE component implementation
- [ ] HTML wireframe approved by user before building
