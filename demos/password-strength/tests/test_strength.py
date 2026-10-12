"""Password strength scoring."""

import pytest

from strength import score_password, Strength


def test_too_short_is_weak():
    result = score_password("Ab1!")
    assert result.level == "weak"
    assert result.score < 40


def test_strong_password():
    result = score_password("CorrectHorseBattery9!")
    assert result.level == "strong"
    assert result.score >= 80


def test_missing_classes_is_fair_or_weak():
    result = score_password("alllowercaseletters")
    assert result.level in ("weak", "fair")
    assert "uppercase" in " ".join(result.missing).lower() or "digit" in " ".join(result.missing).lower()


def test_empty_raises():
    with pytest.raises(ValueError):
        score_password("")
