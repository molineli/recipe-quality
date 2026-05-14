from __future__ import annotations


GRADE_ORDER = ["A", "B", "C", "D", "E"]
LIMITED_COMPONENTS = (
    ("sodium_mg", "sodium_mg_limit", "sodium"),
    ("cooking_oil_g", "cooking_oil_g_limit", "cooking_oil"),
    ("added_sugar_g", "added_sugar_g_limit", "added_sugar"),
)
MAIN_MEAL_ALIASES = {
    "breakfast": "breakfast",
    "早餐": "breakfast",
    "早饭": "breakfast",
    "lunch": "lunch",
    "午餐": "lunch",
    "午饭": "lunch",
    "dinner": "dinner",
    "晚餐": "dinner",
    "晚饭": "dinner",
}
SNACK_MEAL_NAMES = {"snack", "snacks", "零食", "加餐", "点心"}


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

    ingredient_records = daily_totals.get("ingredient_records") or []
    edible_weight_g = _edible_weight_g(ingredient_records)
    if edible_weight_g is not None:
        if edible_weight_g < 600 or edible_weight_g > 3500:
            caps.append(
                {
                    "trigger": "edible_weight_outside_range",
                    "value": edible_weight_g,
                    "cap_grade": "D",
                }
            )
        if edible_weight_g > 0 and energy:
            energy_density = energy / edible_weight_g
            if energy_density < 0.3 or energy_density > 3.5:
                caps.append(
                    {
                        "trigger": "energy_density_outside_range",
                        "value": energy_density,
                        "cap_grade": "D",
                    }
                )

    meal_energy = _meal_energy_by_name(ingredient_records)
    if energy and meal_energy:
        max_meal_ratio = max(meal_energy.values()) / energy
        if max_meal_ratio > 0.80:
            caps.append(
                {
                    "trigger": "max_meal_energy_ratio_above_80_percent",
                    "value": max_meal_ratio,
                    "cap_grade": "E",
                }
            )
        elif max_meal_ratio > 0.70:
            caps.append(
                {
                    "trigger": "max_meal_energy_ratio_above_70_percent",
                    "value": max_meal_ratio,
                    "cap_grade": "D",
                }
            )

        snack_energy = meal_energy.get("snack", 0.0)
        snack_ratio = snack_energy / energy
        if snack_ratio > 0.50:
            caps.append(
                {
                    "trigger": "snack_energy_ratio_above_50_percent",
                    "value": snack_ratio,
                    "cap_grade": "D",
                }
            )

        main_meal_names = {"breakfast", "lunch", "dinner"}
        if main_meal_names.issubset(meal_energy):
            main_meal_ratios = {meal: meal_energy[meal] / energy for meal in main_meal_names}
            abnormal_main_meals = [
                meal
                for meal, ratio in main_meal_ratios.items()
                if (
                    (meal == "breakfast" and (ratio < 0.10 or ratio > 0.50))
                    or (meal == "lunch" and (ratio < 0.15 or ratio > 0.60))
                    or (meal == "dinner" and (ratio < 0.15 or ratio > 0.55))
                )
            ]
            if abnormal_main_meals:
                caps.append(
                    {
                        "trigger": "main_meal_energy_ratio_abnormal",
                        "value": main_meal_ratios,
                        "cap_grade": "C",
                    }
                )

            sorted_main_ratios = sorted(main_meal_ratios.values())
            if sorted_main_ratios[0] < 0.05 and sorted_main_ratios[1] + sorted_main_ratios[2] > 0.90:
                caps.append(
                    {
                        "trigger": "two_main_meals_energy_ratio_above_90_percent",
                        "value": main_meal_ratios,
                        "cap_grade": "D",
                    }
                )

    data_quality = daily_totals.get("data_quality") or {}
    if data_quality.get("status") == "insufficient":
        caps.append({"trigger": "insufficient_nutrition_data", "value": data_quality, "cap_grade": "C"})
    return caps


def _edible_weight_g(ingredient_records: list[dict]) -> float | None:
    if not ingredient_records:
        return None
    weight = 0.0
    has_amount = False
    for item in ingredient_records:
        if not item.get("edible", True):
            continue
        amount = _to_float(item.get("amount_g"))
        if amount is None:
            continue
        weight += amount
        has_amount = True
    return round(weight, 2) if has_amount else None


def _meal_energy_by_name(ingredient_records: list[dict]) -> dict[str, float]:
    meal_energy: dict[str, float] = {}
    for item in ingredient_records:
        if not item.get("edible", True):
            continue
        meal_name = _canonical_meal_name(item.get("meal_name"))
        if meal_name is None:
            continue
        energy = _record_energy(item)
        if energy is None:
            continue
        meal_energy[meal_name] = meal_energy.get(meal_name, 0.0) + energy
    return meal_energy


def _canonical_meal_name(value: object) -> str | None:
    text = str(value or "").strip().lower()
    if not text:
        return None
    if text in MAIN_MEAL_ALIASES:
        return MAIN_MEAL_ALIASES[text]
    if text in SNACK_MEAL_NAMES:
        return "snack"
    return None


def _record_energy(record: dict) -> float | None:
    nutrients = record.get("nutrients") or {}
    if isinstance(nutrients, dict):
        energy = _to_float(nutrients.get("energy_kcal"))
        if energy is not None:
            return energy
    return _to_float(record.get("energy_kcal"))


def _to_float(value: object) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
