import pytest
from calculators.scientific import percent, power, sqrt


def test_power():
    assert power(2, 10) == 1024
    assert power(3, 0) == 1
    assert power(2, -1) == 0.5
    assert power(5, 2) == 25


def test_sqrt():
    assert sqrt(9) == 3.0
    assert sqrt(0) == 0.0
    assert sqrt(16) == 4.0


def test_sqrt_negative_raises_value_error():
    with pytest.raises(ValueError):
        sqrt(-1)
    with pytest.raises(ValueError):
        sqrt(-100)


def test_percent():
    assert percent(25, 200) == 12.5
    assert percent(50, 100) == 50.0
    assert percent(0, 100) == 0.0
    assert percent(1, 4) == 25.0
