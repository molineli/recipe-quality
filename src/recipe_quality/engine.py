from __future__ import annotations

from typing import Any

from recipe_quality.aggregator import aggregate_daily_totals
from recipe_quality.models import Nutrients, ResolvedFoodItem
from recipe_quality.scoring.basic_nutrition import score_basic_nutrition
from recipe_quality.scoring.cooking_processing_safety import score_cooking_processing_safety
from recipe_quality.scoring.daily_intake_fit import score_daily_intake_fit
from recipe_quality.scoring.grade import apply_grade_caps, evaluate_grade_caps, score_to_grade
from recipe_quality.scoring.limiting_components import score_limiting_components
from recipe_quality.scoring.personalization import score_personalization


def evaluate_daily_diet(input_data: dict[str, Any]) -> dict[str, Any]:
    daily_targets = input_data.get("daily_targets") or {}
    if "daily_totals" in input_data:
        daily_totals = input_data["daily_totals"]
    else:
        resolved_items = [
            ResolvedFoodItem(
                name=item.get("name", ""),
                amount_g=float(item.get("amount_g") or 0),
                meal_name=item.get("meal_name"),
                nutrients=Nutrients.from_mapping(item.get("nutrients")),
                nutrition_estimation_status=item.get("nutrition_estimation_status", "resolved"),
            )
            for item in input_data.get("items", [])
        ]
        daily_totals = aggregate_daily_totals(resolved_items, input_data.get("condiments"))

    basic, basic_details = score_basic_nutrition(daily_totals, daily_targets)
    limiting, limiting_details = score_limiting_components(daily_totals, daily_targets)
    cooking, cooking_details = score_cooking_processing_safety(input_data)
    intake, intake_details = score_daily_intake_fit(daily_totals, daily_targets)
    personalization, personalization_details = score_personalization(input_data)

    module_scores = {
        "basic_nutrition_quality": basic,
        "limiting_components": limiting,
        "cooking_processing_safety": cooking,
        "daily_intake_fit": intake,
        "personalization_feasibility": personalization,
    }
    total_score = round(sum(module_scores.values()), 2)
    raw_grade = score_to_grade(total_score)
    grade_caps = evaluate_grade_caps(daily_totals, daily_targets)
    final_grade = apply_grade_caps(raw_grade, grade_caps)
    return {
        "evaluation_scope": input_data.get("evaluation_scope", "whole_day"),
        "target_population": input_data.get("target_population", "healthy_adult"),
        "total_score": total_score,
        "raw_grade": raw_grade,
        "final_grade": final_grade,
        "module_scores": module_scores,
        "module_details": {
            "basic_nutrition_quality": basic_details,
            "limiting_components": limiting_details,
            "cooking_processing_safety": cooking_details,
            "daily_intake_fit": intake_details,
            "personalization_feasibility": personalization_details,
        },
        "daily_totals": daily_totals,
        "grade_caps": grade_caps,
    }

