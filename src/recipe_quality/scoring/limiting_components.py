from __future__ import annotations

from recipe_quality.utils.math import linear_limit_score


DEFAULT_LIMITS = {
    "sodium_mg_limit": 2000.0,
    "cooking_oil_g_limit": 25.0,
    "added_sugar_g_limit": 25.0,
}


def score_limiting_components(
    daily_totals: dict,
    resolved_targets: dict | None = None,
) -> tuple[float, dict[str, float]]:
    """计算 B 限制性成分控制分数和明细。"""
    targets = {**DEFAULT_LIMITS, **(resolved_targets or {})}
    sodium = linear_limit_score(daily_totals.get("sodium_mg"), targets["sodium_mg_limit"], 9)
    oil = linear_limit_score(daily_totals.get("cooking_oil_g"), targets["cooking_oil_g_limit"], 7)
    sugar = linear_limit_score(daily_totals.get("added_sugar_g"), targets["added_sugar_g_limit"], 5)
    saturated = score_saturated_fat(daily_totals)
    details = {
        "sodium": round(sodium, 2),
        "cooking_oil": round(oil, 2),
        "added_sugar": round(sugar, 2),
        "saturated_fat": round(saturated, 2),
    }
    return round(sum(details.values()), 2), details


def score_saturated_fat(daily_totals: dict) -> float:
    """按饱和脂肪供能比计算 B4 得分。"""
    saturated_fat_g = daily_totals.get("saturated_fat_g")
    energy_kcal = daily_totals.get("energy_kcal")
    if not saturated_fat_g or not energy_kcal:
        return 0.0
    ratio = saturated_fat_g * 9 / energy_kcal
    if ratio <= 0.10:
        return 4.0
    if ratio >= 0.15:
        return 0.0
    return 4 * (1 - (ratio - 0.10) / 0.05)
