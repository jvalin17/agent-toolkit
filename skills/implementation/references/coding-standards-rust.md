# Rust Coding Standards

> Our synthesis of Rust API guidelines and community best practices.
> Last verified: 2026-04-24

## Sources
- [Rust API Guidelines](https://rust-lang.github.io/api-guidelines/)
- [The Rust Style Guide](https://doc.rust-lang.org/nightly/style-guide/)
- [Rust by Example](https://doc.rust-lang.org/rust-by-example/)
- [Clippy Lints](https://rust-lang.github.io/rust-clippy/master/)

---

## Imports (use statements)
```rust
// GOOD: grouped, specific
use std::collections::HashMap;
use std::io::{self, Read};

use serde::{Deserialize, Serialize};
use tokio::sync::Mutex;

use crate::models::User;
use crate::services::auth;

// BAD: glob imports in application code
use std::io::*;
use crate::models::*;
```

**Rules:**
- Group: std → external crates → crate-local. Blank line between groups.
- Glob imports (`*`) only in tests and preludes. Never in application code.
- Use `self` for importing the module alongside items: `use std::io::{self, Read};`
- Run `cargo fmt` and `cargo clippy` — they catch import issues.

## Naming
```rust
// Types, traits, enums: PascalCase
struct UserProfile {}
enum JobStatus { Draft, Applied, Interview }
trait Searchable {}

// Functions, methods, variables: snake_case
fn get_active_users() -> Vec<User> {}
let user_count = 0;
let is_authenticated = true;

// Constants: UPPER_SNAKE_CASE
const MAX_CONNECTIONS: u32 = 100;
static DEFAULT_TIMEOUT: Duration = Duration::from_secs(30);

// Lifetimes: short lowercase
fn find<'a>(data: &'a str) -> &'a str {}

// BAD
let x = get_data();     // x what?
let tmp = process();    // tmp what?
fn do_it() {}           // do what?
```

## Comments
```rust
// GOOD: doc comments on public items
/// Searches for jobs matching the given criteria.
///
/// Returns an empty Vec if no matches found.
/// Respects rate limits — sleeps between API calls.
pub fn search_jobs(query: &str) -> Result<Vec<Job>> {}

// GOOD: explains non-obvious unsafe
// SAFETY: pointer is valid for the lifetime of the buffer,
// and we don't alias it elsewhere in this scope.
unsafe { ptr.read() }

// BAD: restates code
// Create a new vector
let jobs = Vec::new();
```

**Rules:**
- `///` doc comments on all public items (functions, structs, enums, traits).
- `//` inline comments for WHY only.
- `// SAFETY:` comment required before every `unsafe` block.
- No commented-out code. Delete it.

## Indentation & Formatting
- 4 spaces. No tabs.
- Run `cargo fmt` — non-negotiable. It enforces the official Rust style.
- Max line length: 100 characters (rustfmt default).

## Error Handling
```rust
// GOOD: use Result, provide context
fn load_config(path: &Path) -> Result<Config, AppError> {
    let content = std::fs::read_to_string(path)
        .map_err(|e| AppError::ConfigLoad { path: path.to_owned(), source: e })?;
    toml::from_str(&content)
        .map_err(|e| AppError::ConfigParse { source: e })
}

// BAD: unwrap in production code
let config = std::fs::read_to_string("config.toml").unwrap();
```

- Never `.unwrap()` or `.expect()` in production code. Use `?` and proper error types.
- `.unwrap()` is fine in tests.
- Use `thiserror` for library error types, `anyhow` for application error types.

## Rust-Specific
- Prefer `&str` over `String` in function parameters.
- Prefer iterators over manual loops: `.iter().map().filter().collect()`.
- Use `clippy`: `cargo clippy -- -D warnings`. Fix all warnings.
- Derive common traits: `#[derive(Debug, Clone, PartialEq)]` on data types.

## File Organization
```
src/
├── main.rs            # entry point only
├── lib.rs             # library root, re-exports
├── models/
│   ├── mod.rs
│   └── user.rs
├── services/
│   ├── mod.rs
│   └── auth.rs
├── handlers/          # HTTP handlers
└── error.rs           # error types
```

Keep modules focused. Split when a file exceeds ~300 lines.
