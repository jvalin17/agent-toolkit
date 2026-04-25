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
