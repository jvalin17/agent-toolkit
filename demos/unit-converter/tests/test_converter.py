"""Unit converter — temperature and length."""

import pytest

from converter import celsius_to_fahrenheit, fahrenheit_to_celsius, kilometers_to_miles, miles_to_kilometers


def test_celsius_to_fahrenheit():
    assert celsius_to_fahrenheit(0) == 32.0
    assert celsius_to_fahrenheit(100) == 212.0
    assert celsius_to_fahrenheit(-40) == -40.0


def test_fahrenheit_to_celsius():
    assert fahrenheit_to_celsius(32) == 0.0
    assert fahrenheit_to_celsius(212) == 100.0
    assert fahrenheit_to_celsius(-40) == -40.0


def test_kilometers_to_miles():
    assert kilometers_to_miles(0) == 0.0
    assert round(kilometers_to_miles(1.609344), 6) == 1.0
    assert round(kilometers_to_miles(10), 5) == 6.21371


def test_miles_to_kilometers():
    assert miles_to_kilometers(0) == 0.0
    assert round(miles_to_kilometers(1), 6) == 1.609344
