import pytest

from calculators.expression import evaluate


def test_precedence():
    assert evaluate("2+3*4") == 14.0


def test_parentheses():
    assert evaluate("(2+3)*4") == 20.0


def test_returns_float():
    assert isinstance(evaluate("1+1"), float)


def test_floats_and_division():
    assert evaluate("7/2") == 3.5
    assert evaluate("1.5*2") == 3.0


def test_whitespace_and_nesting():
    assert evaluate(" ( 1 + 2 ) * ( 3 - (4 / 2) ) ") == 3.0


def test_unary_minus_and_plus():
    assert evaluate("-3+5") == 2.0
    assert evaluate("2*-3") == -6.0
    assert evaluate("+4") == 4.0


def test_left_associativity():
    assert evaluate("10-4-3") == 3.0
    assert evaluate("100/10/5") == 2.0


def test_division_by_zero_is_value_error():
    with pytest.raises(ValueError):
        evaluate("1/0")


@pytest.mark.parametrize(
    "bad",
    [
        "",
        "   ",
        "abc",
        "__import__('os')",
        "__import__('os').system('echo hi')",
        "2**3",
        "2//3",
        "2%3",
        "1 if 1 else 2",
        "[1,2]",
        "(1+2",
        "1+2)",
        "1+",
        "*3",
        "1 2",
        "True",
        "1e3",
        "1_000",
        "lambda: 1",
        "2 @ 3",
        "1+2; 3",
    ],
)
def test_rejects_invalid(bad):
    with pytest.raises(ValueError):
        evaluate(bad)


def test_rejects_non_string():
    with pytest.raises(ValueError):
        evaluate(None)  # type: ignore[arg-type]
