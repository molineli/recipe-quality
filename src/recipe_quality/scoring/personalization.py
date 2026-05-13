from __future__ import annotations

from typing import Any

from recipe_quality.normalizer import normalize_recipe_input


LIKE_SINGLE_MATCH_SCORE = 1.5
UNHEALTHY_LIKED_FOOD_METHODS = {
    "deep_fry",
    "reused_oil_fry",
    "heavy_grill",
    "charred",
    "sugar_glazed",
    "candied",
    "dry_pot",
    "braise_heavy_oil",
    "cold_mix_heavy_sauce",
}
HOME_COOKING_METHODS = {
    "steam",
    "boil",
    "blanch",
    "poach",
    "stew_clear",
    "soup",
    "porridge_or_cooked_grain",
    "pressure_cook",
    "microwave",
    "cold_mix_low_oil",
    "ready_to_eat_minimal",
    "bake_low_oil",
    "air_fry",
    "pan_fry_low_oil",
    "stir_fry_low_oil",
    "stir_fry",
    "braise_light",
}
PROTEIN_GROUPS = {
    "livestock_poultry_meat",
    "aquatic_products",
    "eggs",
    "dairy",
    "soy_products",
}
COMPLEX_METHODS = {
    "sous_vide_safe",
    "smoke",
    "salt_baked_or_salt_cured",
    "candied",
    "reused_oil_fry",
    "heavy_grill",
}


def score_personalization(input_data: dict) -> tuple[float, dict]:
    """Calculate the E module score from recipe facts, not direct AI scores.

    AI or upstream parsing may provide structured labels such as liked foods,
    habit match level, and feasibility factors. This function still computes
    E1, E2, and E3 deterministically from those labels and the normalized
    recipe records.
    """
    normalized = normalize_recipe_input(input_data)
    target_user = input_data.get("target_user") or {}
    warnings: list[str] = []

    liked_score, liked_details = score_liked_foods(
        target_user=target_user,
        ingredient_records=normalized["ingredient_records"],
        dish_records=normalized["dish_records"],
        warnings=warnings,
    )
    habit_score, habit_details = score_habit_match(
        input_data=input_data,
        target_user=target_user,
        ingredient_records=normalized["ingredient_records"],
        dish_records=normalized["dish_records"],
        warnings=warnings,
    )
    feasibility_score, feasibility_details = score_feasibility(
        input_data=input_data,
        dish_records=normalized["dish_records"],
        warnings=warnings,
    )

    total = round(liked_score + habit_score + feasibility_score, 2)
    details = {
        "score": total,
        "max_score": 8,
        "liked_foods_reasonable_use": round(liked_score, 2),
        "habit_match": round(habit_score, 2),
        "feasibility": round(feasibility_score, 2),
        "liked_foods_details": liked_details,
        "habit_match_details": habit_details,
        "feasibility_details": feasibility_details,
        "warnings": warnings,
    }
    return total, details


def score_liked_foods(
    target_user: dict[str, Any],
    ingredient_records: list[dict[str, Any]],
    dish_records: list[dict[str, Any]],
    warnings: list[str],
) -> tuple[float, dict[str, Any]]:
    """Score E1 by checking whether preferred foods are used reasonably.

    A matched liked food adds personalization value, while risky cooking
    methods or ultra-processed liked ingredients cap this subscore. The
    function returns both the numeric score and evidence for explanation.
    """
    liked_foods = _string_list(target_user.get("liked_foods"))
    if not liked_foods:
        warnings.append("E1 liked foods score is 0 because target_user.liked_foods is empty.")
        return 0.0, {"liked_foods": [], "matched_foods": [], "risk_limited": False}

    dish_method_by_name = {
        dish.get("dish_name"): dish.get("cooking_method") for dish in dish_records if dish.get("dish_name")
    }
    matched: list[dict[str, Any]] = []
    for ingredient in ingredient_records:
        name = str(ingredient.get("name") or "").strip()
        if not name:
            continue
        matched_likes = _string_list(ingredient.get("liked_food_matches"))
        match_source = "ai_label" if matched_likes else "name_fallback"
        if not matched_likes:
            matched_likes = [liked for liked in liked_foods if _food_name_matches(name, liked)]
        if not matched_likes:
            continue
        cooking_method = dish_method_by_name.get(ingredient.get("dish_name"))
        processing_level = ingredient.get("processing_level")
        use_quality = ingredient.get("liked_food_use_quality")
        risky = (
            use_quality == "risky"
            or cooking_method in UNHEALTHY_LIKED_FOOD_METHODS
            or processing_level == "ultra_processed"
        )
        matched.append(
            {
                "name": name,
                "matched_liked_foods": matched_likes,
                "match_source": match_source,
                "dish_name": ingredient.get("dish_name"),
                "cooking_method": cooking_method,
                "processing_level": processing_level,
                "liked_food_use_quality": use_quality,
                "risky_use": risky,
            }
        )

    distinct_matches = {
        liked for match in matched for liked in match["matched_liked_foods"]
    }
    if not distinct_matches:
        return 0.0, {"liked_foods": liked_foods, "matched_foods": [], "risk_limited": False}

    score = 3.0 if len(distinct_matches) >= 2 else LIKE_SINGLE_MATCH_SCORE
    risky_count = sum(1 for match in matched if match["risky_use"])
    risk_limited = risky_count >= max(1, len(matched) / 2)
    if risk_limited:
        score = min(score, 1.0)
        warnings.append("E1 liked foods score was capped at 1 because liked foods mainly used risky methods or ultra-processed ingredients.")

    return round(score, 2), {
        "liked_foods": liked_foods,
        "matched_liked_food_count": len(distinct_matches),
        "matched_foods": matched,
        "risk_limited": risk_limited,
    }


