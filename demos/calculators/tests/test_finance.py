from calculators.finance import compound_interest, tip


def test_compound_interest():
    assert compound_interest(1000, 0.05, 2) == 1102.5


def test_tip():
    assert tip(80, 15) == 12.0
