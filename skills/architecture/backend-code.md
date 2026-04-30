# Backend: Code Structure, Flow & Extensibility
Keywords: modules, patterns, SOLID, DRY, KISS, dependencies, plugins, data flow, extensibility

Code organization, design patterns, and extension points. 10 decisions + validation steps.

**Rules from real usage:**
- Cross-cutting concerns (budget, auth, logging, rate limiting) go in the wrapper/middleware, not in each caller. If 6 services all need budget checks, put it in the LLM provider wrapper — one place, catches all calls.
- Soft limits (budget, rate limiting, warning thresholds) follow the force_override pattern: check -> reject with details -> frontend shows confirmation -> retry with `force_override: true` flag. Never silently block or silently allow.

## Code Structure & Patterns

5 decisions covering how the codebase is organized.

### Decision 11: Module Organization

**Context:** How source code is structured into directories and modules. Depends on architecture pattern (monolith vs microservices).

**Options:**

| | Option A: By Layer | Option B: By Feature | Option C: Hybrid |
|---|---------|---------|---------|
| What | `controllers/`, `services/`, `models/`, `repositories/` | `users/`, `orders/`, `payments/` (each with its own controller, service, model) | Top-level by feature, internal by layer |
| Best for | Small apps, teams that think in layers | Medium-large apps, teams organized by product area | Most real-world apps |
| Trade-off | Cross-cutting changes touch many directories | Some duplication of patterns across features | Slightly more complex directory structure |
| Cost | Same | Same | Same |
| SOLID/DRY check | ⚠️ Changes often cross layers (violates SRP at directory level) | ✅ Each feature is self-contained (SRP) | ✅ Best of both |

**Consequence:** Affects how new features are added, how teams work in parallel, and how code is reviewed.

---

### Decision 12: Design Patterns

**Context:** Identify 2-3 patterns that solve actual problems in THIS project. Don't enumerate all patterns — only the ones that apply.

**Approach:** Based on the requirements and architecture decisions so far, identify specific problems and match patterns:

| Problem | Pattern | Example |
|---------|---------|---------|
| Multiple similar behaviors | Strategy | Different pricing calculators, different notification channels |
| Complex object creation | Factory / Builder | Creating orders with many optional fields |
| Cross-cutting concerns | Middleware / Decorator | Logging, auth, rate limiting applied to request handlers |
| Event-driven communication | Observer / Pub-Sub | Order created → send email, update inventory, log analytics |
| External service integration | Adapter / Gateway | Wrapping payment APIs so you can swap providers |
| Plugin/extension system | Plugin | Adding new skill types, new data sources |

**Consequence:** Pattern choices affect interface design and dependency direction.

---

### Decision 13: SOLID Check

**Context:** Validate the proposed structure against SOLID principles. Not a choice — a validation step.

Walk through each principle against the proposed structure:

| Principle | Question | What to Check |
|-----------|----------|---------------|
| **SRP** (Single Responsibility) | Does each module have one reason to change? | Flag god classes, modules doing too many things |
| **OCP** (Open/Closed) | Can you add features without modifying existing code? | Check if new features require editing existing modules |
| **LSP** (Liskov Substitution) | Can you swap implementations? | E.g., can you swap SQLite → PostgreSQL without changing business logic? |
| **ISP** (Interface Segregation) | Are interfaces focused or bloated? | Flag interfaces with methods that some implementations don't need |
| **DIP** (Dependency Inversion) | Do high-level modules depend on abstractions? | Check if business logic imports concrete database/API clients directly |

For each violation found, propose a specific fix.

---

### Decision 14: DRY/KISS/YAGNI Check

**Context:** Flag over-engineering or duplication. Not a choice — a validation step.

| Principle | Question | Red Flags |
|-----------|----------|-----------|
| **DRY** | Is there duplicated logic? | Copy-pasted validation, repeated error handling, duplicated queries |
| **KISS** | Is this the simplest solution? | Microservices for a 2-person team, Kubernetes for a prototype, event sourcing for a CRUD app |
| **YAGNI** | Are we building features we don't need yet? | Premature multi-tenancy, internationalization before first user, plugin system with one plugin |

For each violation found, propose a simpler alternative.

---

### Decision 15: Dependency Direction

**Context:** What depends on what. Circular dependencies indicate poor architecture. Depends on module organization (Decision 11).

**Validation:**
- Draw the dependency graph (which modules import which)
- Check for circular dependencies
- Verify that dependencies flow inward: UI → Application → Domain → Infrastructure (Clean Architecture) or similar
- Flag any case where a core module depends on an infrastructure module

**Options for fixing circular dependencies:**

| | Option A: Dependency Inversion | Option B: Extract Shared Module | Option C: Event-Based Decoupling |
|---|---------|---------|---------|
| What | Introduce an interface, have the dependency point to the abstraction | Move shared code to a common module both can import | Replace direct calls with events/messages |
| Best for | When two modules have a clear provider-consumer relationship | When the cycle is caused by shared types or utilities | When modules should be truly independent |