def score_habit_match(
    input_data: dict[str, Any],
    target_user: dict[str, Any],
    ingredient_records: list[dict[str, Any]],
    dish_records: list[dict[str, Any]],
    warnings: list[str],
) -> tuple[float, dict[str, Any]]:
    """Score E2 by matching the day against the user's usual eating pattern.

    If an upstream structured `habit_match_level` exists, use it as a label
    and convert it to points. Otherwise, apply a small ruleset for the current
    `chinese_home_meals` pattern.
    """
    habit_pattern = target_user.get("habit_pattern")
    explicit_level = input_data.get("habit_match_level") or target_user.get("habit_match_level")
    if explicit_level:
        score = _habit_level_score(str(explicit_level))
        if score is not None:
            return score, {
                "habit_pattern": habit_pattern,
                "match_level": explicit_level,
                "source": "explicit_label",
            }
        warnings.append(f"E2 ignored unsupported habit_match_level={explicit_level}.")

    if habit_pattern == "chinese_home_meals":
        groups = {item.get("food_group") for item in ingredient_records if item.get("edible", True)}
        methods = {dish.get("cooking_method") for dish in dish_records}
        signals = {
            "has_staple": "grains_and_tubers" in groups,
            "has_protein_dish": bool(groups & PROTEIN_GROUPS),
            "has_vegetable": "vegetables" in groups,
            "has_home_cooking_method": bool(methods & HOME_COOKING_METHODS),
        }
        signal_count = sum(signals.values())
        if signal_count >= 3:
            return 2.0, {"habit_pattern": habit_pattern, "match_level": "full", "signals": signals}
        if signal_count >= 2:
            return 1.0, {"habit_pattern": habit_pattern, "match_level": "partial", "signals": signals}
        return 0.0, {"habit_pattern": habit_pattern, "match_level": "mismatch", "signals": signals}

    if habit_pattern:
        warnings.append(f"E2 habit pattern {habit_pattern} has no rule yet; used neutral partial score.")
        return 1.0, {"habit_pattern": habit_pattern, "match_level": "unknown", "source": "fallback"}

    warnings.append("E2 habit match score is 0 because target_user.habit_pattern is missing.")
    return 0.0, {"habit_pattern": None, "match_level": "missing"}


def score_feasibility(
    input_data: dict[str, Any],
    dish_records: list[dict[str, Any]],
    warnings: list[str],
) -> tuple[float, dict[str, Any]]:
    """Score E3 by subtracting execution-burden penalties from 3 points.

    Structured `feasibility` factors are preferred. When they are absent, the
    function falls back to recipe-level signals such as dish count and complex
    cooking methods.
    """
    feasibility = input_data.get("feasibility") or {}
    penalties: list[str] = []

    prep_time = _to_float(feasibility.get("estimated_prep_time_min"))
    if prep_time is not None and prep_time > 60:
        penalties.append("prep_time_over_60_min")
    if feasibility.get("step_complexity") == "complex":
        penalties.append("complex_steps")
    if feasibility.get("ingredient_availability") == "hard_to_find":
        penalties.append("hard_to_find_ingredients")
    if feasibility.get("cost_level") == "high":
        penalties.append("high_cost")
    if feasibility.get("special_equipment_required") is True:
        penalties.append("special_equipment_required")

    if not feasibility:
        dish_count = len(dish_records)
        complex_method_count = sum(
            1 for dish in dish_records if dish.get("cooking_method") in COMPLEX_METHODS
        )
        if dish_count > 6:
            penalties.append("many_dishes")
        if complex_method_count:
            penalties.append("complex_cooking_methods")
        source = "recipe_fallback"
    else:
        source = "structured_factors"

    score = max(3.0 - len(penalties), 0.0)
    if not feasibility and not dish_records:
        warnings.append("E3 feasibility score is 0 because no dishes or feasibility factors were provided.")
        score = 0.0

    return round(score, 2), {
        "source": source,
        "penalties": penalties,
        "estimated_prep_time_min": prep_time,
        "step_complexity": feasibility.get("step_complexity"),
        "ingredient_availability": feasibility.get("ingredient_availability"),
        "cost_level": feasibility.get("cost_level"),
        "special_equipment_required": feasibility.get("special_equipment_required"),
    }


def _habit_level_score(level: str) -> float | None:
    """Convert a normalized habit-match label into E2 points."""
    return {
        "full": 2.0,
        "partial": 1.0,
        "mismatch": 0.0,
        "unknown": 1.0,
    }.get(level)


def _food_name_matches(ingredient_name: str, liked_food: str) -> bool:
    """Return whether an ingredient name is a practical match for a liked food."""
    ingredient = ingredient_name.strip().lower()
    liked = liked_food.strip().lower()
    return bool(ingredient and liked and (ingredient == liked or ingredient in liked or liked in ingredient))


def _string_list(value: Any) -> list[str]:
    """Normalize a user-provided list-like field to non-empty strings."""
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _to_float(value: Any) -> float | None:
    """Safely convert optional structured input values to float."""
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
