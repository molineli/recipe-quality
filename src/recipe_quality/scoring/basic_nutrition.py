from __future__ import annotations


DEFAULT_TARGETS = {
    "protein_g": 60.0,
    "fiber_g": 25.0,
    "calcium_mg": 800.0,
    "iron_mg": 12.0,
    "potassium_mg": 2000.0,
    "vitamin_c_mg": 100.0,
}

FOOD_GROUP_TARGETS = {
    "grains_and_tubers": {"weight": 2.0, "target_g": 250.0},
    "vegetables": {"weight": 3.0, "target_g": 300.0},
    "fruits": {"weight": 3.0, "target_g": 200.0},
    "livestock_poultry_meat": {"weight": 2.0, "target_g": 75.0},
    "aquatic_products": {"weight": 2.0, "target_g": 75.0},
    "eggs": {"weight": 2.0, "target_g": 50.0},
    "dairy": {"weight": 2.0, "target_g": 300.0},
    "soy_products": {"weight": 1.0, "target_g": 25.0},
    "nuts": {"weight": 1.0, "target_g": 10.0},
}


def score_basic_nutrition(daily_totals: dict, daily_targets: dict | None = None) -> tuple[float, dict]:
    """计算 A 基础营养质量的初版分数和明细。"""
    targets = {**DEFAULT_TARGETS, **(daily_targets or {})}
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
    }
    return round(food_group_score + protein + fiber + micro, 2), details


def score_food_group_coverage(daily_totals: dict) -> tuple[float, dict]:
    """按新版 A1 权重计算食物组覆盖度 20 分。"""
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
    """按有效食物类别数量计算 A1 多样性得分。"""
    if count >= 8:
        return 2.0
    if count >= 6:
        return 1.5
    if count >= 4:
        return 1.0
    if count >= 2:
        return 0.5
    return 0.0
