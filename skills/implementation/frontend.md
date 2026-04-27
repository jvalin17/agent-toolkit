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

## Frontend Resilience Rules (from real usage — these prevent UI breaking)

1. **Never use Promise.all for independent data loading.** Load each data source independently. One failing endpoint must not blank out the entire page. Use individual try/catch per fetch.
2. **All dynamic text must handle overflow.** Any text from user data or API responses: `truncate` + `overflow-hidden` + `max-w`. Test with long strings like "Senior_Backend_Engineer_Resume_2026-04-27.pdf".
3. **Core features must never be conditionally hidden.** Always render with empty state + action link. Never `{data && <Component>}` for primary features — show the component with "No data yet — [action to get data]".
4. **Results appear where the action was triggered.** Don't redirect to another tab/page after an action. Show results inline.
5. **No false success messages.** Never show "Done!" or "Success!" for actions that haven't completed. Show "In progress..." or "Confirm when complete."
6. **Dev workflow note:** After modifying frontend code, tell user: "Restart dev server or hard-refresh browser to see changes."
7. **Health checks, not just availability checks.** If displaying "API connected" or provider status, verify with a test query — not just "key exists."

## Checklist Per Block

- [ ] Component renders without errors
- [ ] Props are reflected in output
- [ ] User interactions trigger correct callbacks
- [ ] Loading/error/empty states handled (independently per data source)
- [ ] Dynamic text has overflow protection
- [ ] Core features visible even when empty
- [ ] No Promise.all for display data from multiple endpoints
- [ ] Accessibility level matches requirements
- [ ] Component follows the specified architecture pattern
- [ ] Styling uses the specified approach
- [ ] Provider wrappers included in test setup

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
