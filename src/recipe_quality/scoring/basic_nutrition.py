from __future__ import annotations

from recipe_quality.config_loader import load_food_group_targets
from recipe_quality.targets import resolve_basic_nutrition_targets


FOOD_GROUP_TARGETS = load_food_group_targets()


def score_basic_nutrition(
    daily_totals: dict,
    resolved_targets: dict | None = None,
    target_user: dict | None = None,
) -> tuple[float, dict]:
    """计算 A 基础营养质量总分，并返回各子项明细。"""
    targets = resolve_basic_nutrition_targets(resolved_targets, target_user)
    food_group_score, food_group_details = score_food_group_coverage(daily_totals)
    protein = 6 * min((daily_totals.get("protein_g") or 0) / targets["protein_g"], 1)
    fiber = 6 * min((daily_totals.get("fiber_g") or 0) / targets["fiber_g"], 1)
    micro_values = []
    for key in ("calcium_mg", "iron_mg", "potassium_mg", "vitamin_c_mg"):
        value = daily_totals.get(key)
        if value is not None:
            micro_values.append(min(value / targets[key], 1))
    micro = 8 * (sum(micro_values) / len(micro_values)) if micro_values else 0
    details = {
        "food_group_coverage": food_group_details,
        "protein_adequacy": round(protein, 2),
        "fiber_adequacy": round(fiber, 2),
        "micronutrient_coverage": round(micro, 2),
        "targets_used": targets,
    }
    return round(food_group_score + protein + fiber + micro, 2), details


def score_food_group_coverage(daily_totals: dict) -> tuple[float, dict]:
    """按配置中的食物组权重和目标克数计算 A1 食物组覆盖度。"""
    amounts = daily_totals.get("food_group_amounts_g") or {}
    group_scores: dict[str, float] = {}
    for group, config in FOOD_GROUP_TARGETS.items():
        amount = float(amounts.get(group) or 0)
        score = config["weight"] * min(amount / config["target_g"], 1)
        group_scores[group] = round(score, 2)
    diversity_count = int(daily_totals.get("food_group_count") or 0)
    diversity_score = score_diversity(diversity_count)
    total_score = round(sum(group_scores.values()) + diversity_score, 2)
    return total_score, {
        "score": total_score,
        "max_score": 20,
        "group_amounts_g": amounts,
        "group_scores": group_scores,
        "diversity": {
            "count": diversity_count,
            "score": diversity_score,
        },
        "unclassified_ingredients": (daily_totals.get("data_quality") or {}).get(
            "unclassified_ingredients", []
        ),
    }


def score_diversity(count: int) -> float:
    """根据有效食物组数量计算 A1 多样性附加分。"""
    if count >= 8:
        return 2.0
    if count >= 6:
        return 1.5
    if count >= 4:
        return 1.0
    if count >= 2:
        return 0.5
    return 0.0
