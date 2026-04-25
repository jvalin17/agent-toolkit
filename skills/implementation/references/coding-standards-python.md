# Python Coding Standards

> Our synthesis of PEP 8 and community best practices. Follow official PEP 8 for the authoritative source.
> Last verified: 2026-04-24

## Sources
- [PEP 8 — Style Guide for Python Code](https://peps.python.org/pep-0008/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [The Hitchhiker's Guide to Python — Code Style](https://docs.python-guide.org/writing/style/)

---

## Imports
```python
# GOOD: only what you use, grouped and ordered
import os
import sys
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import Column, String

from app.core.config import settings

# BAD: unused imports, wildcard imports, no grouping
from os import *
import json  # never used
from app.models import *
```

**Rules:**
- Group: stdlib → third-party → local. Blank line between groups.
- No wildcard imports (`from x import *`). Ever.
- Remove unused imports. Use `ruff check --select F401` to find them.
- One import per line for `from` imports with 3+ names.

## Naming
```python
# Variables and functions: snake_case
user_count = 0
def get_active_users():

# Classes: PascalCase
class UserRepository:

# Constants: UPPER_SNAKE_CASE
MAX_RETRY_COUNT = 3
DEFAULT_TIMEOUT_SECONDS = 30

# Private: single underscore prefix
def _validate_input(data):

# BAD: vague, abbreviated, misleading
x = get_data()      # what is x?
temp = process()     # temp what?
flag = True          # flag for what?
lst = []             # just say users, items, etc.
```

**Rules:**
- Name describes the content/purpose. Reader shouldn't need context.
- Booleans read as questions: `is_active`, `has_permission`, `can_edit`.
- Functions read as actions: `get_user`, `validate_input`, `send_email`.
- No single-letter names except `i, j, k` in short loops and `e` for exceptions.

## Comments
```python
# GOOD: explains WHY
# Rate limit to 10 req/s because the job board API bans above that
await asyncio.sleep(0.1)

# GOOD: clarifies non-obvious behavior
# Returns None if user not found (not an error — caller handles it)
def find_user(user_id: str) -> User | None:

# BAD: states the obvious
# Increment counter
counter += 1

# BAD: essay
# This function takes a user ID as input and then queries the database
# to find the user record. If the user is found, it returns the user
# object. If not found, it returns None. The function uses SQLAlchemy
# to perform the query and handles the session management internally.
def find_user(user_id: str) -> User | None:
```

**Rules:**
- Comment WHY, not WHAT. The code says what. Comments say why.
- Docstrings on public functions: one line if simple, Args/Returns if complex.
- No commented-out code. Delete it. Git has history.
- No TODO comments without a name and date: `# TODO(jvalin 2026-04): handle pagination`

## Indentation & Formatting
- 4 spaces. No tabs.
- Max line length: 88 characters (Black default) or 79 (PEP 8 strict).
- Use `ruff format` or `black` for consistent formatting.
- Blank line between functions. Two blank lines between classes.

## Type Hints
```python
# GOOD: typed
def get_user(user_id: str) -> User | None:
def calculate_score(resume: Resume, job: Job) -> float:

# BAD: no hints
def get_user(user_id):
def calculate_score(resume, job):
```

Use type hints on all public functions. Skip on obvious one-liners.

## Error Handling
```python
# GOOD: specific exception, helpful message
try:
    user = db.query(User).filter_by(id=user_id).one()
except NoResultFound:
    raise HTTPException(status_code=404, detail=f"User {user_id} not found")

# BAD: bare except, silent failure
try:
    user = db.query(User).filter_by(id=user_id).one()
except:
    pass
```

- Never bare `except:`. Always specify the exception type.
- Never silently swallow exceptions (`except: pass`).
- Log or re-raise — don't hide errors.

## File Organization
```
module/
├── __init__.py          # exports only (keep thin)
├── models.py            # data models
├── schemas.py           # request/response shapes
├── service.py           # business logic
├── repository.py        # data access
└── router.py            # API endpoints
```

One responsibility per file. If a file grows past ~300 lines, split it.
