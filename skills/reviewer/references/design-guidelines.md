---
source: Vercel design principles, Material Design, Apple HIG, Refactoring UI
type: reference
role: frontend
---

# Design Guidelines for Frontend Implementation

Concrete, measurable rules for visual design. Use these when building components, reviewing UI, or generating HTML wireframes. Every rule here is testable — either by Playwright or by visual inspection.

---

## 1. Spacing System

Use a consistent spacing scale. Never use arbitrary pixel values.

### Scale (base 4px)

| Token | Value | Use for |
|-------|-------|---------|
| `xs` | 4px | Icon-to-text gap, inline element spacing |
| `sm` | 8px | Related items within a group, button icon padding |
| `md` | 16px | Card internal padding, form field gap within a group |
| `lg` | 24px | Section gap, card grid gap, between form groups |
| `xl` | 32px | Page section separation |
| `2xl` | 48px | Major section breaks, hero-to-content gap |
| `3xl` | 64px | Page top/bottom padding |

### Rules

- **Internal padding:** cards 16-24px, modals 24-32px, page sections 32-48px
- **Gap between related items:** 8-12px (form fields in same group, buttons in a group)
- **Gap between groups:** 24-32px (form sections, card groups)
- **Never mix spacing values in the same context.** If card padding is 16px, all cards use 16px
- **Vertical rhythm:** consistent line-height multiplied by spacing scale

### Anti-Patterns

- Magic numbers (13px, 17px, 23px) instead of scale values
- Different padding on each side of a card without justification
- No spacing between form fields (elements touching)
- Inconsistent gap sizes within the same list/grid

---

## 2. Typography

### Hierarchy (max 4 levels visible at once)

| Level | Use for | Size range | Weight |
|-------|---------|------------|--------|
| Display | Hero, landing page headline | 36-60px | 700-800 |
| Heading | Section titles, page headers | 20-32px | 600-700 |
| Subheading | Card titles, group labels | 16-20px | 500-600 |
| Body | Content, descriptions, form labels | 14-16px | 400 |
| Caption | Help text, metadata, timestamps | 12-14px | 400 |

### Rules

- **Body text:** min 14px (16px preferred). Never below 14px for readable content
- **Line height:** 1.4-1.6 for body text, 1.1-1.3 for headings
- **Line length:** 45-75 characters per line (measure with `max-width: 65ch`)
- **Font stack:** system fonts first for performance (`-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`)
- **Max 2 font families** per project (one for headings, one for body — or one for both)
- **Weight contrast:** use weight differences (400 vs 700) more than size differences for emphasis
- **Truncation:** dynamic text gets `overflow: hidden; text-overflow: ellipsis; white-space: nowrap` or `line-clamp`

### Anti-Patterns

- More than 4 visually distinct text sizes on one screen
- Body text below 14px
- Line length > 80 characters (hard to read)
- All-caps for more than 3 words (unreadable)
- Multiple font families with no clear purpose

---

## 3. Color

### System

- **Primary:** 1 brand color + 1-2 shades (hover/active)
- **Neutral:** gray scale for text, backgrounds, borders (min 5 shades: 50, 100, 200, 500, 900)
- **Semantic:** green=success, red=error/destructive, yellow=warning, blue=info
- **Background:** max 2 background colors per page (e.g., white content + gray-50 sidebar)

### Rules

- **Text contrast:** WCAG AA minimum (4.5:1 for body, 3:1 for large text). See `skills/reviewer/accessibility.md`
- **Don't communicate with color alone.** Add icons, text, or patterns alongside color (colorblind users)
- **Hover/focus states:** darken by 10-15% or add border/shadow — never just change text color
- **Disabled state:** 40-50% opacity of normal state, not a completely different color
- **Dark mode:** if supported, define color tokens, not hardcoded hex values
- **Max 3 colors** in a single component (background, text, accent). More = visual noise

### Anti-Patterns

