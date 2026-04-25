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

## Checklist Per Block

- [ ] Component renders without errors
- [ ] Props are reflected in output
- [ ] User interactions trigger correct callbacks
- [ ] Loading/error/empty states handled
- [ ] Accessibility level matches requirements (WCAG AA/AAA/basic)
- [ ] Component follows the specified architecture pattern (atomic/feature-based/flat)
- [ ] Styling uses the specified approach
- [ ] Provider wrappers included in test setup (check what context the component needs)

## TDD Cycle

For each piece of UI logic in the slab:

1. **TEST FIRST** — Write a failing test that describes the expected rendering or interaction
2. **RUN TEST** — Confirm it fails (red)
3. **IMPLEMENT** — Write the minimum component code to make the test pass
4. **RUN TEST** — Confirm it passes (green)
5. **REFACTOR** — Clean up without changing behavior
6. **RUN TEST** — Confirm still green

For guardrails and core principles, see the main `SKILL.md`.
