# TypeScript & React Coding Standards

> Our synthesis of Google TS guide, React docs, and community best practices.
> Last verified: 2026-04-24

## Sources
- [Google TypeScript Style Guide](https://google.github.io/styleguide/tsguide.html)
- [React Documentation — Thinking in React](https://react.dev/learn/thinking-in-react)
- [Airbnb JavaScript Style Guide](https://github.com/airbnb/javascript)
- [TypeScript Do's and Don'ts](https://www.typescriptlang.org/docs/handbook/declaration-files/do-s-and-don-ts.html)

---

## Imports
```typescript
// GOOD: grouped, only what's used
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

import { JobCard } from '@/components/jobs/JobCard';
import { useJobSearch } from '@/hooks/useJobSearch';
import type { Job } from '@/types/jobs';

// BAD: unused, default + named mixed randomly, no grouping
import React from 'react';  // unused in modern React
import { everything } from './utils';  // vague
```

**Rules:**
- Group: react → third-party → local components → local utils → types.
- Use `type` keyword for type-only imports: `import type { Job } from ...`
- No default exports (prefer named exports for refactorability).
- Remove unused imports. ESLint `no-unused-vars` catches these.

## Naming
```typescript
// Variables and functions: camelCase
const userCount = 0;
function getActiveUsers() {}

// Components: PascalCase
function JobSearchForm() {}

// Types and interfaces: PascalCase
interface UserProfile {}
type JobStatus = 'draft' | 'applied' | 'interview';

// Constants: UPPER_SNAKE_CASE
const MAX_RESULTS = 25;
const API_BASE_URL = '/api/v1';

// Booleans: is/has/can/should prefix
const isLoading = true;
const hasPermission = false;
const canEdit = user.role === 'admin';

// Event handlers: handle prefix
function handleSubmit() {}
function handleSearchChange() {}

// BAD
const d = new Date();    // d what?
const temp = fetch();    // temp what?
let flag = false;        // flag for what?
```

## Comments
```typescript
// GOOD: explains why
// Debounce search to avoid hitting API on every keystroke
const debouncedSearch = useMemo(() => debounce(search, 300), [search]);

// GOOD: documents non-obvious prop behavior
interface JobCardProps {
  job: Job;
  /** If true, shows match score badge. Only available after running match. */
  showScore?: boolean;
}

// BAD: restates the code
// Set loading to true
setLoading(true);
```

**Rules:**
- JSDoc on component props interfaces when behavior isn't obvious.
- No commented-out JSX. Delete it.
- Comment WHY, not WHAT.

## React Specifics
```tsx
// GOOD: small, focused component
function JobCard({ job, onApply }: JobCardProps) {
  return (
    <div className="job-card">
      <h3>{job.title}</h3>
      <p>{job.company}</p>
      <button onClick={() => onApply(job.id)}>Apply</button>
    </div>
  );
}

// BAD: component doing too much
function JobPage() {
  // 200 lines of state, effects, handlers, and JSX
}
```

**Rules:**
- One component per file.
- Components under 100 lines. Extract sub-components if larger.
- Custom hooks for reusable logic: `useJobSearch`, `useAuth`.
- Avoid `useEffect` for data derived from state — use `useMemo`.
- Keys in lists: use stable IDs, never array index.
- Prefer `const` over `let`. Never `var`.

## Indentation & Formatting
- 2 spaces. No tabs.
- Use Prettier for consistent formatting.
- Max line length: 100 characters.
- Semicolons: be consistent (Prettier enforces either way).

## Type Safety
```typescript
// GOOD: explicit types where inference isn't enough
function calculateScore(resume: Resume, job: Job): number {}
const [jobs, setJobs] = useState<Job[]>([]);

// BAD: any kills type safety
function processData(data: any): any {}
const result: any = fetchSomething();
```

- Never use `any`. Use `unknown` if type is truly unknown, then narrow.
- No type assertions (`as`) unless truly necessary. Prefer type guards.
- Use discriminated unions for state: `type State = { status: 'loading' } | { status: 'done'; data: Job[] }`

## Error Handling
```typescript
// GOOD: handle errors with user feedback
try {
  const jobs = await searchJobs(query);
  setJobs(jobs);
} catch (error) {
  setError(error instanceof Error ? error.message : 'Search failed');
}

// BAD: silent catch
try { await searchJobs(query); } catch {}
```

## Defensive API Patterns

```typescript
// GOOD: guard API response shape before using it
const data = await api.listJobs();
setJobs(Array.isArray(data) ? data : []);

// BAD: trust the cast
const data = await api.listJobs() as Job[];
setJobs(data);  // crashes if data is {jobs: [...]} or {detail: "error"}

// GOOD: safe JSON parsing for DB/API strings
function safeJsonParse(value: unknown, fallback: unknown = {}): unknown {
  if (typeof value !== "string") return value || fallback;
  try { return JSON.parse(value) || fallback; }
  catch { return fallback; }
}

// BAD: unguarded JSON.parse
const parsed = JSON.parse(job.parsed_data);  // throws on "", "null", malformed

// GOOD: check response.ok on raw fetch
const r = await fetch("/api/settings", { method: "PUT", body: JSON.stringify(data) });
if (!r.ok) { setError(`Save failed (${r.status})`); return; }
setMessage("Saved");

// BAD: assume fetch succeeded
await fetch("/api/settings", { method: "PUT", body: JSON.stringify(data) });
setMessage("Saved");  // shows success even on 500

// GOOD: loading state with try/finally
setLoading(true);
try {
  await api.matchBatch(ids);
} catch {
  setError("Matching failed");
} finally {
  setLoading(false);  // always resets, even on error
}

// BAD: loading state without finally
setLoading(true);
await api.matchBatch(ids);  // if this throws, loading stays true forever
setLoading(false);
```

**Rules:**
- `Array.isArray()` before `.map()` on any API response.
- `try/catch` with safe fallback around every `JSON.parse` of external data.
- `response.ok` check on every raw `fetch()` before success path.
- `try/finally` around every `setLoading(true)` block.
- Never clear user input (`setApiKey("")`) before confirming the save succeeded.
- User-provided URLs: validate scheme (`/^https?:\/\//`) before rendering as `<a href>`.
- File drag-drop: enforce same extension filter as `<input accept>`.
- Per-item async data: use `Record<id, data>` not a single shared state variable.
- Only set `Content-Type` header when the request has a body.

## File Organization
```
src/
├── components/
│   └── jobs/
│       ├── JobCard.tsx          # one component per file
│       ├── JobList.tsx
│       └── JobSearchForm.tsx
├── hooks/
│   └── useJobSearch.ts          # custom hooks
├── pages/
│   └── JobSearchPage.tsx        # page-level components
├── api/
│   └── jobs.ts                  # API client functions
└── types/
    └── jobs.ts                  # shared type definitions
```
