"""Password strength scoring for demo purposes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class Strength:
    score: int
    level: str
    missing: List[str]


def score_password(password: str) -> Strength:
    if password == "":
        raise ValueError("password must not be empty")

    missing: List[str] = []
    score = 0

    length = len(password)
    if length >= 12:
        score += 40
    elif length >= 8:
        score += 25
    else:
        score += 10
        missing.append("at least 8 characters")

    has_upper = any(ch.isupper() for ch in password)
    has_lower = any(ch.islower() for ch in password)
    has_digit = any(ch.isdigit() for ch in password)
    has_special = any(not ch.isalnum() for ch in password)

    if has_upper:
        score += 15
    else:
        missing.append("uppercase letter")
    if has_lower:
        score += 15
    else:
        missing.append("lowercase letter")
    if has_digit:
        score += 15
    else:
        missing.append("digit")
    if has_special:
        score += 15
    else:
        missing.append("special character")

    # Short passwords cannot be strong/fair regardless of character classes
    if length < 8:
        score = min(score, 35)

    if score >= 80:
        level = "strong"
    elif score >= 50:
        level = "fair"
    else:
        level = "weak"

    return Strength(score=score, level=level, missing=missing)
