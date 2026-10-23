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

```python
def test_calculate_total():  # Tautological — recomputes the answer the way the code does
    items = [{"price": 10}, {"price": 5}]
    assert calculate_total(items) == sum(i["price"] for i in items)

def test_checkout_calls_payment():  # Implementation-coupled — asserts how, not what
    payment = Mock()
    checkout(cart, payment)
    payment.process.assert_called_once_with(cart.total)
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
- No mocking the unit under test; mocks only at system boundaries (external APIs, time, randomness)
- Expected values are independent literals or spec examples, never recomputed from the inputs (finalize blocks `assert True`, `expect(x).toBe(x)` and friends; you catch the recomputed kind)
- Tests sit at the seams agreed in the execution plan (`slabs[].seams`); a test at an unagreed seam, or one reaching past the interface (private method, call count, DB query instead of the API), is a finding
- Fixture provenance: test fixtures cite their data source (query output, user sample, spec, or factory). Flag fixtures that use specific-looking values (real dates, IDs, names) with no stated origin. (G-IMPL-7 — hard blocker in strict mode)
