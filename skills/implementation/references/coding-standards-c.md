# C Coding Standards

> Our synthesis of CERT C, MISRA C, and Linux kernel style. Follow authoritative sources below for edge cases.
> Last verified: 2026-09-14

## Sources
- [CERT C Coding Standard](https://wiki.sei.cmu.edu/confluence/display/c/SEI+CERT+C+Coding+Standard)
- [MISRA C:2012 Guidelines](https://www.misra.org.uk/misra-c/)
- [Linux Kernel Coding Style](https://www.kernel.org/doc/html/latest/process/coding-style.html)

---

## Includes
```c
/* GOOD: system headers first, then local; include guards on every header */
#ifndef MYLIB_WIDGET_H
#define MYLIB_WIDGET_H

#include <stddef.h>
#include <stdint.h>

#include "mylib/types.h"

#endif /* MYLIB_WIDGET_H */

/* BAD: no guard, wrong order, includes implementation details */
#include "mylib/internal.h"
#include <stdint.h>
```

**Rules:**
- Group: system → third-party → local. Blank line between groups.
- Every header needs an include guard (`#ifndef`/`#define`/`#endif`); prefer over `#pragma once` for portability.
- Include only what you use; forward-declare structs to avoid pulling in full headers.

## Naming
```c
/* GOOD: snake_case, UPPER for macros, module prefix on all public symbols */
#define MYLIB_MAX_RETRIES  3
#define MYLIB_TIMEOUT_MS   100
typedef struct mylib_widget mylib_widget_t;
int  mylib_widget_init(mylib_widget_t *w, uint32_t id);
void mylib_widget_destroy(mylib_widget_t *w);

/* BAD: no prefix, inconsistent case, cryptic abbreviations */
#define maxR 3
int WidgetInit(Widget *W, int ID);
void wdgt_Destroy();
```

**Rules:**
- All identifiers: `snake_case`. No camelCase or PascalCase.
- Macros and compile-time constants: `UPPER_SNAKE_CASE`.
- Public symbols carry a module prefix (`mylib_`) to avoid link-time collisions.
- Single-letter names only for loop indices `i`, `j`, `k`.

## Memory
```c
/* GOOD: check allocation, sizeof on variable, NULL-after-free */
uint8_t *buf = malloc(count * sizeof(*buf));
if (buf == NULL) return -ENOMEM;
/* ... use buf ... */
free(buf);
buf = NULL;  /* poison: catches use-after-free and double-free */

/* BAD: unchecked alloc, sizeof on type, no NULL-after-free */
uint8_t *buf = malloc(count * sizeof(uint8_t));  /* buf may be NULL */
free(buf);
/* buf still points at freed memory */
```

**Rules:**
- Check every `malloc`/`calloc`/`realloc` return; NULL is fatal.
- `sizeof(*ptr)` not `sizeof(TypeName)` — stays correct if the type changes.
- Set pointer to `NULL` after `free`; kills most use-after-free and double-free bugs.
- Prefer `calloc` when zero-initialization is needed.

## Error Handling
```c
/* GOOD: checked returns, single cleanup exit via goto */
int process_file(const char *path, result_t *out)
{
    int rc = 0; FILE *fp = NULL; char *buf = NULL;

    fp  = fopen(path, "r");
    if (!fp)  { rc = -errno;  goto cleanup; }
    buf = malloc(BUF_SIZE);
    if (!buf) { rc = -ENOMEM; goto cleanup; }
    if (fread(buf, 1, BUF_SIZE, fp) == 0) { rc = -EIO; goto cleanup; }

    rc = parse(buf, out);
cleanup:
    free(buf); if (fp) fclose(fp);
    return rc;
}

/* BAD: unchecked returns, no cleanup — leaks fp and buf on any error */
void process_file(const char *path) {
    FILE *fp  = fopen(path, "r");
    char *buf = malloc(BUF_SIZE);
    fread(buf, 1, BUF_SIZE, fp);
}
```

**Rules:**
- Functions that can fail return `int` (0 = success, negative = error).
- Check `errno` immediately after a failed syscall — it is overwritten by subsequent calls.
- `goto cleanup` keeps a single exit point for resource release — no leaks.
- Never ignore return values from `fgets`, `snprintf`, `fread`, or `fwrite`.

## Pointers
```c
/* GOOD: NULL check, const on read-only data, restrict on non-aliasing pairs */
int widget_name_len(const mylib_widget_t *w)
{
    if (w == NULL) return -EINVAL;
    return (int)strlen(w->name);
}

void vec_add(float * restrict dst, const float * restrict src, size_t n)
{
    for (size_t i = 0; i < n; i++) dst[i] += src[i];
}

/* BAD: no NULL check, drops const, unchecked pointer arithmetic */
int widget_name_len(mylib_widget_t *w) {
    return strlen(w->name);          /* crashes if w is NULL */
}
char *p = (char *)buf + offset;      /* offset may be out of bounds */
```

**Rules:**
- NULL-check every pointer parameter before first dereference.
- Apply `const` to every pointer you do not write through; propagate it outward.
- Use `restrict` to declare non-aliasing pairs — enables safe compiler optimizations.
- Prefer indexed array access over manual arithmetic; indexes are easier to bounds-check.

## Structs
```c
/* GOOD: designated initializers (C99+), opaque type hides internals */
/* header exposes only: */
typedef struct mylib_conn mylib_conn_t;
mylib_conn_t *mylib_conn_create(const char *host, uint16_t port);
void          mylib_conn_destroy(mylib_conn_t *c);

/* .c file defines the struct; calloc zero-initializes all fields */
mylib_conn_t *mylib_conn_create(const char *host, uint16_t port)
{
    mylib_conn_t *c = calloc(1, sizeof(*c));
    if (c == NULL) return NULL;
    c->port = port;
    snprintf(c->host, sizeof(c->host), "%s", host);
    return c;
}

/* BAD: exposed internals, uninitialized fields */
struct conn { int fd; uint16_t port; char host[256]; };
struct conn c;   /* fields are garbage */
c.fd = 3;        /* port and host uninitialized */
```

**Rules:**
- Use `calloc` or `= {0}` / designated initializers — no uninitialized fields.
- Expose only an opaque `typedef` in public headers; keep `struct` body in the `.c` file.
- Designated initializers (`{ .field = value }`) preferred over positional ones.

## Common Anti-Patterns
```c
/* BUFFER OVERFLOW — BAD */
char buf[16];
strcpy(buf, user_input);         /* no length check */
sprintf(buf, "%s", user_input);  /* no length check */

/* BUFFER OVERFLOW — GOOD */
strncpy(buf, user_input, sizeof(buf) - 1);
buf[sizeof(buf) - 1] = '\0';
snprintf(buf, sizeof(buf), "%s", user_input);

/* USE-AFTER-FREE — BAD */
free(p);
printf("%s\n", p->name);   /* undefined behavior */

/* DOUBLE-FREE — BAD (fix: set p = NULL after every free) */
free(p); free(p);          /* undefined behavior */

/* FORMAT STRING VULNERABILITY — BAD */
printf(user_input);           /* attacker controls format */
/* GOOD */
printf("%s", user_input);

/* UNDEFINED BEHAVIOR — BAD */
int x = INT_MAX; x += 1;  /* signed overflow is UB */
int arr[4]; arr[4] = 0;   /* out-of-bounds write */
```

**Rules:**
- Never use `gets`, `scanf("%s")`, or `strcpy` on untrusted input.
- Pass a string literal as the format argument to `printf`/`fprintf` — never user data.
- Signed integer overflow is undefined behavior; use unsigned arithmetic or pre-check bounds.
- Build with `-Wall -Wextra -Wformat-security -fsanitize=address,undefined` during development.
