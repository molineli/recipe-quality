from __future__ import annotations


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(value, upper))


def linear_limit_score(actual: float | None, limit: float, max_score: float) -> float:
    if actual is None:
        return 0.0
    if actual <= limit:
        return max_score
    if actual >= 2 * limit:
        return 0.0
    return max_score * (1 - (actual - limit) / limit)

