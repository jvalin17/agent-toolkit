# Coding Standards Index

> Quick reference for all language standards. Each language has a detailed file.
> Last verified: 2026-04-24

## Universal Rules (ALL languages)

1. **No unnecessary imports.** Only import what you use. Remove unused imports before committing.
2. **Readable variable names.** `user_count` not `uc`. `is_authenticated` not `flag1`. A reader should understand the variable without reading surrounding code.
3. **Appropriate comments.** Comment WHY, not WHAT. No essays. If the code needs a paragraph to explain, the code is too complex — simplify it.
4. **Consistent indentation.** Follow the language standard. Never mix tabs and spaces.
5. **Small functions.** If a function doesn't fit on one screen (~30 lines), it's doing too much. Split it.
6. **Early returns.** Reduce nesting. Return early for error cases instead of wrapping everything in if/else.
7. **No magic numbers.** Use named constants. `MAX_RETRIES = 3` not bare `3`.
8. **Error messages must be helpful.** `"User {id} not found"` not `"Error"`.

## Per-Language Files

| Language | File | Official Style Guide |
|----------|------|---------------------|
| Python | [coding-standards-python.md](coding-standards-python.md) | [PEP 8](https://peps.python.org/pep-0008/) |
| TypeScript/React | [coding-standards-typescript.md](coding-standards-typescript.md) | [Google TS Guide](https://google.github.io/styleguide/tsguide.html) |
| Java | [coding-standards-java.md](coding-standards-java.md) | [Google Java Guide](https://google.github.io/styleguide/javaguide.html) |
| Rust | [coding-standards-rust.md](coding-standards-rust.md) | [Rust API Guidelines](https://rust-lang.github.io/api-guidelines/) |
