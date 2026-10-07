# Frontend Implementation
Keywords: UI, components, state, styling, routing, accessibility, React, Vue, Svelte, Playwright, UX laws, design

Implement UI components, layouts, state management, API calls, styling, and routing using TDD. Visual components use Playwright-first TDD with user-approved wireframes.

## Inputs

Read from upstream docs before writing any code:
- **Wireframes** (`requirements/wireframes/`): implement to match layout structure
- **Component architecture, styling, state management, design system, accessibility target**: use what was decided in architecture/requirements docs
- **UX Laws** (`skills/reviewer/references/ux-laws.md`): Fitts's, Hick's, Jakob's, Proximity — apply to every visual component
- **Design Guidelines** (`skills/reviewer/references/design-guidelines.md`): spacing, typography, color, hierarchy — apply to all styling decisions

## Visual Component TDD Cycle (mandatory for buttons, forms, modals, dropdowns, navs, cards, any CSS-styled component)

Every visual component follows this 3-step cycle BEFORE implementation. Do not skip any step.

### Step 1: Write Playwright Spec First

Create `tests/e2e/<component-name>.spec.ts` BEFORE writing the component. The spec defines what the component must do, based on UX laws and design guidelines.

**Required test categories for visual components:**

```typescript
// 1. FITTS'S LAW — target sizes
test('interactive targets meet minimum size', async ({ page }) => {
  const button = page.getByRole('button', { name: 'Submit' });
  const box = await button.boundingBox();
  expect(box!.width).toBeGreaterThanOrEqual(44);
  expect(box!.height).toBeGreaterThanOrEqual(44);
});

// 2. HICK'S LAW — choice overload (for dropdowns, navs, menus)
test('dropdown with many items has search', async ({ page }) => {
  await page.getByRole('combobox').click();
  const options = await page.getByRole('option').count();
  if (options > 10) {
    await expect(page.getByPlaceholder(/search|filter/i)).toBeVisible();
  }
});

// 3. JAKOB'S LAW — standard interactions
test('modal closes on Escape', async ({ page }) => {
  // trigger modal open
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).not.toBeVisible();
});

test('modal closes on overlay click', async ({ page }) => {
  // trigger modal open
  await page.locator('[data-testid="modal-overlay"]').click({ position: { x: 0, y: 0 } });
  await expect(page.getByRole('dialog')).not.toBeVisible();
});

// 4. PROXIMITY — spacing between elements
test('label is close to its input', async ({ page }) => {
  const label = page.getByText('Email');
  const input = page.getByRole('textbox', { name: 'Email' });
  const labelBox = await label.boundingBox();
  const inputBox = await input.boundingBox();
  const gap = inputBox!.y - (labelBox!.y + labelBox!.height);
  expect(gap).toBeLessThanOrEqual(12);
});

// 5. VISUAL — rendering, styles, responsiveness
test('component renders correctly', async ({ page }) => {
  await expect(page.getByRole('button', { name: 'Submit' })).toBeVisible();
});

// 6. INTERACTION — click, hover, focus, keyboard
test('button shows focus ring on Tab', async ({ page }) => {
  await page.keyboard.press('Tab');
  const button = page.getByRole('button', { name: 'Submit' });
  await expect(button).toBeFocused();
});
```

**Which UX law tests to include per component type:**

| Component | Fitts's (sizes) | Hick's (choices) | Jakob's (conventions) | Proximity (spacing) |
|-----------|:---:|:---:|:---:|:---:|
| Button | Yes | — | Yes (focus, keyboard) | — |
| Form | Yes (submit) | Yes (field count) | Yes (submit position, error placement) | Yes (label-input gap) |
| Modal | Yes (close button) | Yes (action count) | Yes (Escape, overlay close) | Yes (internal spacing) |
| Dropdown/Select | Yes (option height) | Yes (option count, search) | Yes (keyboard nav) | Yes (option spacing) |
| Navigation | Yes (link targets) | Yes (item count) | Yes (logo → home) | Yes (item grouping) |
| Card | Yes (clickable area) | — | — | Yes (internal padding) |
| Table | Yes (row click area) | — | Yes (sortable headers) | Yes (cell padding) |

