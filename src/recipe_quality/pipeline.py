from __future__ import annotations

from collections.abc import Callable
from typing import Any

from recipe_quality.aggregator import resolve_and_aggregate
from recipe_quality.ai_annotation import annotate_recipe_input
from recipe_quality.engine import evaluate_daily_diet
from recipe_quality.fatsecret import FatSecretClient, FatSecretResolver
from recipe_quality.normalizer import normalize_recipe_input


ProgressCallback = Callable[[str, str], None]


def evaluate_full_pipeline(
    payload: dict[str, Any],
    progress_callback: ProgressCallback | None = None,
    resolver: Any | None = None,
) -> dict[str, Any]:
    """Run AI annotation, nutrition resolution, aggregation, and scoring."""
    _emit(progress_callback, "ai_annotation", "AI 标注食物组、英文检索名和烹调方式。")
    annotated = annotate_recipe_input(payload)

    _emit(progress_callback, "normalization", "标准化餐次、菜品、食材和调味品。")
    normalized = normalize_recipe_input(annotated)

    _emit(progress_callback, "nutrition_resolution", "查询 FatSecret 并汇总全天营养。")
    resolver = resolver or FatSecretResolver(FatSecretClient())
    resolved = resolve_and_aggregate(
        resolver,
        normalized["ingredient_records"],
        normalized["condiments"],
        dish_records=normalized["dish_records"],
        record_quality=payload.get("record_quality"),
    )

    _emit(progress_callback, "scoring", "运行本地评分规则和等级封顶规则。")
    enriched = {
        **annotated,
        "items": resolved["items"],
        "ingredient_records": resolved["ingredient_records"],
        "dish_records": resolved["dish_records"],
        "daily_totals": resolved["daily_totals"],
    }
    evaluation = evaluate_daily_diet(enriched)

    _emit(progress_callback, "completed", "完整流程处理完成。")
    return build_pipeline_summary(annotated, resolved, evaluation)


def build_pipeline_summary(
    annotated: dict[str, Any],
    resolved: dict[str, Any],
    evaluation: dict[str, Any],
) -> dict[str, Any]:
    """Build the compact JSON summary used by scripts and the demo UI."""
    daily_totals = resolved["daily_totals"]
    return {
        "ai_warnings": annotated.get("ai_annotation_meta", {}).get("warnings", []),
        "resolved_items": [
            {
                "name": item.get("name"),
                "meal_name": item.get("meal_name"),
                "search_name": item.get("search_name"),
                "food_group": item.get("food_group"),
                "processing_level": item.get("processing_level"),
                "fatsecret_food_name": item.get("fatsecret_food_name"),
                "serving_used": item.get("serving_used"),
                "status": item.get("nutrition_estimation_status"),
                "nutrients": item.get("nutrients"),
                "error": item.get("error"),
            }
            for item in resolved["items"]
        ],
        "daily_totals": {
            key: daily_totals.get(key)
            for key in [
                "energy_kcal",
                "protein_g",
                "fat_g",
                "saturated_fat_g",
                "carbohydrate_g",
                "fiber_g",
                "sodium_mg",
                "calcium_mg",
                "iron_mg",
                "vitamin_c_mg",
                "cooking_oil_g",
                "added_sugar_g",
                "food_group_amounts_g",
                "food_group_count",
                "data_quality",
            ]
        },
        "total_score": evaluation["total_score"],
        "raw_grade": evaluation["raw_grade"],
        "final_grade": evaluation["final_grade"],
        "module_scores": evaluation["module_scores"],
        "grade_caps": evaluation["grade_caps"],
    }


def _emit(callback: ProgressCallback | None, step_key: str, message: str) -> None:
    if callback is not None:
        callback(step_key, message)
