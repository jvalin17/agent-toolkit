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

## Quality Checks

- [ ] No heavy computation on page load or component mount
- [ ] Images have width/height and use modern formats (WebP/AVIF)
- [ ] Below-fold content is lazy-loaded
- [ ] LCP image is NOT lazy-loaded
- [ ] No XSS vectors (innerHTML, eval, dangerouslySetInnerHTML without sanitization)
- [ ] Error boundaries wrap major sections
- [ ] Loading and error states for all async operations
- [ ] Responsive layout works on mobile, tablet, desktop
