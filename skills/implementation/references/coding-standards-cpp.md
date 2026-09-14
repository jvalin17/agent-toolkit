# C++ Coding Standards

> Our synthesis of the Google C++ Style Guide and C++ Core Guidelines. Follow those sources for the authoritative reference.
> Last verified: 2026-09-14

## Sources
- [Google C++ Style Guide](https://google.github.io/styleguide/cppguide.html)
- [C++ Core Guidelines — Bjarne Stroustrup & Herb Sutter](https://isocpp.github.io/CppCoreGuidelines/CppCoreGuidelines)
- [Effective Modern C++ — Scott Meyers](https://www.oreilly.com/library/view/effective-modern-c/9781491908419/)

---

## Includes
```cpp
// GOOD: stdlib → system → third-party → local, alphabetical within groups
#include <algorithm>
#include <string>
#include <vector>

#include <absl/strings/str_cat.h>

#include "project/core/user.h"
#include "project/util/logging.h"

// BAD: no grouping, relative paths, C-style headers
#include "../../util/logging.h"
#include <stdio.h>              // prefer <cstdio>
#include <absl/strings/str_cat.h>
#include <string>
```

**Rules:**
- Group: stdlib → system → third-party → local. Blank line between groups. Alphabetical within.
- Prefer `<cstdio>` over `<stdio.h>`. Use `#pragma once`. No `using namespace std;` ever.

## Naming
```cpp
// GOOD
class UserRepository {};        // PascalCase classes
void process_request();         // snake_case functions/variables
constexpr int kMaxRetries = 3; // kConstant
#define LOG_FATAL(msg) ...      // MACRO_CASE

// BAD
class user_repository {};       // wrong case
void ProcessRequest();          // PascalCase on function
int r = 0;                      // meaningless name
const int MAX_RETRIES = 3;      // use kMaxRetries
```

**Rules:**
- Classes/structs/enums: `PascalCase`. Functions/variables: `snake_case`. Constants: `kCamelCase`. Macros: `UPPER_SNAKE_CASE`.
- Avoid macros — prefer `constexpr` and inline functions.
- Class member variables get a trailing underscore: `count_`.

## Memory
```cpp
// GOOD: RAII — smart pointers, containers, stack allocation
auto conn = std::make_unique<Connection>(host, port);
auto cache = std::make_shared<Cache>(config);
std::vector<Widget> widgets;  // owns elements automatically

// GOOD: return by value; NRVO/move avoids copies
std::string build_message(std::string prefix) {
    prefix += " world";
    return prefix;
}

// BAD: raw ownership — who calls delete? when?
Connection* conn = new Connection(host, port);
delete conn;
```

**Rules:**
- No raw `new`/`delete` — use `std::make_unique` / `std::make_shared`.
- Raw pointers are non-owning observers only. Pass by value to own; `const&` to observe.

## Error Handling
```cpp
// GOOD: typed exception; noexcept where truly non-throwing
class ParseError : public std::runtime_error {
  public:
    using std::runtime_error::runtime_error;
};
int parse_port(std::string_view input);                        // throws ParseError
bool try_parse_port(std::string_view input, int& out) noexcept;  // out-param style

// BAD: catch-all swallows errors silently
try { connect(host); } catch (...) { /* ignored */ }
```

**Rules:**
- Mark non-throwing functions `noexcept` — enables optimizations, documents intent.
- Never catch `...` silently — log or re-throw. Destructors are `noexcept` by default; keep them that way.
- Prefer `std::optional<T>` / `std::expected<T,E>` (C++23) for expected failure paths.

## Classes
```cpp
// GOOD: Rule of Zero — members manage themselves
class Config {
  public:
    explicit Config(std::string path);
  private:
    std::string path_;
    std::vector<std::string> entries_;
};

// GOOD: Rule of Five when owning a raw resource
class FileHandle {
  public:
    explicit FileHandle(const char* path);
    ~FileHandle();
    FileHandle(const FileHandle&) = delete;
    FileHandle& operator=(const FileHandle&) = delete;
    FileHandle(FileHandle&&) noexcept;
    FileHandle& operator=(FileHandle&&) noexcept;
};

// BAD: polymorphic base with no virtual destructor — UB on delete
class Base { public: void do_work(); };
```

**Rules:**
- Prefer Rule of Zero: let `unique_ptr`, `vector`, `string` handle lifecycle.
- If you define any of destructor/copy/move, define or `= delete` all five.
- Polymorphic base classes must have a `virtual` destructor.
- Prefer composition over inheritance; mark single-arg constructors `explicit`.

## Templates
```cpp
// GOOD (C++20): concepts give clear constraints and readable errors
template <std::integral T>
T clamp(T value, T lo, T hi) { return std::max(lo, std::min(value, hi)); }

// GOOD (pre-C++20): SFINAE via enable_if
template <typename T, std::enable_if_t<std::is_integral_v<T>, int> = 0>
T clamp(T value, T lo, T hi);

// BAD: unconstrained — cryptic errors deep in instantiation
template <typename T>
T clamp(T value, T lo, T hi) { return lo < value ? (value < hi ? value : hi) : lo; }
```

**Rules:**
- Prefer C++20 concepts over SFINAE — better constraints, better error messages.
- Prefer `if constexpr` over recursive template specializations.
- Explicit instantiation in `.cpp` reduces compile time for heavy templates.

## Concurrency
```cpp
// GOOD: mutex + lock_guard for shared state; atomic for simple scalars
class RequestCounter {
  public:
    void increment() { std::lock_guard lock(mutex_); ++count_; }
    int get() const  { std::lock_guard lock(mutex_); return count_; }
  private:
    mutable std::mutex mutex_;
    int count_ = 0;
};
std::atomic<bool> shutdown_requested{false};

// BAD: unsynchronized shared data — data race, undefined behavior
int g_count = 0;
void worker() { ++g_count; }
```

**Rules:**
- Protect all shared mutable state with `std::mutex`; use `std::atomic` for simple scalars.
- Prefer `std::lock_guard` / `std::scoped_lock`. Never use `volatile` for synchronization.

## Common Anti-Patterns
```cpp
// BAD → GOOD

// C-style cast hides bugs
double ratio = (double)count / total;
double ratio = static_cast<double>(count) / total;  // explicit, checkable

// using namespace std pollutes global namespace
using namespace std;
// omit it; qualify std::string, std::vector explicitly

// owning raw pointer with manual delete
Widget* w = new Widget();
auto w = std::make_unique<Widget>();

// magic numbers
if (attempts > 3) { ... }
constexpr int kMaxAttempts = 3;
if (attempts > kMaxAttempts) { ... }

// returning pointer to local — dangling, undefined behavior
int* get_value() { int x = 42; return &x; }
int  get_value() { return 42; }
```

**Rules:**
- Use `static_cast`/`dynamic_cast`/`const_cast` — never C-style `(T)x`. No `using namespace std;`. No owning raw pointers. Name every magic number with a `constexpr` constant.
