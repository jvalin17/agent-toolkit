# Design Review
Keywords: design, taste, spacing, typography, color, hierarchy, UX laws, Fitts, Hick, Jakob, proximity, visual quality

For guardrails and principles, see main SKILL.md.

## Prerequisites

Read these before reviewing:
- `skills/reviewer/references/ux-laws.md` — Fitts's, Hick's, Jakob's, Proximity laws
- `skills/reviewer/references/design-guidelines.md` — spacing, typography, color, hierarchy, layout, animation

## Step 1: UX Laws Compliance

Check every interactive and visual component against the 4 UX laws.

### Fitts's Law (target sizes and distances)

For each `<button>`, `<a>`, clickable element, and form control:
- [ ] Touch target >= 44x44px (width AND height including padding)
- [ ] Primary CTA is the largest interactive element in its section
- [ ] Destructive actions (delete, remove) are smaller than primary actions
- [ ] Destructive actions are positioned away from primary actions (not adjacent)
- [ ] Icon-only buttons have padding making total area >= 40x40px

Flag with file:line. Measure from CSS/Tailwind classes or computed styles.

### Hick's Law (choice overload)

For each navigation, dropdown, form, and settings view:
- [ ] Top-level navigation has <= 7 items
- [ ] Dropdowns with > 10 options have search/filter
- [ ] Forms show <= 6 fields at once (progressive disclosure for rest)
- [ ] Modals have <= 3 action buttons
- [ ] Settings pages group options into categories of <= 7 items

Count items in the code. Flag violations with element count and file:line.

### Jakob's Law (convention compliance)

For each modal, form, navigation, and search component:
- [ ] Modals close on Escape key press
- [ ] Modals close on overlay/backdrop click
- [ ] Logo links to home page
- [ ] Search has magnifying glass icon and submits on Enter
- [ ] Form submit button is at the bottom of the form
- [ ] Error messages are near the field that caused them
- [ ] Links are visually distinct from body text
- [ ] Custom components support keyboard navigation (Tab, Enter, Arrow keys)

### Proximity (spatial grouping)

For each form, card, button group, and list:
- [ ] Related form fields are grouped with shared label and tight spacing (8-12px)
- [ ] Groups are separated with larger spacing (24-32px)
- [ ] Labels are within 12px of their inputs
- [ ] Button groups use 8px gap between related actions
- [ ] Help text is immediately below its element (4px gap)
- [ ] Spacing is consistent within the same component

## Step 2: Visual Design Quality

### Spacing Consistency

Scan all components for spacing values (padding, margin, gap):
- [ ] Uses a consistent scale (multiples of 4px or 8px)
- [ ] No magic numbers (13px, 17px, 23px, etc.)
- [ ] Same padding used for all cards of the same type
- [ ] Vertical rhythm maintained (consistent gap between sections)

### Typography Hierarchy

Scan all text elements:
- [ ] Max 4 visually distinct text levels per screen
- [ ] Body text >= 14px
- [ ] Line length <= 75 characters (`max-width` on text containers)
- [ ] Max 2 font families
- [ ] Truncation on all dynamic text (`text-overflow: ellipsis` or `line-clamp`)

### Color Usage

Scan stylesheets and component styles:
- [ ] Colors use theme tokens, not hardcoded hex values
- [ ] Max 3 colors per component (background, text, accent)
- [ ] Semantic colors used correctly (red=error, green=success)
- [ ] Color is not the only differentiator (icons/text alongside)
- [ ] Hover/focus states have visible change (not just cursor)
- [ ] Text contrast meets WCAG AA (4.5:1 body, 3:1 large)

### Visual Hierarchy

For each page/view:
- [ ] One primary action is visually dominant
- [ ] Visual weight order: filled > outlined > text > link
- [ ] Cards use border OR shadow, not both
- [ ] Consistent icon style (all outlined or all filled)
- [ ] Whitespace used intentionally to elevate important elements

### Layout

- [ ] Max content width set (no full-viewport text lines)
- [ ] Responsive breakpoints implemented
- [ ] Sidebar collapses to drawer on mobile
- [ ] No horizontal scroll
- [ ] Touch spacing on mobile (8px+ gap between interactive elements)

### Animation

- [ ] Transition duration 150-300ms for UI, 300-500ms for pages
- [ ] `prefers-reduced-motion` respected
- [ ] No decorative animations blocking interaction
- [ ] Skeleton screens used for content loading (not spinners)

## Step 3: Playwright Coverage Check

For each visual component reviewed:
- [ ] Playwright `.spec.ts` file exists
- [ ] Spec tests touch target sizes (Fitts's)
- [ ] Spec tests dropdown item counts (Hick's)
- [ ] Spec tests keyboard interactions (Jakob's)
- [ ] Spec tests spacing/proximity between elements (Proximity)
- [ ] Spec was written BEFORE the component (check git history: spec commit before component commit)

Flag components without Playwright specs. Flag specs written after the component.

## Output Format

> **Design Review for [target]**
>
> ### UX Laws
> | # | Law | Severity | File:Line | Issue | Fix |
> |---|-----|----------|-----------|-------|-----|
> | 1 | Fitts's | High | Button.tsx:12 | Touch target 32x28px | Add `min-h-[44px] min-w-[44px]` padding |
> | 2 | Hick's | Medium | Nav.tsx:8 | 12 top-level nav items | Group into 5 categories with submenus |
> | 3 | Jakob's | High | Modal.tsx:45 | No Escape key handler | Add `onKeyDown` Escape listener |
> | 4 | Proximity | Medium | Form.tsx:20 | Label 24px from input | Reduce gap to `gap-1` (4px) |
>
> ### Visual Design
> | # | Category | Severity | File:Line | Issue | Fix |
> |---|----------|----------|-----------|-------|-----|
> | 1 | Spacing | Medium | Card.tsx:8 | Mixed padding (12px, 18px, 16px) | Standardize to 16px |
> | 2 | Typography | Low | Page.tsx:34 | Line length ~95 chars | Add `max-w-prose` |
>
> ### Playwright Coverage
> | Component | Spec exists | UX law tests | Written first |
> |-----------|-------------|--------------|---------------|
> | Button.tsx | Yes | Fitts ✓, Jakob ✓ | Yes |
> | Modal.tsx | No | — | — |
>
> **Summary:** [count by severity, UX law compliance %, Playwright coverage %]
