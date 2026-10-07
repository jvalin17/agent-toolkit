---
source: UX research (Fitts, Hick, Nielsen, Gestalt)
type: reference
role: frontend
---

# UX Laws for Frontend Implementation

Apply these laws when building any visual component. They are not suggestions — they are design constraints that affect usability.

---

## 1. Fitts's Law

**The time to reach a target depends on its size and distance.**

Larger, closer targets are faster to click. Small, distant targets cause frustration and errors.

### Rules

- **Buttons and CTAs:** minimum 44x44px touch target (WCAG), 48x48px recommended for mobile
- **Primary actions:** make them the largest clickable element in their section
- **Destructive actions:** keep small and away from primary actions — harder to hit = fewer accidents
- **Form submit buttons:** full-width on mobile, min 120px wide on desktop
- **Navigation links:** generous padding (min 8px vertical, 16px horizontal) — the padding IS the target
- **Icon-only buttons:** min 40x40px with visible hover/focus area, not just the 16px icon
- **Edge/corner targets:** place frequent actions near screen edges (infinite target depth in desktop browsers)
- **Dropdown items:** min 36px row height — don't pack 20 items in 12px rows

### Anti-Patterns (flag these)

- Touch target smaller than 44x44px
- Primary CTA same size as secondary actions
- Destructive button (Delete, Remove) adjacent to and same size as primary action (Save, Submit)
- Icon button with no padding — clickable area is just the icon pixels
- Tiny close/dismiss buttons (< 32x32px)

### Playwright Test Triggers

Test any: `<button>`, `<a>` styled as button, clickable card, icon button, form submit, dropdown item.

```typescript
// Verify minimum touch target size
const button = page.getByRole('button', { name: 'Submit' });
const box = await button.boundingBox();
expect(box.width).toBeGreaterThanOrEqual(44);
expect(box.height).toBeGreaterThanOrEqual(44);
```

---

## 2. Hick's Law

**Decision time increases with the number and complexity of choices.**

More options = slower decisions = higher abandonment. Reduce choices to reduce friction.

### Rules

- **Navigation:** max 7 (+/- 2) top-level items. Group the rest under clear categories
- **Dropdowns:** if > 10 items, add search/filter. If > 25, use a searchable combobox instead
- **Forms:** show only required fields first. Progressive disclosure for optional fields
- **Action menus:** max 5-7 items visible. Group related actions with dividers
- **Onboarding:** one choice per step, not a wall of options
- **Settings pages:** group into categories with max 5-7 visible per group
- **Modals:** max 2 actions (primary + cancel). 3 only if the third is clearly secondary (e.g., "Don't show again")

### Anti-Patterns (flag these)

- Dropdown with > 15 items and no search
- Navigation with > 7 ungrouped top-level items
- Form showing > 6 fields at once without progressive disclosure
- Modal with > 3 action buttons
- Settings page with > 10 ungrouped options visible at once
- Onboarding step with > 3 choices

### Playwright Test Triggers

Test any: `<select>`, dropdown menu, navigation bar, form, modal actions, settings page.

```typescript
// Verify dropdown with many items has search
const options = await page.getByRole('option').count();
if (options > 10) {
  await expect(page.getByRole('searchbox')).toBeVisible();
}
```

---

## 3. Jakob's Law

**Users spend most of their time on OTHER sites. They expect yours to work the same way.**

Don't reinvent standard patterns. Use conventions users already know.

### Rules

- **Logo:** top-left, links to home
- **Search:** top-right or top-center, magnifying glass icon, Enter to submit
- **Navigation:** horizontal top bar (desktop), hamburger menu (mobile)
- **Shopping cart:** top-right with item count badge
- **Forms:** labels above inputs, submit button at bottom-right (LTR) or full-width
- **Links:** underlined or visually distinct from body text. Blue for unvisited is still expected
- **Back button:** top-left, arrow icon, labeled "Back" — not a custom gesture
- **Loading:** spinner or skeleton in place of content, not a separate page
- **Error messages:** red, near the field that caused them, not just a banner at top
- **Modals:** close with X (top-right), Escape key, and clicking overlay
- **Tables:** sortable column headers, row hover highlight, pagination at bottom
- **Toast/notifications:** top-right or bottom-right, auto-dismiss after 3-5s for success, persist for errors

### Anti-Patterns (flag these)

- Custom scroll behavior that overrides native scroll
- Non-standard form submit patterns (double-click to save, swipe to submit)
- Navigation hidden behind gestures users won't discover
- Modal that can't be closed with Escape or overlay click
- Error messages far from the field that caused them
- Custom select/dropdown that doesn't support keyboard navigation
- Infinite scroll without a "Back to top" button or scroll position memory

### Playwright Test Triggers

Test any: modal, form submission, navigation, search, link behavior.

```typescript
// Verify modal closes on Escape
await page.getByRole('dialog').waitFor();
await page.keyboard.press('Escape');
await expect(page.getByRole('dialog')).not.toBeVisible();
```

---

## 4. Law of Proximity (Gestalt)

**Elements near each other are perceived as related. Distance implies separation.**

Group related items. Separate unrelated items. Spacing IS information.

### Rules

- **Related form fields:** group with shared label and reduce internal spacing (8-12px gap between related fields, 24-32px between groups)
- **Card content:** consistent internal padding (16-24px). Items within a card are related — space between cards (16-24px gap) separates unrelated items
- **Button groups:** 8px gap between related actions (Save + Cancel), 24px+ between unrelated actions
- **Labels and inputs:** label directly above or beside its input with 4-8px gap — never far apart
- **Lists:** related items share tight spacing (4-8px). Section breaks use 2-3x the item spacing
- **Dashboard widgets:** 16-24px gap between cards. Cards that relate (e.g., chart + its filters) are adjacent
- **Inline help/descriptions:** immediately below the element they describe, 4px gap, smaller/lighter text

### Anti-Patterns (flag these)

- Uniform spacing everywhere — no visual grouping (everything 16px apart)
- Label far from its input (> 12px gap)
- Related actions separated by unrelated content
- Form fields with no visual grouping — just a flat list
- Help text or description far from the element it describes
- Inconsistent spacing within the same component (8px here, 20px there, 12px elsewhere)

### Playwright Test Triggers

Test any: form layout, card grid, button groups, label-input pairs.

```typescript
// Verify label is close to its input (proximity)
const label = page.getByText('Email');
const input = page.getByRole('textbox', { name: 'Email' });
const labelBox = await label.boundingBox();
const inputBox = await input.boundingBox();
const gap = inputBox.y - (labelBox.y + labelBox.height);
expect(gap).toBeLessThanOrEqual(12);
```

---

## How to Use This File

This file is loaded by the frontend role. Its anti-patterns are enforced in `roles/frontend/role.md` quality checks. When building or reviewing visual components:

1. **During implementation:** check each component against the 4 laws before marking the slab complete
2. **During review:** `/reviewer design.md` runs these checks with file:line evidence
3. **During testing:** Playwright specs verify measurable rules (target sizes, option counts, spacing)