- Hardcoded hex values scattered across components instead of theme tokens
- Red/green as only differentiator (excludes colorblind users)
- Low-contrast text (light gray on white, dark gray on black)
- Neon/saturated colors for large surfaces (eye strain)
- Different shades of the same color with no defined palette (brand blue is #2563EB here but #3B82F6 there)

---

## 4. Visual Hierarchy

### Rules

- **One primary action per view.** The most important action is visually dominant (size, color, position)
- **Z-pattern for landing pages:** top-left logo → top-right CTA → bottom-left content → bottom-right action
- **F-pattern for content pages:** users scan left-to-right, then down the left edge
- **Visual weight order:** filled button > outlined button > text button > link
- **Whitespace is structure.** Empty space around an element elevates its importance
- **Card elevation:** use shadow or border to lift content from background, not both
- **Icon consistency:** all icons same style (outlined OR filled, not mixed), same stroke width, same size per context

### Component Visual Weight

| Element | Background | Border | Shadow | Use for |
|---------|-----------|--------|--------|---------|
| Primary button | Filled (brand color) | None | Optional subtle | Main action per section |
| Secondary button | White/transparent | 1px solid | None | Alternative action |
| Tertiary/ghost button | None | None | None | Cancel, back, low-priority |
| Destructive button | Red filled or red text | Optional | None | Delete, remove — smaller than primary |
| Card | White | 1px solid gray-200 OR shadow-sm | Not both | Content container |
| Input | White | 1px solid gray-300 | None (inset shadow optional) | Form fields |
| Modal | White | None | shadow-xl | Overlay dialog |

### Anti-Patterns

- Multiple primary-styled buttons in one section (competing for attention)
- Cards with both border AND shadow (double elevation = visual noise)
- No clear visual hierarchy — everything same size, weight, color
- Important actions hidden in text links while unimportant ones are prominent buttons

---

## 5. Layout

### Rules

- **Max content width:** 1280px for full layouts, 768px for text-heavy content, 480px for forms
- **Grid:** 12-column on desktop, 4-column on mobile. Use CSS Grid or Flexbox
- **Sidebar width:** 240-280px fixed on desktop, drawer on mobile
- **Consistent alignment:** left-align text (LTR), center-align hero/CTA sections only
- **Responsive breakpoints:** 640px (mobile), 768px (tablet), 1024px (desktop), 1280px (wide)
- **Mobile first:** design for 375px width, then add complexity for wider screens
- **Touch spacing on mobile:** min 8px gap between interactive elements to prevent misclicks

### Anti-Patterns

- Content wider than viewport (horizontal scroll)
- Sidebar visible on mobile (takes too much space)
- Fixed elements covering content on mobile (sticky headers > 60px tall)
- No max-width on text content (lines stretching across 1920px)
- Centering everything (misaligned, hard to scan)

---

## 6. Animation and Transitions

### Rules

- **Duration:** 150-300ms for UI transitions (hover, toggle, expand). 300-500ms for page transitions. Never > 500ms
- **Easing:** `ease-out` for entrances, `ease-in` for exits, `ease-in-out` for movement
- **Purpose:** animation must communicate state change (expand, collapse, appear, disappear). Never decorative
- **Reduce motion:** respect `prefers-reduced-motion` — disable animations or reduce to opacity-only
- **Loading:** use skeleton screens (gray boxes matching content shape), not spinners, for content areas

### Anti-Patterns

- Animation > 500ms (feels sluggish)
- Bouncing/elastic animations on UI controls (distracting)
- Animation that blocks interaction (user waits for animation to finish)
- No `prefers-reduced-motion` support
- Spinner for content loading instead of skeleton

---

## How This File is Used

1. **During `/implementation frontend.md`:** check components against these rules before marking slab complete
2. **During `/reviewer design.md`:** systematic audit against each section
3. **During HTML wireframe generation:** apply these rules to the wireframe itself
4. **Playwright tests:** verify measurable rules (spacing, sizes, contrast ratios)
