# Walking Skeleton Implementation

Build the thinnest possible end-to-end slice that proves the architecture works. The skeleton is always the first thing you build before any feature slabs.

## Why Skeleton First

- Catches architecture problems in hour 1, not day 5
- Proves all the layers can talk to each other
- Creates the project structure that features build on
- Gives the user something running immediately

## Inputs

Read the architecture doc's **component diagram** and **data flow**. Identify the minimal path through all layers.

## Deriving the Skeleton

From the architecture doc, trace the simplest possible path that touches every layer in the system. One table, one endpoint, one page, one call per layer. Nothing more.

Present the skeleton plan:

> "Before we build features, let's get the skeleton running — one thin path through the entire system:"
>
> **Skeleton for [project name]:**
> | Layer | What | Just enough to... |
> |-------|------|-------------------|
> | Database | 1 table, 2-3 fields | Prove DB connection works |
> | Backend | 1 endpoint (GET) | Prove server starts, talks to DB |
> | Frontend | 1 page, 1 API call | Prove frontend talks to backend |
> | Auth | Basic middleware (if needed) | Prove auth flow works |
> | LLM | 1 prompt, 1 call (if needed) | Prove LLM integration works |
>
> "This should take ~30 minutes. Once it runs end-to-end, we build features on top."

Only include layers that exist in the architecture. If there is no frontend, skip it. If there is no LLM integration, skip it.

## No TDD for the Skeleton

The skeleton is scaffold work, not business logic. It is wiring: config, project setup, connection strings, basic routing. No TDD needed — this is not testable business logic. Just get it running.

## Auth in the Skeleton

If the architecture specifies authentication, include a basic auth middleware in the skeleton. Do not implement full RBAC or permissions yet — just enough to prove the auth flow works (login, token, protected endpoint). Full security hardening comes with the feature slabs.

## Commit as First Slab

After the skeleton runs end-to-end, commit it as the first slab. Then move to feature slabs.

> "Skeleton running. All layers connected. Ready to commit: 'Walking skeleton — end-to-end path through all layers'. Proceed?"

## What the Skeleton is NOT

- It is not a feature. It delivers no user-visible functionality.
- It is not a place for business logic. That comes in feature slabs with TDD.
- It is not permanent scaffolding code — feature slabs will replace the placeholder implementations.

For guardrails and core principles, see the main `SKILL.md`.
