# UI Review
Keywords: overflow, empty state, placeholder, false success, layout, UX, broken, hidden feature, blank page, loading failure, Promise.all

For guardrails and principles, see main SKILL.md.

## Step 1: Dynamic Text Overflow

Every element that displays dynamic data (user input, API responses, database content) needs overflow handling.

**Check every dynamic text element for:**
- `max-width` or width constraint on the container
- `overflow: hidden`, `text-overflow: ellipsis`, or `overflow-wrap: break-word`
- Tooltip or expandable view for truncated content

**Test with:**
- A 200-character single word (no spaces — breaks `word-wrap`)
- A 5-line paragraph where one line is expected
- Unicode characters, emoji, RTL text

Flag any dynamic text element without overflow handling. Report file:line for the component.

## Step 2: Empty State Handling

Every view that depends on data MUST have an empty state. No blank screens.

**For each data-dependent view, check:**
- What renders when the data array is empty?
- What renders when the API returns no results?
- What renders on first use before the user has created anything?

**A good empty state has:**
1. A clear message ("No recipes yet")
2. An action link ("Create your first recipe" or "Try a different search")
3. Visual context (icon or illustration — not a blank void)

**Flag these patterns:**
- Blank white space where a list/grid should be
- Spinner that never stops (no data = loading forever)
- Generic "No data" without context or action
- Error message shown for expected-empty states

## Step 3: Placeholder Detection

Find buttons, links, and features that exist in the UI but don't work yet.

**Search for:**
- `onClick={() => {}}` or empty handlers
- `// TODO`, `// FIXME`, `// HACK` in component files
- `console.log("not implemented")` or similar
- Links that go to `#` or `javascript:void(0)`
- Buttons that are always disabled without explanation
- Menu items that do nothing on click

**These are user-facing lies.** Every visible UI element must either work or be removed. Flag each one.

## Step 4: False Success Messages

Never show "success" for actions that haven't completed.

**Check for:**
- Toast/notification shown before async operation completes
- "Saved!" displayed without waiting for API response
- "Sent!" shown when the email/message wasn't actually sent
- Redirect to success page before confirmation from backend
- Optimistic UI without rollback on failure

**Pattern to flag:**
```
// BAD: shows success before knowing the result
showToast("Saved!");
await api.save(data);  // This might fail

// GOOD: shows success after confirmation
const result = await api.save(data);
if (result.ok) showToast("Saved!");
```

Search for toast/notification calls and verify they appear AFTER the async operation, not before.

## Step 5: Core Features Never Hidden

Core features (identified from `project-state.md` core intent) must never be conditionally hidden based on data state.

**Wrong:** Hide the search bar when there are no items.
**Right:** Show the search bar with empty state: "No items to search. Create one first."

**Wrong:** Hide the dashboard when the user has no activity.
**Right:** Show the dashboard with empty state and onboarding prompt.

Check that `{condition && <CoreFeature />}` patterns don't hide features that should always be visible.

## Step 6: Results Appear Where Expected

When a user triggers an action, the result should appear where they're looking.

**Flag these patterns:**
- Form submission redirects to a different page unexpectedly
- Search results appear in a different section from the search bar
- Action feedback appears at the top of a long page while user is scrolled down
- Modal closes and result is somewhere the user has to find

## Step 7: Silent Loading Failures

**This is the #1 cause of blank UI pages.** Check every component that loads data from APIs:

- **No Promise.all for independent data.** Search for `Promise.all` — if it loads display data from multiple endpoints, flag it. One failing endpoint kills ALL of them. Each data source must load independently with its own try/catch.
- **Error boundaries.** Every data-loading component should have error handling that shows a message, not a blank screen.
- **Health checks vs availability.** If UI shows "connected" or "available" for an API/service, verify it actually makes a test query — not just checks if a key exists.
- **Verify all API endpoints return data.** After any frontend change, check that each endpoint the page calls returns valid data. A 500 error that's caught silently = blank component.

**Test pattern:** For each page, list every API call it makes. Verify each one independently. Then verify the page renders with 1 endpoint failing — it should degrade gracefully, not go blank.

## Output Format

> **UI Review for [target]**
>
> | # | Category | Severity | File:Line | Issue | Fix |
> |---|----------|----------|-----------|-------|-----|
> | 1 | Overflow | High | UserCard.tsx:34 | No max-width on username display | Add `max-w-[200px] truncate` |
> | 2 | Empty state | High | Dashboard.tsx:12 | Blank screen when no data | Add empty state with CTA |
> | 3 | Placeholder | Medium | Settings.tsx:45 | "Export" button has empty onClick | Remove or implement |
> | 4 | False success | High | Form.tsx:67 | Toast before API response | Move toast into .then() |
>
> **Summary:** [count findings by severity, overall UI health]
