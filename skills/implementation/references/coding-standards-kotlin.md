# Kotlin Coding Standards

> Our synthesis of Kotlin Coding Conventions, Android Kotlin Style Guide, and Effective Kotlin.
> Last verified: 2026-09-14

## Sources
- [Kotlin Coding Conventions](https://kotlinlang.org/docs/coding-conventions.html)
- [Android Kotlin Style Guide](https://developer.android.com/kotlin/style-guide)
- [Effective Kotlin — Marcin Moskała](https://kt.academy/book/effectivekotlin)

---

## Imports
```kotlin
// GOOD: specific imports, grouped (stdlib → third-party → project)
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.withContext

import com.squareup.moshi.JsonClass

import com.example.app.model.User
import com.example.app.repository.UserRepository

// BAD: wildcard imports
import kotlinx.coroutines.*
import com.example.app.model.*
```

**Rules:**
- No wildcard imports. Always import specific symbols.
- Group: kotlin/java stdlib → third-party → project. Blank line between groups.
- Remove unused imports. IDE enforces this automatically.

## Naming
```kotlin
// Classes: PascalCase, noun
class UserRepository
class JobSearchService

// Functions: camelCase, verb
fun findById(id: String): User
fun isAuthenticated(): Boolean

// Constants: UPPER_SNAKE_CASE
const val MAX_RETRY_COUNT = 3
const val DEFAULT_ROLE = "user"

// Backing properties: underscore prefix
private var _items = mutableListOf<Item>()
val items: List<Item> get() = _items

// BAD
val obj: Any          // obj of what?
val s: String         // s what?
fun doStuff() {}      // stuff what?
```

## Null Safety
```kotlin
// GOOD: express nullability clearly, use safe calls and elvis
fun getDisplayName(user: User?): String =
    user?.name?.trim() ?: "Anonymous"

// GOOD: lateinit for DI-injected, lazy for computed-once
lateinit var viewModel: UserViewModel          // set by framework
val config: Config by lazy { loadConfig() }   // computed once on first access

// GOOD: early return over nesting
fun process(input: String?) {
    val value = input ?: return
    // use value safely
}

// BAD: !! is a crash waiting to happen
val name = user!!.profile!!.name!!

// BAD: lateinit on primitives or nullable types (won't compile, but tempting to work around)
// BAD: using !! to "fix" a nullable instead of handling it
```

**Rules:**
- Prefer `?.` and `?:` over `!!`. Reserve `!!` only for invariants you can truly guarantee.
- Use `lateinit` for non-null fields initialized by a framework (DI, test setup).
- Use `lazy` for expensive computed properties that are read-only after first access.

## Coroutines
```kotlin
// GOOD: structured concurrency — scope tied to lifecycle
class UserViewModel(private val repo: UserRepository) : ViewModel() {
    fun loadUser(id: String) {
        viewModelScope.launch {
            val user = withContext(Dispatchers.IO) { repo.findById(id) }
            _state.value = UiState.Success(user)
        }
    }
}

// GOOD: Flow for reactive streams
fun observeUsers(): Flow<List<User>> = repo.usersFlow()
    .map { it.filter { u -> u.isActive } }
    .catch { e -> emit(emptyList()) }

// BAD: GlobalScope leaks — not tied to any lifecycle
GlobalScope.launch { repo.findById(id) }

// BAD: blocking the main thread
val user = runBlocking { repo.findById(id) }  // on main thread

// BAD: wrong dispatcher for I/O
withContext(Dispatchers.Main) { File("x").readText() }
```

**Rules:**
- Always use a lifecycle-aware scope (`viewModelScope`, `lifecycleScope`, or injected `CoroutineScope`).
- Use `withContext(Dispatchers.IO)` for I/O, `Dispatchers.Default` for CPU work.
- Never use `GlobalScope` in production code. Never block the main thread with `runBlocking`.

## Data Classes and Sealed Classes
```kotlin
// GOOD: data class for value objects — gets equals/hashCode/copy/toString free
data class User(val id: String, val name: String, val email: String)
val updated = user.copy(name = "Alice")   // immutable update
val (id, name, email) = user              // destructuring

// GOOD: sealed class for exhaustive state modeling
sealed class UiState {
    object Loading : UiState()
    data class Success(val user: User) : UiState()
    data class Error(val message: String) : UiState()
}

// Force exhaustive handling — compiler error if branch missing
when (state) {
    is UiState.Loading  -> showSpinner()
    is UiState.Success  -> render(state.user)
    is UiState.Error    -> showError(state.message)
}

// BAD: data class for mutable, many-optional-field forms — use a regular class instead
data class FormState(var name: String? = null, var email: String? = null, ...)
```

## Extension Functions and Scope Functions
```kotlin
// GOOD: extension adds cohesive behavior without inheritance
fun String.toSlug(): String = lowercase().replace(' ', '-')

// GOOD: scope functions — pick the right one
val user = User().apply { name = "Alice"; email = "alice@example.com" }  // configure, returns receiver
val slug = title?.let { toSlug(it) } ?: ""                               // transform nullable
val result = buildString { append("Hello "); append(name) }              // scoped result

// BAD: extension on unrelated type just to avoid a utility class
fun Int.sendEmail(): Unit { ... }   // Int has nothing to do with email

// BAD: chaining scope functions until the intent is unreadable
user.let { it.also { it.apply { ... }.run { ... } } }
```

**Rules:**
- Extensions should read naturally on the receiver type.
- Prefer `apply` for init, `let` for nullable transforms, `also` for side-effects, `run` for scoped results.
- Avoid nesting scope functions more than one level deep.

## Collections
```kotlin
// GOOD: immutable by default
val ids: List<String> = listOf("a", "b", "c")
val scores: Map<String, Int> = mapOf("alice" to 42)

// GOOD: Sequence for large or chained pipelines (lazy evaluation)
val topEmails = users.asSequence()
    .filter { it.isActive }
    .map { it.email }
    .take(10)
    .toList()

// GOOD: idiomatic fold instead of manual accumulation
val total = orders.fold(0) { acc, order -> acc + order.amount }

// BAD: mutable list when you don't need mutation
val ids = mutableListOf("a", "b", "c")   // nothing mutates it

// BAD: eager chaining on a large list (allocates intermediate lists)
users.filter { ... }.map { ... }.filter { ... }   // use .asSequence() instead
```

## Common Anti-Patterns
| Anti-pattern | Fix |
|---|---|
| `user!!.profile!!.name!!` — crash on any null | `user?.profile?.name ?: "Unknown"` |
| `GlobalScope.launch { }` — leaks past lifecycle | `viewModelScope.launch { }` |
| `if (x != null) { x!! }` — Java null-check style | `x?.let { use(it) }` |
| Blocking I/O on main: `URL(...).readText()` | `withContext(Dispatchers.IO) { ... }` |
| `fun getCount(): Int? = list.size` — size is never null | `fun getCount(): Int = list.size` |
| Mutable `var` when value never changes | `val` — immutable by default |
