import pytest

from calculators.basic import add, divide, multiply, subtract


def test_add():
    assert add(2, 3) == 5


def test_subtract():
    assert subtract(10, 4) == 6


def test_multiply():
    assert multiply(3, 7) == 21


def test_divide():
    assert divide(8, 2) == 4.0


def test_divide_by_zero():
    with pytest.raises(ZeroDivisionError):
        divide(1, 0)


def test_float_compatible():
    assert add(1.5, 2.5) == 4.0
    assert subtract(5.5, 1.25) == 4.25
    assert multiply(2.5, 4) == 10.0
    assert divide(7.5, 2.5) == 3.0
