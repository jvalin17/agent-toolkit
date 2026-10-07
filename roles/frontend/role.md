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

These laws produce measurable, testable requirements — not subjective opinions. For deep-dive examples and Playwright snippets, see `skills/reviewer/references/ux-laws.md`.

### Fitts's Law — target size and distance

- Buttons and CTAs: min 44x44px touch target, 48x48px on mobile
- Primary action: largest clickable element in its section
- Destructive actions (Delete, Remove): smaller than primary, positioned away from it
- Icon-only buttons: min 40x40px including padding
- Dropdown items: min 36px row height
- Navigation links: generous padding (min 8px vertical, 16px horizontal)

### Hick's Law — reduce choices

- Navigation: max 7 top-level items, group the rest
- Dropdowns: search/filter if > 10 items, searchable combobox if > 25
- Forms: max 6 visible fields, progressive disclosure for the rest
- Modals: max 2 actions (primary + cancel), 3 only if third is clearly secondary
- Settings: group into categories, max 7 visible per group

### Jakob's Law — use familiar patterns

- Logo: top-left, links to home
- Search: top area, magnifying glass icon, Enter to submit
- Modals: close with X (top-right), Escape key, and overlay click
- Forms: labels above inputs, submit at bottom, errors near the field (red)
- Links: visually distinct from body text
- Loading: skeleton screens in place of content, not a separate page
- Tables: sortable headers, row hover, pagination at bottom
- Toasts: top-right or bottom-right, auto-dismiss 3-5s for success, persist for errors

### Law of Proximity — spacing is information

- Related form fields: 8-12px gap, shared group label
- Between groups: 24-32px gap (2-3x the within-group gap)
- Labels to inputs: max 4-8px gap, directly above or beside
- Button groups: 8px between related actions (Save + Cancel)
- Card internal padding: 16-24px consistent
- Card-to-card gap: 16-24px
- Help text: immediately below its element, 4px gap

## Design Guidelines (apply to all visual components)

For full reference, see `skills/reviewer/references/design-guidelines.md`.

### Spacing scale (base 4px)

`4 | 8 | 16 | 24 | 32 | 48 | 64` — never use arbitrary values (13px, 17px, 23px)

### Typography

- Body text: min 14px (16px preferred), line-height 1.4-1.6
- Max 4 visually distinct text levels per screen
- Line length: 45-75 characters (`max-width: 65ch`)
- Max 2 font families, use weight contrast (400 vs 700) for emphasis
- Truncate all dynamic text: `overflow: hidden; text-overflow: ellipsis`

### Color

- 1 brand color + neutral gray scale (min 5 shades) + semantic (red/green/yellow/blue)
- Max 3 colors per component (background, text, accent)
- Never use color alone to communicate (add icons/text for colorblind users)
- Use theme tokens, not hardcoded hex values
- Hover/focus: darken 10-15% or add border/shadow

### Visual hierarchy

- One primary action per view — visually dominant (size, color, position)
- Visual weight: filled button > outlined > text button > link
- Cards: border OR shadow, not both
- All icons same style (outlined OR filled, not mixed)

### Layout

- Max content width: 1280px layouts, 768px text-heavy, 480px forms
- Responsive breakpoints: 640px / 768px / 1024px / 1280px
- Sidebar: 240-280px fixed desktop, drawer on mobile

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
