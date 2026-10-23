# Implementation — TDD module

Pull this when writing or changing logic.

## Seams first

A **seam** is the public boundary a test observes behaviour through without reaching inside. Before the first test of a slab, list the seams under test: prefer existing ones, as few as possible, the highest you can reach. Confirm them with the user; in an execution plan they are the slab's `seams` list. No test at an unagreed seam.

## The loop

1. **Red before green.** Write one failing test at an agreed seam, with specific assertions. Run it; the failure must match the missing behaviour.
2. Implement the minimum code to pass it. Nothing for the test after next.
3. Re-run: green before the next change.
4. One **vertical slice** per cycle: one seam, one test, one minimal implementation. The first slice is a tracer bullet through every layer.
5. Realistic fixture data; cite provenance when the project mode requires it (G-IMPL-7).

Refactoring is not part of the loop. It belongs to review (`/reviewer`).

## Anti-patterns

- **Tautological**: the assertion cannot fail. The expected value is recomputed the way the code computes it, or a thing is compared to itself (`assert total == total`, `expect(x).toBe(x)`, `assert True`). Expected values come from an independent source: a known-good literal, a worked example, the spec. The precommit gate greps the diff for these and blocks.
- **Implementation-coupled**: mocks internal collaborators, tests private methods, asserts call counts, or verifies through a side channel (querying the database instead of using the interface). The tell: the test breaks on a refactor with no behaviour change.
- **Horizontal slicing**: all tests first, then all code. Bulk tests verify imagined behaviour and lock in a test structure before the implementation is understood. Work in vertical slices.

## Mocks

Only at **system boundaries**: external APIs, time, randomness, sometimes the filesystem or the database. Never the project's own modules.

Fix mode: failing test → fix → verify (do not ask which mode).
Direct mode: still test-first for logic; wiring-only may scaffold without TDD.
