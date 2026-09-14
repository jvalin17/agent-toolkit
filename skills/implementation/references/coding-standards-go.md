# Go Coding Standards

> Our synthesis of Effective Go, Go Code Review Comments, and the Uber Go Style Guide.
> Last verified: 2026-09-14

## Sources
- [Effective Go](https://go.dev/doc/effective_go)
- [Go Code Review Comments](https://go.dev/wiki/CodeReviewComments)
- [Uber Go Style Guide](https://github.com/uber-go/guide/blob/master/style.md)

---

## Imports
```go
// GOOD: three groups — stdlib, third-party, internal
import (
    "context"
    "fmt"

    "go.uber.org/zap"

    "github.com/myorg/myapp/internal/config"
)

// BAD: no grouping, dot import, unused entry
import (
    "fmt"
    . "math"
    "context"
    "os" // unused
)
```

**Rules:**
- Three groups: stdlib → third-party → internal. Blank line between groups.
- Use `goimports` (not `gofmt` alone) — it manages grouping automatically.
- No dot imports. No blank imports except in `main` or `_test.go`.

## Naming
```go
// GOOD
type UserRepository struct{}          // exported: PascalCase
type userCache struct{}               // unexported: camelCase
const MaxRetryCount = 3
var errNotFound = errors.New("not found")  // unexported sentinel
type Storer interface{ Store(ctx context.Context, u User) error }  // -er suffix

// BAD
var MAX_RETRY_COUNT = 3    // underscores + ALL_CAPS not Go style
type user_repository struct{}
userpackage.UserCreate()  // stutter — package name is part of the call
```

**Rules:**
- No underscores in identifiers. Acronyms: `userID`, `parseURL`, `httpClient`.
- No stuttering: `pkg.New()` not `pkg.NewPkg()`.
- Single-method interfaces take an `-er` suffix (`Reader`, `Storer`, `Sender`).

## Error Handling
```go
// GOOD: wrap with %w, inspect with errors.Is/As
func findUser(ctx context.Context, id string) (*User, error) {
    u, err := db.Query(ctx, id)
    if err != nil { return nil, fmt.Errorf("findUser %s: %w", id, err) }
    return u, nil
}
var ErrNotFound = errors.New("not found")  // exported only if callers branch on it
if errors.Is(err, ErrNotFound) { ... }

// BAD: panic in library, string comparison, lost context
func findUser(id string) *User {
    u, err := db.Query(id)
    if err != nil { panic(err) }  // never panic in library code
    return u
}
if err.Error() == "not found" { ... }  // breaks with wrapped errors
```

**Rules:**
- Wrap every error: `fmt.Errorf("context: %w", err)`. Never discard.
- `errors.Is` / `errors.As` to inspect wrapped errors — never string-match.
- No `panic` in library code. Sentinel errors unexported unless callers must branch on them.

## Concurrency
```go
// GOOD: context propagated, WaitGroup, clear exit condition
func processAll(ctx context.Context, items []Item) error {
    var wg sync.WaitGroup
    for _, item := range items {
        wg.Add(1)
        go func(it Item) { defer wg.Done(); process(ctx, it) }(item)
    }
    wg.Wait()
    return nil
}

// BAD: goroutine leak — no exit condition, context ignored
go func() {
    for { out <- fetch() }  // runs forever
}()
```

**Rules:**
- Every goroutine must have a defined exit condition. No fire-and-forget without cancellation.
- `context.Context` is always the first parameter for any blocking or I/O call.
- Size channels deliberately: unbuffered = synchronization, buffered = decoupling.

## Interfaces
```go
// GOOD: accept interfaces, return structs; interface in consumer package
type Storer interface{ Store(ctx context.Context, u User) error }
func NewService(s Storer) *Service { return &Service{store: s} }

// BAD: fat interface — hard to mock, couples unrelated behaviour
type UserService interface {
    Create(User) error; Delete(string) error
    List() ([]User, error); Notify(User) error; Export() ([]byte, error)
}
```

**Rules:**
- Interfaces belong in the consumer package, not the implementation package.
- Prefer one- or two-method interfaces. Compose when needed.
- Don't export an interface until a second implementation exists.

## Structs
```go
// GOOD: functional options — avoids boolean/int argument explosion
type Option func(*Server)
func WithTimeout(d time.Duration) Option { return func(s *Server) { s.timeout = d } }
func NewServer(addr string, opts ...Option) *Server {
    s := &Server{addr: addr, timeout: 30 * time.Second}
    for _, o := range opts { o(s) }
    return s
}

// GOOD: embedding for composition
type LoggedStore struct {
    Store              // promotes all Store methods
    log *zap.Logger
}

// BAD: boolean argument hell
func NewServer(addr string, tls bool, timeout int, retries int, verbose bool) *Server
```

**Rules:**
- Use constructor functions (`NewFoo`) — never rely on zero-value struct literals for exported types.
- Functional options (`WithX`) for anything optional; no boolean or positional flag parameters.
- Embed only when the outer type truly IS the inner type, not for code reuse.

## Testing
```go
// GOOD: table-driven with t.Run
func TestAdd(t *testing.T) {
    for _, tc := range []struct{ name string; a, b, want int }{
        {"pos", 1, 2, 3}, {"neg", -1, -2, -3}, {"zero", 0, 0, 0},
    } {
        t.Run(tc.name, func(t *testing.T) {
            assert.Equal(t, tc.want, Add(tc.a, tc.b))
        })
    }
}

// GOOD: t.Helper so failure line points to the caller, not the helper
func assertUser(t *testing.T, got, want User) { t.Helper(); assert.Equal(t, want.ID, got.ID) }

// BAD: copy-paste tests, no subtests
func TestAddPositive(t *testing.T) { /* ... */ }
func TestAddNegative(t *testing.T) { /* ... */ }
```

**Rules:**
- Table-driven tests for any function with more than two cases.
- `t.Run` for subtests — each gets a name and isolated failure.
- `t.Helper()` in every test helper. `testify/assert` (non-fatal) unless a nil deref would follow.

## Common Anti-Patterns
```go
// BAD: naked return — reader must scroll up to find named vars
func compute() (result int, err error) { result = 42; return }

// BAD: init() abuse — hidden side effects, untestable
func init() { db = mustConnectDB() }  // crashes if env missing

// BAD: interface pollution — one impl, no need for interface yet
type Processor interface{ Process() error }

// BAD: channel as mutex — use sync.Mutex
var sem = make(chan struct{}, 1)
sem <- struct{}{}; doWork(); <-sem
```

**Rules:**
- No naked returns in functions longer than ~5 lines.
- `init()` for registration only (`flag.String`, `sql.Register`). Never I/O or connections.
- Don't export an interface until two concrete implementations exist.
- `sync.Mutex` for mutual exclusion; channels for communication.
