# Software Engineering Principles Reference

> **Our synthesis.** Principles explained in our own words with original examples.
> These are well-established software engineering concepts — see sources for authoritative definitions.
> Last verified: 2026-04-24

## Sources
- [SOLID Principles — Robert C. Martin (Uncle Bob)](https://en.wikipedia.org/wiki/SOLID)
- [SOLID Principles — DigitalOcean](https://www.digitalocean.com/community/conceptual-articles/s-o-l-i-d-the-first-five-principles-of-object-oriented-design)
- [DRY — The Pragmatic Programmer (Hunt & Thomas)](https://en.wikipedia.org/wiki/Don%27t_repeat_yourself)
- [KISS — Keep It Simple (Kelly Johnson)](https://en.wikipedia.org/wiki/KISS_principle)
- [YAGNI — Extreme Programming (Ron Jeffries)](https://en.wikipedia.org/wiki/You_aren%27t_gonna_need_it)
- [KISS, DRY, SOLID, YAGNI Guide — Medium](https://medium.com/@hlfdev/kiss-dry-solid-yagni-a-simple-guide-to-some-principles-of-software-engineering-and-clean-code-05e60233c79f)

---

## SOLID Principles

### S — Single Responsibility Principle (SRP)
**Rule:** A class/module should have one reason to change.
**Check:** "If I describe what this module does, do I use the word 'and'?"
- ❌ "This handles authentication AND sends emails AND logs events"
- ✅ "This handles authentication" (separate modules for email and logging)

### O — Open/Closed Principle (OCP)
**Rule:** Open for extension, closed for modification.
**Check:** "Can I add new behavior without changing existing code?"
- ❌ Adding a new agent requires modifying the coordinator's if/else chain
- ✅ New agent implements AgentBase, coordinator discovers it automatically

### L — Liskov Substitution Principle (LSP)
**Rule:** Subtypes must be substitutable for their base types.
**Check:** "Can I swap this implementation without breaking callers?"
- ❌ `SQLiteStorage` throws errors that `PostgresStorage` doesn't — callers break on switch
- ✅ Both implement `StorageBase` with same behavior contract

### I — Interface Segregation Principle (ISP)
**Rule:** Don't force implementations to depend on methods they don't use.
**Check:** "Does every implementer of this interface use ALL its methods?"
- ❌ `Agent` interface has `render_ui()` but background agents don't render anything
- ✅ Separate `Agent` and `UIRenderable` interfaces

### D — Dependency Inversion Principle (DIP)
**Rule:** High-level modules shouldn't depend on low-level modules. Both depend on abstractions.
**Check:** "Does the business logic import the database library directly?"
- ❌ `job_matcher.py` imports `sqlite3` directly
- ✅ `job_matcher.py` depends on `StorageBase` interface, `sqlite_storage.py` implements it

## Other Key Principles

### DRY — Don't Repeat Yourself
**Rule:** Every piece of knowledge has a single authoritative representation.
**Check:** "If this logic changes, how many files do I edit?"
- ❌ Same validation logic in 3 API endpoints
- ✅ Shared validation function/decorator

**Caution:** Don't over-DRY. Two things that look similar but change for different reasons should stay separate. Wrong abstraction is worse than duplication.

### KISS — Keep It Simple, Stupid
**Rule:** The simplest solution that works is the best solution.
**Check:** "Could a junior developer understand this in 5 minutes?"
- ❌ Custom event bus with middleware pipeline for a 3-page app
- ✅ Direct function calls between modules

### YAGNI — You Ain't Gonna Need It
**Rule:** Don't build features or abstractions until you actually need them.
**Check:** "Do I need this TODAY or am I guessing about tomorrow?"
- ❌ Building microservices for a project with 100 users
- ✅ Building a monolith that can be split later IF needed

### Separation of Concerns
**Rule:** Different responsibilities live in different places.
**Check:** "Does this layer know about things it shouldn't?"
- ❌ Database queries in the UI component
- ✅ UI → Service → Repository → Database (each layer only talks to adjacent)

### Composition Over Inheritance
**Rule:** Prefer assembling behavior from parts over deep inheritance chains.
**Check:** "Is my inheritance tree deeper than 2 levels?"
- ❌ `Animal → Pet → Dog → ServiceDog → TherapyDog`
- ✅ `Dog` has `ServiceCapability` and `TherapyCapability` injected

### Least Surprise
**Rule:** Code should behave as the reader expects.
**Check:** "Would someone reading this function name be surprised by what it does?"
- ❌ `get_user()` also updates the last-login timestamp
- ✅ `get_user()` only gets. `record_login()` updates the timestamp.
