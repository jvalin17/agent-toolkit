"""Scientific calculator operations."""

import math


def power(base, exp):
    """Calculate base raised to the power of exp."""
    return base ** exp


def sqrt(x):
    """Calculate square root of x. Raises ValueError for negative numbers."""
    if x < 0:
        raise ValueError("Cannot calculate square root of a negative number")
    return math.sqrt(x)


def percent(part, whole):
    """Calculate what percentage part is of whole."""
    if whole == 0:
        raise ZeroDivisionError("Cannot calculate percentage with zero whole")
    return (part / whole) * 100
