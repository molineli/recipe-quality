from __future__ import annotations

from typing import Any

from recipe_quality.aggregator import aggregate_daily_totals
from recipe_quality.models import Nutrients, ResolvedFoodItem
from recipe_quality.normalizer import normalize_recipe_input
from recipe_quality.scoring.basic_nutrition import score_basic_nutrition
from recipe_quality.scoring.cooking_processing_safety import score_cooking_processing_safety
from recipe_quality.scoring.daily_intake_fit import score_daily_intake_fit
from recipe_quality.scoring.grade import apply_grade_caps, evaluate_grade_caps, score_to_grade
from recipe_quality.scoring.limiting_components import score_limiting_components
from recipe_quality.scoring.personalization import score_personalization
from recipe_quality.targets import resolve_daily_targets


def evaluate_daily_diet(input_data: dict[str, Any]) -> dict[str, Any]:
    """执行全天饮食评分主流程，返回总分、等级、模块分和封顶信息。"""
    resolved_targets = resolve_daily_targets(input_data.get("target_user"))
    if "daily_totals" in input_data:
        daily_totals = input_data["daily_totals"]
    else:
        normalized = normalize_recipe_input(input_data)
        resolved_items = [
            ResolvedFoodItem(
                name=item.get("name", ""),
                amount_g=float(item.get("amount_g") or 0),
                ingredient_id=item.get("ingredient_id"),
                meal_name=item.get("meal_name"),
                dish_name=item.get("dish_name"),
                edible=item.get("edible", True),
                food_group=item.get("food_group"),
                classification_source=item.get("classification_source"),
                classification_confidence=item.get("classification_confidence"),
                nutrients=Nutrients.from_mapping(item.get("nutrients")),
                nutrition_estimation_status=item.get("nutrition_estimation_status", "resolved"),
            )
            for item in normalized["ingredient_records"]
        ]
        daily_totals = aggregate_daily_totals(
            resolved_items,
            normalized["condiments"],
            dish_records=normalized["dish_records"],
            record_quality=input_data.get("record_quality"),
        )

    basic, basic_details = score_basic_nutrition(
        daily_totals,
        resolved_targets,
        target_user=input_data.get("target_user"),
    )
    limiting, limiting_details = score_limiting_components(daily_totals, resolved_targets)
    cooking, cooking_details = score_cooking_processing_safety(input_data)
    intake, intake_details = score_daily_intake_fit(daily_totals, resolved_targets)
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
    grade_caps = evaluate_grade_caps(daily_totals, resolved_targets)
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
        "daily_targets": resolved_targets,
        "grade_caps": grade_caps,
    }
