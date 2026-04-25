# Design Patterns Reference

## When to Suggest Each Pattern

Only suggest patterns that solve a REAL problem in the user's project. Never suggest patterns "just because."

### Creational Patterns

| Pattern | Suggest When | Example |
|---------|-------------|---------|
| **Factory** | Multiple implementations of same interface, chosen at runtime | Agent system: `AgentFactory.create("job")` returns JobAgent |
| **Builder** | Complex object with many optional parameters | Config objects, query builders, report generators |
| **Singleton** | Exactly one instance needed globally (DB connection, config) | Database connection pool, app configuration |

### Structural Patterns

| Pattern | Suggest When | Example |
|---------|-------------|---------|
| **Adapter** | Wrapping external library to match your interface | Wrapping jobspy to match your SkillBase interface |
| **Facade** | Simplifying complex subsystem | Single `JobService` hiding scraping + matching + storing |
| **Proxy** | Adding behavior before/after calls (caching, logging, auth) | Caching proxy around API calls |
| **Composite** | Tree-like structures, treat individual + group the same | File system, UI components, nested categories |

### Behavioral Patterns

| Pattern | Suggest When | Example |
|---------|-------------|---------|
| **Strategy** | Multiple algorithms/behaviors, swappable at runtime | Different search strategies, different scoring algorithms |
| **Observer** | One change should notify many listeners | Event system: job found → update UI + save to DB + notify user |
| **Command** | Undo/redo, queuing operations, logging actions | Application tracking: undo status change, action history |
| **Template Method** | Same steps, different implementations | Agent base class: all agents follow same lifecycle, different logic |

### Architectural Patterns

| Pattern | Suggest When | Example |
|---------|-------------|---------|
| **Repository** | Abstract data access from business logic | `JobRepository.find_by_criteria()` hides SQL |
| **MVC/MVP** | Separating UI from logic from data | Web apps: route → controller → model → view |
| **CQRS** | Read and write models are very different | News feed: write a post (simple) vs read a feed (complex aggregation) |
| **Event Sourcing** | Need complete audit trail, replay events | Financial transactions, application status history |
| **Plugin** | System must be extensible without modifying core | Agent system: add new agents without changing coordinator |

## Anti-Patterns to Flag

| Anti-Pattern | What It Looks Like | Better Alternative |
|-------------|-------------------|-------------------|
| God Object | One class does everything | Split into focused classes (SRP) |
| Spaghetti | No clear structure, everything calls everything | Layer architecture, dependency rules |
| Golden Hammer | Using same pattern/tool for everything | Choose pattern based on problem |
| Premature Optimization | Caching, sharding, microservices before needed | Start simple, optimize when measured |
| Over-Engineering | Abstract factory for 2 implementations | Simple factory or just a function |
