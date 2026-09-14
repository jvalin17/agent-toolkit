# C# Coding Standards

> Our synthesis of Microsoft C# conventions, .NET Design Guidelines, and community best practices.
> Last verified: 2026-09-14

## Sources
- [Microsoft C# Coding Conventions](https://learn.microsoft.com/en-us/dotnet/csharp/fundamentals/coding-style/coding-conventions)
- [.NET Framework Design Guidelines](https://learn.microsoft.com/en-us/dotnet/standard/design-guidelines/)
- [Effective C# — Bill Wagner](https://www.oreilly.com/library/view/effective-c-50/9780134579290/)

---

## Using Statements
```csharp
// GOOD: System → third-party → project; blank line between groups
using System.Collections.Generic;
using System.Threading;

using Microsoft.Extensions.Logging;

using MyApp.Domain.Models;

// GOOD: .NET 6+ global usings in a dedicated GlobalUsings.cs
global using System;
global using System.Collections.Generic;

// BAD: unordered, unused, mixed groups
using MyApp.Domain.Models;
using System;
using Microsoft.Extensions.Logging;
using System.Linq; // unused
```

- Order: `System` → third-party → project. Blank line between groups.
- In .NET 6+, move universal BCL usings to a single `GlobalUsings.cs`.
- Remove unused usings. Roslyn IDE0005 enforces this automatically.

## Naming
```csharp
// PascalCase: types, public members, methods, constants
public class UserRepository {}
public void FindById(Guid id) {}
public const int MaxRetries = 3;

// camelCase: parameters and local variables
public User Find(Guid userId) { var count = 0; }

// _camelCase: private fields
private readonly ILogger<UserService> _logger;

// IInterface: interfaces always prefixed with I
public interface IUserRepository {}

// BAD
object obj; string s; bool b;   // meaningless names
IUserRepo r;                    // abbreviation hides intent
```

## Async/Await
```csharp
// GOOD: async all the way, CancellationToken, ConfigureAwait in libraries
public async Task<User> GetUserAsync(Guid id, CancellationToken ct = default)
{
    return await _repo.FindByIdAsync(id, ct).ConfigureAwait(false);
}

// BAD
public async void LoadData() { await FetchAsync(); }       // async void — exceptions vanish
public User GetUser(Guid id) => GetUserAsync(id).Result;  // blocks, deadlock risk
public async Task<User> GetAsync(Guid id) { ... }         // missing CancellationToken
```

- Propagate `CancellationToken` through every async call.
- Use `ConfigureAwait(false)` in library code to avoid context deadlocks.
- Never use `async void` except for top-level event handlers.
- Suffix all async methods with `Async`.

## LINQ
```csharp
// GOOD: method syntax, materialized once
var active = users.Where(u => u.IsActive).OrderBy(u => u.Name).ToList();

// GOOD: query syntax for join-heavy projections
var result = from u in users join r in roles on u.RoleId equals r.Id
             select new { u.Name, r.Title };

// BAD: stored as IEnumerable — re-evaluates on every access
private IEnumerable<User> _active = users.Where(u => u.IsActive);

// BAD: deferred query in loop causes N+1
foreach (var u in users.Where(u => u.IsActive)) Console.WriteLine(u.Name);
```

- Call `.ToList()` / `.ToArray()` when the result is used more than once.
- Never return `IQueryable` across layer boundaries.

## Nullable Reference Types
```csharp
// GOOD: enabled project-wide, explicit annotation, proper guard
// In .csproj: <Nullable>enable</Nullable>
public string? FindEmail(Guid id) =>
    _users.TryGetValue(id, out var u) ? u.Email : null;

public void Send(string email)
{
    ArgumentNullException.ThrowIfNull(email); // .NET 6+ guard
}

// BAD: suppressor hides bugs; unannotated null return
public string GetEmail(Guid id) => _users[id].Email!;  // ! suppressor
public string GetName() => null;                        // missing ? annotation
```

- Enable `<Nullable>enable</Nullable>` in every new project.
- Avoid `!` (null-forgiving) except where null is provably impossible.

## Dependency Injection
```csharp
// GOOD: constructor injection, interfaces, registered via IServiceCollection
public class OrderService
{
    private readonly IOrderRepository _repo;
    public OrderService(IOrderRepository repo) => _repo = repo;
}
builder.Services.AddScoped<IOrderRepository, SqlOrderRepository>();

// BAD: service locator — hides dependencies, breaks unit tests
public class OrderService
{
    private readonly IOrderRepository _repo =
        ServiceLocator.Get<IOrderRepository>(); // anti-pattern
}
```

- Always inject interfaces, not concrete types.
- Never use `IServiceProvider` as a service locator inside business logic.
- Match lifetime to usage: `Singleton` / `Scoped` / `Transient`.

## Records and Pattern Matching
```csharp
// GOOD: record for immutable data; switch expression for exhaustive dispatch
public record UserDto(Guid Id, string Name, string Email);

string Describe(Shape s) => s switch
{
    Circle c    => $"Circle r={c.Radius}",
    Rectangle r => $"Rect {r.Width}x{r.Height}",
    _           => "Unknown"
};

if (n is EmailNotification { IsVerified: true } email) Send(email);

// BAD: record for a stateful service (use class)
public record UserService(IUserRepository Repo) { ... }
```

- Use `record` for DTOs and value objects; `class` for services with behaviour.
- Prefer `switch` expressions over if/else chains for exhaustive matching.

## Error Handling
```csharp
// GOOD: specific exception, using declaration for guaranteed disposal
using var conn = new SqlConnection(_cs);
try { return await QueryAsync(conn, id, ct); }
catch (SqlException ex) when (ex.Number == 1205)
{
    _logger.LogWarning("Deadlock on {Id}", id);
    throw new TransientException("Deadlock", ex);
}

// BAD: catch Exception swallows everything; manual Dispose leaks
try { DoWork(); }
catch (Exception) { }  // never swallow
```

- Catch specific exceptions. Never catch `Exception` unless re-throwing.
- Use `using` declarations (C# 8+) to guarantee `IDisposable` cleanup.
- Use exception filters (`when`) instead of catch-then-rethrow.

## Common Anti-Patterns
```csharp
// BAD: string concat in loop → O(n²) allocations
string r = "";
foreach (var item in items) r += item + ", ";   // use string.Join or StringBuilder

// BAD: boxing via non-generic collections
ArrayList list = new ArrayList();               // use List<int>

// BAD: async void — exceptions crash the process silently
public async void OnClick(object s, EventArgs e) { await SaveAsync(); }

// BAD: catching Exception catches OutOfMemoryException too
catch (Exception e) { _log.LogError(e, "oops"); }
```

---

One class per file. Filename matches class name. Organize by feature, not layer, in large solutions.
