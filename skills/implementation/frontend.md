# Frontend Implementation

Implement UI components, layouts, state management, API calls, styling, and routing using TDD.

## Inputs

Read from upstream docs before writing any code:
- **Wireframes** (`requirements/wireframes/`): If HTML wireframes exist, read them. Implement to match the layout structure. The wireframe's HTML comments (`<!-- Navigation Bar -->`, etc.) map to your component boundaries.
- **Component architecture** (from architecture doc): If atomic design, feature-based, or another pattern was decided, follow it. Structure your files and components accordingly.
- **Styling approach** (from architecture doc): Use the specified approach (Tailwind, CSS modules, styled-components, etc.). Do not introduce a different one.
- **State management** (from architecture doc): Use the specified pattern (Redux, Zustand, Context, etc.).
- **Design system** (from requirements doc): If a component library was specified (shadcn/ui, Material UI, etc.), use it. If "custom" was specified, build components from scratch following the stated visual style.
- **Accessibility target** (from requirements doc): If WCAG AA/AAA was specified, enforce it — aria labels, keyboard navigation, focus management, contrast ratios.

If none of these exist, use sensible defaults and project conventions.

## TDD Patterns by Framework

| Framework | Test Approach |
|-----------|-------------|
| React/TS | vitest + @testing-library/react. Render, query, assert, interact. |
| Vue | vitest + @vue/test-utils. Mount, find, assert, trigger. |
| Svelte | vitest + @testing-library/svelte. Render, query, assert. |
| Plain JS | vitest or Jest. Unit test functions directly. |

Use the test framework specified in the architecture doc's Testing Architecture section if one was chosen. Otherwise, use the defaults above.

## What to Test at Each Level

- **Component:** Renders correctly, displays right data, handles interactions
- **State:** Reducers/stores produce correct state for each action
- **Integration:** Component + API calls + state updates work together
- **Snapshot:** Visual regression for key components (only if Testing Requirements specify visual regression)
- **Accessibility:** Automated a11y checks (only if Testing Requirements specify accessibility testing)

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

1. **No false success.** Check `response.ok` BEFORE any success toast, state clear, or UI update. Never show "Saved" before confirming the save actually worked.
2. **Core features never conditionally hidden.** Always render with empty state + action link.
3. **Results appear inline.** Don't redirect after an action.
4. **Dynamic text: truncate + overflow-hidden + max-w.** Every element displaying user data or filenames.
5. **Health checks, not availability.** "Connected" badge must verify with a test query.
6. **Error isolation.** One failed API must not blank other components.
7. **File input: validate on BOTH click AND drag-drop.** `<input accept>` only filters the picker dialog — drag-drop bypasses it. Validate in the drop handler too.
8. **User URLs: validate scheme.** `href={userUrl}` allows `javascript:` XSS. Check `/^https?:\/\//` before rendering.
9. **JSON.parse on external data: always try/catch.** Use a `safeJsonParse()` helper with fallback.
10. **Dev workflow note:** Tell user to restart dev server or hard-refresh to see changes.

## TDD Cycle

For each piece of UI logic in the slab:

1. **TEST FIRST** — Write a failing test that describes the expected rendering or interaction
2. **RUN TEST** — Confirm it fails (red)
3. **IMPLEMENT** — Write the minimum component code to make the test pass
4. **RUN TEST** — Confirm it passes (green)
5. **REFACTOR** — Clean up without changing behavior
6. **RUN TEST** — Confirm still green
7. **RESILIENCE CHECK** — Run the 7-item frontend check below. **This step is mandatory.**

## Post-Write Resilience Check (runs after EVERY component write or modify)

**This is not optional.** After writing or modifying ANY component, scan it against all 7 items. Fix violations before moving to the next component.

```
For [component just written/modified]:

[ ] 1. PROMISE.ALL — Does this component load data from multiple endpoints?
      If yes: are they loaded independently with separate try/catch?
      FAIL if: Promise.all groups unrelated fetches

[ ] 2. OVERFLOW — Does this component display dynamic text (user data, API response, filenames)?
      If yes: does every dynamic text element have truncate + overflow-hidden + max-w?
      FAIL if: any dynamic text lacks overflow protection

[ ] 3. EMPTY STATE — Is this a core feature component?
      If yes: does it render when data is empty/null/undefined with an action link?
      FAIL if: component is conditionally hidden ({data && <Component>}) for a primary feature

[ ] 4. INLINE RESULTS — Does this component trigger an action (submit, search, generate)?
      If yes: do results appear in the same view, not a redirect to another page/tab?
      FAIL if: action redirects away from where user triggered it

[ ] 5. SUCCESS MESSAGES — Does this component show a success/done/complete message?
      If yes: does the message appear AFTER the action actually completes (after API response, not before)?
      FAIL if: success shown before the action is confirmed complete

[ ] 6. ERROR ISOLATION — Does this component call APIs?
      If yes: does a failed API call show an error message in THIS component, not blank the page?
      FAIL if: error in one component's data loading affects other components

[ ] 7. HEALTH vs AVAILABILITY — Does this component show connection/status indicators?
      If yes: does it verify with a real test query, not just check if a key/URL exists?
      FAIL if: "Connected" badge shown without verifying the service actually responds
```

**If any item fails:** Fix it immediately before proceeding. Don't accumulate UI debt.

**Report format after check:**
> "Resilience check for [ComponentName]: 7/7 passed" or
> "Resilience check for [ComponentName]: 5/7 — fixing #2 (overflow) and #3 (empty state)"

For guardrails and core principles, see the main `SKILL.md`.
