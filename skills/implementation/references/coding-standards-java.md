# Java Coding Standards

> Our synthesis of Google Java guide and community best practices.
> Last verified: 2026-04-24

## Sources
- [Google Java Style Guide](https://google.github.io/styleguide/javaguide.html)
- [Oracle Java Code Conventions](https://www.oracle.com/java/technologies/javase/codeconventions-introduction.html)
- [Effective Java — Joshua Bloch](https://www.oreilly.com/library/view/effective-java/9780134686097/)

---

## Imports
```java
// GOOD: specific imports, grouped
import java.util.List;
import java.util.Optional;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import com.example.app.model.User;
import com.example.app.service.UserService;

// BAD: wildcard imports
import java.util.*;
import com.example.app.model.*;
```

**Rules:**
- No wildcard imports. Always import specific classes.
- Group: java → javax → third-party → project. Blank line between groups.
- Remove unused imports. IDE does this automatically.

## Naming
```java
// Classes: PascalCase, noun
public class UserRepository {}
public class JobSearchService {}

// Methods: camelCase, verb
public User findById(String id) {}
public boolean isAuthenticated() {}

// Variables: camelCase, descriptive
int activeUserCount = 0;
String errorMessage = "Not found";

// Constants: UPPER_SNAKE_CASE
public static final int MAX_RETRY_COUNT = 3;
public static final String DEFAULT_ROLE = "user";

// BAD
Object obj;        // obj of what?
String s;          // s what?
int n;             // n of what?
boolean b;         // boolean of what?
```

## Comments
```java
// GOOD: Javadoc on public methods
/**
 * Finds jobs matching the given criteria.
 *
 * @param query search terms
 * @param location city or "remote"
 * @return matching jobs, empty list if none found
 */
public List<Job> searchJobs(String query, String location) {}

// GOOD: explains why
// Cache for 5 minutes — job board API rate limits at 100 req/min
@Cacheable(value = "jobs", ttl = 300)

// BAD: restates code
// Get the user
User user = userService.getUser(id);
```

**Rules:**
- Javadoc on all public classes and methods.
- Keep Javadoc concise. One sentence description + @param + @return.
- Inline comments for WHY only.
- No commented-out code.

## Indentation & Formatting
- 2 spaces (Google style) or 4 spaces (Oracle style). Pick one, be consistent.
- Opening brace on same line: `if (condition) {`
- Max line length: 100 characters.
- Use Google Java Format or Spotless for consistency.

## Error Handling
```java
// GOOD: specific exception, helpful message
try {
    User user = repository.findById(id)
        .orElseThrow(() -> new NotFoundException("User " + id + " not found"));
} catch (DatabaseException e) {
    log.error("Failed to query user {}: {}", id, e.getMessage());
    throw new ServiceException("Unable to retrieve user", e);
}

// BAD: catch Exception, swallow
try { repository.findById(id); }
catch (Exception e) { /* ignore */ }
```

- Catch specific exceptions, not `Exception` or `Throwable`.
- Always log or re-throw. Never swallow.
- Use Optional instead of returning null.

## File Organization
```
src/main/java/com/example/app/
├── controller/        # REST endpoints
├── service/           # business logic
├── repository/        # data access
├── model/             # entities
├── dto/               # request/response objects
├── config/            # configuration
└── exception/         # custom exceptions
```

One public class per file. Class name matches filename.
