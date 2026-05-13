from __future__ import annotations


def clamp(value: float, lower: float, upper: float) -> float:
    """将数值限制在指定上下界范围内。"""
    return max(lower, min(value, upper))


def linear_limit_score(actual: float | None, limit: float, max_score: float) -> float:
    """按限制性成分规则计算线性递减得分。"""
    if actual is None:
        return 0.0
    if actual <= limit:
        return max_score
    if actual >= 2 * limit:
        return 0.0
    return max_score * (1 - (actual - limit) / limit)
