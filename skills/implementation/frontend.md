# Frontend Implementation
Keywords: UI, components, state, styling, routing, accessibility, React, Vue, Svelte

Implement UI components, layouts, state management, API calls, styling, and routing using TDD.

## Inputs

Read from upstream docs before writing any code:
- **Wireframes** (`requirements/wireframes/`): implement to match layout structure
- **Component architecture, styling, state management, design system, accessibility target**: use what was decided in architecture/requirements docs

## Per-Component Rules (enforced on every component written)

1. **Max 200 lines per component.** If over, split: orchestrator (state + handlers) + presentational sub-components.
2. **No raw fetch() in components.** Use the API client from `api/client.ts`. Every response typed.
3. **No `as unknown as` casts.** If you need a cast, the API client return type is wrong — fix the client.
4. **No silent catches.** Every `catch` must show `toast.error()` or a user-visible message.
5. **Import types from `types/index.ts`.** No inline interface definitions in components.
6. **Every setLoading(true) must have finally { setLoading(false) }.** Otherwise the UI gets stuck forever on error.
7. **Every API response expected as array must guard with Array.isArray().** APIs change shape. Don't trust casts.
8. **Shared state across list items: use per-item map.** `Record<id, data>` not a single variable for expandable cards/panels.
9. **Promise.all: BAD for independent page loads, GOOD for batching loop fetches.** Load unrelated data independently. Use Promise.all ONLY for N fetches of the same type in a loop.
10. **Frontend defaults for backend data.** Any UI depending on a config/discovery endpoint must have hardcoded fallback defaults so it's never completely blank when backend is unreachable.
11. **Second copy-paste = extract.** If you paste a pattern a second time, extract to `components/shared/`.

## Resilience Rules (from real usage)

1. **No false success.** Check `response.ok` BEFORE any success toast, state clear, or UI update.
2. **Core features never conditionally hidden.** Always render with empty state + action link.
3. **Results appear inline.** Don't redirect after an action.
4. **Dynamic text: truncate + overflow-hidden + max-w.** Every element displaying user data or filenames.
5. **Health checks, not availability.** "Connected" badge must verify with a test query.
6. **Error isolation.** One failed API must not blank other components.
7. **File input: validate on BOTH click AND drag-drop.** `<input accept>` only filters the picker dialog — drag-drop bypasses it. Validate in the drop handler too.
8. **User URLs: validate scheme.** `href={userUrl}` allows `javascript:` XSS. Check `/^https?:\/\//` before rendering.
9. **JSON.parse on external data: always try/catch.** Use a `safeJsonParse()` helper with fallback.
10. **Dev workflow note:** Tell user to restart dev server or hard-refresh to see changes.

## Post-Write Resilience Check (mandatory after EVERY component write or modify)

```
For [component just written/modified]:

[ ] 1. PROMISE.ALL — Does this component load data from multiple endpoints?
      If yes: are they loaded independently with separate try/catch?
      FAIL if: Promise.all groups unrelated fetches

[ ] 2. OVERFLOW — Does this component display dynamic text?
      If yes: does every dynamic text element have truncate + overflow-hidden + max-w?
      FAIL if: any dynamic text lacks overflow protection

[ ] 3. EMPTY STATE — Is this a core feature component?
      If yes: does it render when data is empty/null/undefined with an action link?
      FAIL if: component is conditionally hidden for a primary feature

[ ] 4. INLINE RESULTS — Does this component trigger an action?
      If yes: do results appear in the same view, not a redirect?
      FAIL if: action redirects away from where user triggered it

[ ] 5. SUCCESS MESSAGES — Does this component show a success message?
      If yes: does it appear AFTER the action actually completes?
      FAIL if: success shown before confirmed complete

[ ] 6. ERROR ISOLATION — Does this component call APIs?
      If yes: does a failed API call show error in THIS component, not blank the page?
      FAIL if: error in one component affects others

[ ] 7. HEALTH vs AVAILABILITY — Does this component show connection/status indicators?
      If yes: does it verify with a real test query?
      FAIL if: "Connected" shown without verifying service responds
```

**Report:** "Resilience check for [ComponentName]: 7/7 passed" or list failures.

For guardrails and core principles, see the main `SKILL.md`.
