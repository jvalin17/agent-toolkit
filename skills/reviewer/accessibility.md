# Accessibility Review
Keywords: a11y, font, contrast, keyboard, screen reader, ARIA, WCAG, focus, tab order

For guardrails and principles, see main SKILL.md.

## Step 1: Font Sizes

Scan all CSS/style files for font-size declarations.

| Rule | Minimum | Flag if |
|------|---------|---------|
| Body text | 14px / 0.875rem | Below 14px |
| Headers (h1-h6) | 16px / 1rem | Below 16px |
| Labels, captions | 12px / 0.75rem | Below 12px |
| Interactive elements (buttons, inputs) | 14px / 0.875rem | Below 14px |

Report every violation with file:line.

## Step 2: Color Contrast (WCAG AA)

Check foreground/background color pairs in stylesheets and inline styles.

| Text size | Required ratio |
|-----------|---------------|
| Normal text (< 18px) | 4.5:1 |
| Large text (>= 18px or bold >= 14px) | 3:1 |
| UI components and graphical objects | 3:1 |

Look for:
- Light gray text on white backgrounds
- Low-contrast placeholder text
- Text over images without overlay
- Disabled states that are too faint to read

## Step 3: Keyboard Navigation

Every interactive element must be reachable and operable via keyboard:

- **Tab order** follows visual layout (no `tabindex` > 0 unless justified).
- **Focus visible** on every focusable element (no `outline: none` without replacement).
- **Enter/Space** activates buttons and links.
- **Escape** closes modals, dropdowns, popups.
- **Arrow keys** navigate within composite widgets (tabs, menus, radio groups).
- **No keyboard traps** — user can always Tab away from any element.

Search for `outline: none`, `outline: 0`, `:focus { outline` — flag any that remove focus without adding a visible alternative.

## Step 4: Screen Reader Labels

Every interactive element needs an accessible name:

| Element | Required | Flag if missing |
|---------|----------|-----------------|
| `<img>` | `alt` attribute | Missing or empty (unless decorative with `alt=""` and `role="presentation"`) |
| `<input>` | Associated `<label>` or `aria-label` | Neither present |
| `<button>` | Text content or `aria-label` | Icon-only button without label |
| `<a>` | Meaningful text (not "click here") | Generic text or empty |
| Custom widgets | `role` + `aria-*` attributes | Missing role |
| Dynamic content | `aria-live` region | Status messages not announced |

## Step 5: Focus Management

Check these focus patterns:

- **Modal open** — focus moves to modal (first focusable element or modal container).
- **Modal close** — focus returns to the trigger element.
- **Page navigation** — focus moves to main content or page title.
- **Dynamic content** — new content announced via `aria-live` or focus moved to it.
- **Delete/remove** — focus moves to a logical next element, not lost.

## Step 6: Dynamic Text Overflow

Check that dynamic text (user input, API data) doesn't break layout:

- Long text truncated with ellipsis or wrapped properly.
- Containers have `max-width` or `overflow` handling.
- No horizontal scrollbars caused by long strings.
- Test with a 200-character string in every text field.

## Output Format

> **Accessibility Review for [target]**
>
> | # | Category | Severity | File:Line | Issue | Fix |
> |---|----------|----------|-----------|-------|-----|
> | 1 | Contrast | High | theme.css:12 | Gray text (#999) on white (#fff) = 2.8:1 | Use #767676 for 4.5:1 |
> | 2 | Keyboard | High | Modal.tsx:8 | `outline: none` with no replacement | Add `focus-visible` style |
> | 3 | Label | Medium | Search.tsx:22 | Icon button without aria-label | Add `aria-label="Search"` |
>
> **Summary:** [pass/fail count, biggest risks]