---

## Part 4: Data Flow

Not a decision area — a documentation exercise. After data and API decisions are made, diagram these three paths.

### Write Path
User action → input validation → business logic → data transformation → storage → confirmation/event emission

### Read Path
User request → authentication/authorization → cache check → database query → data transformation → response serialization → delivery

### Error Path
Failure at any stage → error classification (client error vs server error vs transient) → error response to caller → logging → alerting (if critical) → retry (if transient)

**Output:** ASCII flow diagram showing all three paths with the specific components from this architecture.

---

## Part 5: Extensibility

5 decisions covering how the system grows and accepts new functionality.

### Decision 16: Plugin/Extension Points

**Context:** Where can new functionality be added without modifying core code?

**Options:**

| | Option A: No Extension Points (YAGNI) | Option B: Hook-Based (lifecycle hooks, middleware) | Option C: Plugin Architecture (formal plugin API) |
|---|---------|---------|---------|
| What | Add features by editing existing code | Define hooks where external code can run (beforeSave, afterCreate, etc.) | Formal plugin interface with registration, discovery, and isolation |
| Best for | Small apps, solo developers, early-stage products | Medium apps that need customization points | Platforms, apps with third-party extensions |
| Trade-off | Simplest, but modification risk grows | Moderate complexity, clear extension boundaries | High upfront cost, but scales well |
| Cost | Zero | Moderate design effort | Significant design effort |
| SOLID/DRY check | ⚠️ Violates OCP | ✅ Supports OCP | ✅ Full OCP compliance |

**Consequence:** Affects interface contracts and versioning strategy.

---

### Decision 17: Interface Contracts

**Context:** What must new components implement? Depends on extension point design (Decision 16).

Define for each extension point:
- Required interface (methods/functions that must be implemented)
- Optional interface (methods with default behavior)
- Data contracts (input/output shapes)
- Error contracts (what errors can be thrown and how they're handled)

---

### Decision 18: Shared vs Isolated State

**Context:** What's shared across extensions? Depends on plugin architecture (Decision 16).

**Options:**

| | Option A: Shared State (global context) | Option B: Isolated State (each plugin has its own) | Option C: Shared Read, Isolated Write |
|---|---------|---------|---------|
| What | Extensions can read and modify shared application state | Each extension has its own state, communicates via messages | Extensions can read shared state but only write to their own |
| Best for | Tightly integrated extensions | Loosely coupled plugins, third-party extensions | Most real-world cases |
| Trade-off | Tight coupling, hard to reason about side effects | More complex communication, potential data duplication | Moderate complexity |
| SOLID/DRY check | ⚠️ Violates SRP — who owns the state? | ✅ Clear ownership | ✅ Balanced |

---

### Decision 19: Interface Versioning

**Context:** How do interfaces evolve without breaking existing extensions? Depends on interface contracts (Decision 17).

**Options:**

| | Option A: Semantic Versioning | Option B: Additive Only | Option C: Version Per Interface |
|---|---------|---------|---------|
| What | Major.minor.patch with breaking changes in major versions | Never remove/rename, only add | Each interface has its own version independent of others |
| Best for | Public APIs, plugin ecosystems | Internal extensions, rapid iteration | Large systems with many independent interfaces |
| Trade-off | Must maintain multiple versions during migration | Must be disciplined, old fields accumulate | More complex version tracking |
| SOLID/DRY check | ✅ Clear contracts | ✅ Backward compatible | ✅ Fine-grained control |

---

### Decision 20: Feature Toggles

**Context:** How to enable/disable features safely. Important for gradual rollouts and A/B testing.

**Options:**

| | Option A: Environment Variables | Option B: Config File / Database | Option C: Feature Flag Service (LaunchDarkly, Unleash) |
|---|---------|---------|---------|
| What | Simple on/off via env vars, requires restart | Toggles stored in config or DB, changeable at runtime | Managed service with targeting, rollout %, analytics |
| Best for | Small teams, few features | Medium teams, runtime control needed | Large teams, gradual rollouts, A/B testing |
| Trade-off | Requires redeploy to change, no targeting | Must build admin UI, no analytics | Cost, vendor dependency |
| Cost | Free | Free (build it) | Paid ($10-100+/mo) or self-hosted (Unleash is free) |
| SOLID/DRY check | ✅ Simple | ✅ Flexible | ✅ Full-featured |

**Local/cheap alternative:** Environment variables or a JSON config file.

---

## Decision Format Reference

Each decision above follows the standard format from the base SKILL.md. For guardrails (G-ARCH-1 through G-ARCH-4, G1-G9), see `shared/guardrails.md` — they are not duplicated here.
