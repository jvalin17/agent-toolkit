# Test Quality Patterns (precommit Step 2)

## Sloppy — REJECT

```python
def test_create_user():
    create_user("test", "test@test.com")  # no assertion

def test_something():
    assert True
```

```javascript
test("creates user", () => {
  const user = createUser({name: "x"});
  expect(user).toBeTruthy();
});
```

## Good — REQUIRE

```python
def test_create_user():
    user = create_user("Maria Garcia", "m.garcia@outlook.com")
    assert user.name == "Maria Garcia"
    assert user.email == "m.garcia@outlook.com"
```

```javascript
test("search returns matching recipes", async () => {
  const results = await searchRecipes("chicken");
  expect(results).toHaveLength(1);
  expect(results[0].title).toBe("Chicken Tikka");
});
```

## Audit checklist

- Specific value assertions (not truthy-only)
- Realistic test data
- Would fail if feature code deleted
- Edge cases: empty, null, unicode, boundaries
- No mocking the unit under test
- Fixture provenance: test fixtures cite their data source (query output, user sample, spec, or factory). Flag fixtures that use specific-looking values (real dates, IDs, names) with no stated origin. (G-IMPL-7 — hard blocker in strict mode)