### Step 2: Generate HTML Wireframe for Approval

After writing the Playwright spec, generate a self-contained HTML wireframe in `requirements/wireframes/<component-name>.html`. This is the user's chance to approve the design BEFORE you build it.

**Wireframe requirements:**
- Self-contained single HTML file (inline CSS, no external deps)
- Gray-box style (no brand colors — gray backgrounds, black text, blue links)
- Accurate layout, spacing, and proportions matching design guidelines
- Annotations as HTML comments: `<!-- Fitts: 48x48px touch target -->`, `<!-- Hick: 5 nav items -->`
- Responsive — works at 375px and 1280px
- Interactive where relevant (dropdown opens, modal triggers)

**Present to user:**
> Here's the wireframe for [ComponentName]. Open `requirements/wireframes/<component-name>.html` in your browser.
> Does this layout and interaction model look right? I'll build to match this exactly.

**Wait for approval.** If user requests changes, update wireframe and re-present. Do NOT proceed to implementation without approval.

### Step 3: Build Component to Pass Spec

Now implement the component. It must:
1. Pass all Playwright tests from Step 1
2. Match the approved wireframe from Step 2
3. Follow per-component rules (below)
4. Pass the post-write resilience check
5. Pass the post-write UX laws check (below)

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

## Post-Write UX Laws Check (mandatory after EVERY visual component write or modify)

```
For [component just written/modified]:

[ ] 1. FITTS'S — Are all interactive targets >= 44x44px?
      Check: button sizes, link padding, icon button areas
      FAIL if: any clickable element < 44x44px total area
      FAIL if: destructive action same size and adjacent to primary action

[ ] 2. HICK'S — Are choices minimized?
      Check: dropdown option count, nav item count, form field count, modal button count
      FAIL if: dropdown > 10 items without search
      FAIL if: nav > 7 ungrouped items
      FAIL if: form > 6 visible fields without progressive disclosure

[ ] 3. JAKOB'S — Are standard patterns used?
      Check: modal close (Escape + overlay), keyboard nav, form submit position
      FAIL if: modal missing Escape/overlay close
      FAIL if: custom widget doesn't support keyboard

[ ] 4. PROXIMITY — Are related elements grouped?
      Check: label-input gap, button group gap, section spacing
      FAIL if: label > 12px from its input
      FAIL if: uniform spacing with no grouping
      FAIL if: related actions separated by unrelated content
```

**Report:** "UX Laws check for [ComponentName]: 4/4 passed" or list failures.

## Post-Write Design Check (mandatory after EVERY visual component write or modify)

```
For [component just written/modified]:

[ ] 1. SPACING — Uses scale values (4/8/16/24/32px), no magic numbers
[ ] 2. TYPOGRAPHY — Body >= 14px, max 4 text levels, line-length <= 75ch
[ ] 3. COLOR — Theme tokens used, not hardcoded hex, max 3 colors per component
[ ] 4. HIERARCHY — One primary action dominant, visual weight order correct
[ ] 5. PLAYWRIGHT — Spec file exists and was written BEFORE this component
[ ] 6. WIREFRAME — User approved the HTML wireframe before implementation
```

**Report:** "Design check for [ComponentName]: 6/6 passed" or list failures.

## Playwright Integration Test Rules

Visual components must have Playwright integration tests alongside unit tests. These are not optional.

### When to Write Playwright Tests

Write a Playwright `.spec.ts` for any component that:
- Renders a button, link, or clickable element
- Contains a form, dropdown, or select
- Uses CSS for layout, spacing, or visual styling
- Has hover, focus, or keyboard interactions
- Displays dynamic content that could overflow
- Opens/closes modals, drawers, or popups

### Playwright Test File Location

```
tests/
  e2e/
    <component-name>.spec.ts     # Playwright integration tests
  unit/
    <component-name>.test.ts     # Unit tests (logic, state)
```

### Running Playwright Tests

After building a visual component:
```bash
npx playwright test tests/e2e/<component-name>.spec.ts
```

Before committing any frontend slab:
```bash
npx playwright test  # Run all integration tests
```

**Precommit gate:** frontend changes without passing Playwright tests are flagged.

For guardrails and core principles, see the main `SKILL.md`.
