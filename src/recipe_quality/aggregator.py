from __future__ import annotations

from typing import Any

from recipe_quality.models import NUTRIENT_KEYS, ResolvedFoodItem
from recipe_quality.utils.units import salt_g_to_sodium_mg


COOKING_OIL_NAMES = {
    "油",
    "烹调油",
    "食用油",
    "植物油",
    "食用植物油",
    "菜籽油",
    "花生油",
    "芝麻油",
    "香油",
    "橄榄油",
    "大豆油",
    "玉米油",
    "葵花籽油",
    "调和油",
    "熟油",
    "色拉油",
    "cooking oil",
    "oil",
}
SALT_NAMES = {"盐", "食盐", "碘盐", "精盐", "海盐", "粗盐", "salt"}
SOY_SAUCE_NAMES = {"酱油", "生抽", "老抽", "蒸鱼豉油", "豉油", "味极鲜", "soy sauce"}
LOW_SODIUM_SOY_SAUCE_NAMES = {"低钠酱油", "薄盐酱油", "减盐酱油"}
SOY_SAUCE_SODIUM_MG_PER_G = 65.0
LOW_SODIUM_SOY_SAUCE_SODIUM_MG_PER_G = 35.0


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
        classification = _classify_condiment_name(name)
        sodium_mg = _to_float(condiment.get("sodium_mg"))
        if sodium_mg is not None:
            totals["sodium_mg"] += sodium_mg
        elif classification == "salt":
            totals["sodium_mg"] += salt_g_to_sodium_mg(amount_g)
        elif classification == "soy_sauce":
            totals["sodium_mg"] += amount_g * SOY_SAUCE_SODIUM_MG_PER_G
        elif classification == "low_sodium_soy_sauce":
            totals["sodium_mg"] += amount_g * LOW_SODIUM_SOY_SAUCE_SODIUM_MG_PER_G
        if classification == "cooking_oil":
            totals["cooking_oil_g"] += amount_g
        if classification == "added_sugar":
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
    totals["ingredient_records"] = [item.to_dict() for item in resolved_items]
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


def _classify_condiment_name(name: str) -> str | None:
    """标准化常见调味品名称，供限制性成分汇总使用。"""
    normalized = _normalize_condiment_name(name)
    if normalized in COOKING_OIL_NAMES:
        return "cooking_oil"
    if normalized in SALT_NAMES:
        return "salt"
    if normalized in LOW_SODIUM_SOY_SAUCE_NAMES:
        return "low_sodium_soy_sauce"
    if normalized in SOY_SAUCE_NAMES:
        return "soy_sauce"
    if normalized in {"糖", "白糖", "添加糖", "sugar"}:
        return "added_sugar"
    return None


def _normalize_condiment_name(name: str) -> str:
    return " ".join(str(name or "").strip().casefold().split())


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
