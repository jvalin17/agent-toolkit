"""Temperature and length conversions."""

KM_PER_MILE = 1.609344


def celsius_to_fahrenheit(celsius: float) -> float:
    return celsius * 9.0 / 5.0 + 32.0


def fahrenheit_to_celsius(fahrenheit: float) -> float:
    return (fahrenheit - 32.0) * 5.0 / 9.0


def kilometers_to_miles(kilometers: float) -> float:
    return kilometers / KM_PER_MILE


def miles_to_kilometers(miles: float) -> float:
    return miles * KM_PER_MILE
