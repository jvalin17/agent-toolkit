# Walking Skeleton Implementation
Keywords: skeleton, scaffold, wiring, project setup, end-to-end, first slab

Build the thinnest possible end-to-end slice that proves the architecture works. Always the first thing built before any feature slabs.

## Inputs

Read the architecture doc's component diagram and data flow. Trace the simplest possible path through all layers — one table, one endpoint, one page, one call per layer.

## No TDD for the Skeleton

The skeleton is scaffold work (config, project setup, connection strings, routing), not business logic. Just get it running.

## Frontend Foundation (if project has UI)

Before writing the first component, the skeleton must include these files:

| File | Why | What |
|------|-----|------|
| `types/index.ts` | All interfaces in one place. Prevents duplicate types and `as unknown as` casts. | Domain model interfaces |
| `api/client.ts` | Typed API wrapper. No raw `fetch()` in components. Checks `response.ok`, throws on error. | One function per endpoint, typed returns |
| `hooks/useAsync.ts` | Prevents duplicated loading/error/try-finally pattern. ~40 lines. | `const { data, loading, error } = useAsync(() => api.getJobs())` |
| Toast library | Every catch must show a user-visible message. Silent catches = invisible failures. | Install `sonner` or equivalent. Add `<Toaster />` to App. |
| `ErrorBoundary.tsx` | Without this, ANY unhandled throw blanks the entire screen. | Wraps all routes. Shows "Something went wrong" + retry. |
| `components/shared/` | Prevents copy-pasting the same pattern 4+ times. | Directory ready for Modal, StatCard, etc. |

## Auth in the Skeleton

If architecture specifies auth, include basic auth middleware — just enough to prove the flow works (login, token, protected endpoint). Full security hardening comes with feature slabs.

## Commit

After the skeleton runs end-to-end, commit as the first slab. Then move to feature slabs.

For guardrails and core principles, see the main `SKILL.md`.
