# Runtime Review
Keywords: smoke test, start app, run, try it, does it work, launch, boot, serve

For guardrails and principles, see main SKILL.md.

## Purpose

Start the application and verify the primary user flow works end-to-end. This is not a deep test — it's a smoke test to catch "it doesn't even start" and "the main thing is broken."

## Step 1: Start the App

1. Read the project's start instructions (README, package.json scripts, Makefile, docker-compose).
2. Install dependencies if needed (`npm install`, `pip install -r requirements.txt`, etc.).
3. Start the application using the project's standard dev command.
4. Wait for the app to be ready (watch for "listening on port", "ready", or similar).

If the app fails to start, report the error immediately:
> **Runtime: FAILED TO START**
> - Command: `npm run dev`
> - Error: [exact error output]
> - Likely cause: [assessment]

## Step 2: Test the Primary Flow

Read `project-state.md` for the core intent / primary user flow. If it doesn't exist, infer the primary flow from the code.

Walk through the primary flow:
1. Access the entry point (open URL, call main endpoint, run CLI command).
2. Perform the core action (search, create, submit, etc.).
3. Verify the result appears correctly.

## Step 3: Check for Failures

Look for these common smoke test failures:

| Check | How | Failure looks like |
|-------|-----|--------------------|
| App starts | Process runs without crash | Exit code != 0, stack trace |
| Entry point loads | GET / or main page | Blank screen, 500, connection refused |
| No console errors | Check browser/terminal output | Unhandled exceptions, warnings |
| Core action works | Perform the main feature | Error response, no result, hang |
| Data persists | Create then read back | Data missing after reload |
| Auth works (if applicable) | Login then access protected route | 401, redirect loop |

## Step 4: Report

> **Runtime Smoke Test**
>
> | Check | Status | Notes |
> |-------|--------|-------|
> | App starts | Pass/Fail | [details] |
> | Entry point loads | Pass/Fail | [details] |
> | Console errors | Pass/Fail | [list any errors] |
> | Core action | Pass/Fail | [what was tested, what happened] |
> | Data persistence | Pass/Fail | [details] |
>
> **Verdict:** [Works / Partially works / Broken]
>
> **Blocking issues:** [list anything that prevents basic usage]
