"""Finance calculator functions."""


def compound_interest(principal, rate, periods):
    """Return principal after compounding at rate for the given periods."""
    return principal * (1 + rate) ** periods


def tip(amount, tip_percent):
    """Return the tip for an amount and percentage."""
    return amount * tip_percent / 100
