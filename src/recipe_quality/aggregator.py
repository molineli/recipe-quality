from __future__ import annotations

from typing import Any

from recipe_quality.models import NUTRIENT_KEYS, ResolvedFoodItem
from recipe_quality.utils.units import salt_g_to_sodium_mg


def aggregate_daily_totals(
    resolved_items: list[ResolvedFoodItem],
    condiments: list[dict[str, Any]] | None = None,
    dish_records: list[dict[str, Any]] | None = None,
    record_quality: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """汇总全天食物和调味品的营养数据，生成 daily_totals。"""
    totals: dict[str, Any] = {key: 0.0 for key in NUTRIENT_KEYS}
    missing_nutrients: set[str] = set()
    food_group_amounts: dict[str, float] = {}
    unclassified_ingredients: list[str] = []
    dish_nutrients: dict[tuple[str | None, str | None], dict[str, float]] = {}

    for item in resolved_items:
        dish_key = (item.meal_name, item.dish_name)
        if item.dish_name:
            dish_nutrients.setdefault(dish_key, {"energy_kcal": 0.0, "total_weight_g": 0.0})
            dish_nutrients[dish_key]["total_weight_g"] += item.amount_g if item.edible else 0.0
        if item.food_group and item.edible:
            food_group_amounts[item.food_group] = food_group_amounts.get(item.food_group, 0.0) + item.amount_g
        elif item.edible:
            unclassified_ingredients.append(item.name)
        nutrients = item.nutrients.to_dict()
        for key in NUTRIENT_KEYS:
            value = nutrients.get(key)
            if value is None:
                missing_nutrients.add(key)
                continue
            totals[key] += value
            if item.dish_name and key == "energy_kcal":
                dish_nutrients[dish_key]["energy_kcal"] += value

    totals["cooking_oil_g"] = 0.0
    for condiment in condiments or []:
        name = str(condiment.get("name") or "").strip()
        amount_g = _to_float(condiment.get("amount_g"))
        if amount_g is None:
            continue
        sodium_mg = _to_float(condiment.get("sodium_mg"))
        if sodium_mg is not None:
            totals["sodium_mg"] += sodium_mg
        elif name in {"盐", "食盐", "salt"}:
            totals["sodium_mg"] += salt_g_to_sodium_mg(amount_g)
        if name in {"油", "烹调油", "食用油", "cooking oil", "oil"}:
            totals["cooking_oil_g"] += amount_g
        if name in {"糖", "白糖", "添加糖", "sugar"}:
            totals["added_sugar_g"] += amount_g

    unresolved_items = [
        item.name for item in resolved_items if item.nutrition_estimation_status != "resolved"
    ]
    record_quality = record_quality or {}
    quality_status = "complete"
    if unresolved_items or unclassified_ingredients:
        quality_status = "insufficient"
    if record_quality.get("completeness") in {"incomplete", "missing"}:
        quality_status = "insufficient"
    effective_groups = {
        group
        for group, amount in food_group_amounts.items()
        if amount >= 10 and group not in {"condiments", "beverages", "sweets_snacks", "other", "unknown"}
    }
    totals["food_group_amounts_g"] = food_group_amounts
    totals["food_group_count"] = len(effective_groups)
    totals["dish_records"] = enrich_dish_records(dish_records or [], dish_nutrients)
    totals["data_quality"] = {
        "unresolved_items": unresolved_items,
        "unresolved_nutrition_items": unresolved_items,
        "unclassified_ingredients": unclassified_ingredients,
        "missing_nutrients": sorted(missing_nutrients),
        "record_quality": record_quality,
        "status": quality_status,
    }
    return totals


def enrich_dish_records(
    dish_records: list[dict[str, Any]],
    dish_nutrients: dict[tuple[str | None, str | None], dict[str, float]],
) -> list[dict[str, Any]]:
    """将按原料汇总出的菜品能量和重量补回 Dish Records。"""
    enriched = []
    for dish in dish_records:
        key = (dish.get("meal_name"), dish.get("dish_name"))
        nutrients = dish_nutrients.get(key, {})
        enriched.append(
            {
                **dish,
                "total_weight_g": round(
                    nutrients.get("total_weight_g", dish.get("total_weight_g", 0.0)), 2
                ),
                "energy_kcal": round(nutrients.get("energy_kcal", 0.0), 2),
            }
        )
    return enriched


def resolve_and_aggregate(
    resolver: Any,
    items: list[dict[str, Any]],
    condiments: list[dict[str, Any]] | None = None,
    dish_records: list[dict[str, Any]] | None = None,
    record_quality: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """调用解析器解析食物列表，并进一步汇总全天营养指标。"""
    resolved_items = resolver.resolve_items(items)
    return {
        "items": [item.to_dict() for item in resolved_items],
        "ingredient_records": [item.to_dict() for item in resolved_items],
        "dish_records": dish_records or [],
        "daily_totals": aggregate_daily_totals(
            resolved_items,
            condiments,
            dish_records=dish_records,
            record_quality=record_quality,
        ),
    }


def _to_float(value: Any) -> float | None:
    """将调味品等输入值安全转换为浮点数。"""
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
