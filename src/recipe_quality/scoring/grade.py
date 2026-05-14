from __future__ import annotations


GRADE_ORDER = ["A", "B", "C", "D", "E"]
LIMITED_COMPONENTS = (
    ("sodium_mg", "sodium_mg_limit", "sodium"),
    ("cooking_oil_g", "cooking_oil_g_limit", "cooking_oil"),
    ("added_sugar_g", "added_sugar_g_limit", "added_sugar"),
)


def score_to_grade(score: float) -> str:
    """将百分制总分转换为 A/B/C/D/E 等级。"""
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "E"


def apply_grade_caps(raw_grade: str, caps: list[dict]) -> str:
    """根据已触发的封顶规则修正最终等级。"""
    final_grade = raw_grade
    for cap in caps:
        cap_grade = cap["cap_grade"]
        if GRADE_ORDER.index(cap_grade) > GRADE_ORDER.index(final_grade):
            final_grade = cap_grade
    return final_grade


def evaluate_grade_caps(daily_totals: dict, resolved_targets: dict | None = None) -> list[dict]:
    """检查能量、限制性成分和数据质量等最高等级封顶规则。"""
    targets = {
        "energy_kcal": 2000.0,
        "sodium_mg_limit": 2000.0,
        "cooking_oil_g_limit": 25.0,
        "added_sugar_g_limit": 25.0,
        **(resolved_targets or {}),
    }
    caps: list[dict] = []
    energy = daily_totals.get("energy_kcal") or 0
    if targets["energy_kcal"]:
        ratio = energy / targets["energy_kcal"]
        if ratio < 0.70 or ratio > 1.30:
            caps.append({"trigger": "energy_ratio_severe", "value": ratio, "cap_grade": "D"})
        elif ratio < 0.80 or ratio > 1.20:
            caps.append({"trigger": "energy_ratio_outside_range", "value": ratio, "cap_grade": "C"})

    limited_component_ratios = []
    for key, limit_key, label in LIMITED_COMPONENTS:
        value = daily_totals.get(key) or 0
        limit = targets[limit_key]
        ratio = value / limit if limit else 0
        limited_component_ratios.append((label, ratio))
        if value >= 3 * limit:
            caps.append({"trigger": f"{label}_above_3x_limit", "value": value, "cap_grade": "D"})
        elif value >= 2 * limit:
            caps.append({"trigger": f"{label}_above_2x_limit", "value": value, "cap_grade": "C"})

    over_1_5x = [label for label, ratio in limited_component_ratios if ratio >= 1.5]
    if len(over_1_5x) >= 2:
        caps.append(
            {
                "trigger": "multiple_limited_components_above_1_5x_limit",
                "value": over_1_5x,
                "cap_grade": "C",
            }
        )

    saturated_fat_g = daily_totals.get("saturated_fat_g") or 0
    if energy:
        saturated_fat_energy_ratio = saturated_fat_g * 9 / energy
        if saturated_fat_energy_ratio >= 0.15:
            caps.append(
                {
                    "trigger": "saturated_fat_energy_ratio_above_15_percent",
                    "value": saturated_fat_energy_ratio,
                    "cap_grade": "C",
                }
            )

    food_group_amounts = daily_totals.get("food_group_amounts_g")
    if isinstance(food_group_amounts, dict):
        has_vegetables = (food_group_amounts.get("vegetables") or 0) > 0
        has_fruits = (food_group_amounts.get("fruits") or 0) > 0
        if not has_vegetables and not has_fruits:
            caps.append(
                {
                    "trigger": "missing_vegetables_and_fruits",
                    "value": food_group_amounts,
                    "cap_grade": "C",
                }
            )

    if "food_group_count" in daily_totals and (daily_totals.get("food_group_count") or 0) <= 2:
        caps.append(
            {
                "trigger": "food_group_count_at_most_2",
                "value": daily_totals.get("food_group_count") or 0,
                "cap_grade": "C",
            }
        )

    data_quality = daily_totals.get("data_quality") or {}
    if data_quality.get("status") == "insufficient":
        caps.append({"trigger": "insufficient_nutrition_data", "value": data_quality, "cap_grade": "C"})
    return caps
