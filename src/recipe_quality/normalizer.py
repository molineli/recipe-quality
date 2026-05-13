from __future__ import annotations

from typing import Any


def normalize_recipe_input(payload: dict[str, Any]) -> dict[str, Any]:
    """将统一食谱输入标准化为原料、菜品和调味品三类记录。"""
    ingredient_records: list[dict[str, Any]] = []
    dish_records: list[dict[str, Any]] = []
    condiments: list[dict[str, Any]] = []

    for meal in payload.get("meals", []) or []:
        meal_name = meal.get("meal_name")
        meal_time = meal.get("meal_time")
        for dish_index, dish in enumerate(meal.get("dishes", []) or []):
            dish_name = dish.get("dish_name") or f"dish_{dish_index + 1}"
            dish_condiments = [
                {**condiment, "meal_name": meal_name, "dish_name": dish_name}
                for condiment in dish.get("condiments", []) or []
            ]
            condiments.extend(dish_condiments)
            ingredients = []
            for ingredient_index, ingredient in enumerate(dish.get("ingredients", []) or []):
                record = _ingredient_record(
                    ingredient=ingredient,
                    meal_name=meal_name,
                    meal_time=meal_time,
                    dish_name=dish_name,
                    ingredient_index=ingredient_index,
                )
                ingredient_records.append(record)
                ingredients.append(record)
            dish_records.append(
                {
                    "dish_name": dish_name,
                    "meal_name": meal_name,
                    "meal_time": meal_time,
                    "dish_type": dish.get("dish_type"),
                    "total_weight_g": sum(
                        float(item.get("amount_g") or 0)
                        for item in ingredients
                        if item.get("edible", True)
                    ),
                    "cooking_method": dish.get("cooking_method", "unknown_cooking_method"),
                    "cooking_method_source": dish.get("cooking_method_source"),
                    "cooking_method_confidence": dish.get("cooking_method_confidence"),
                    "food_safety_risk_tags": dish.get("food_safety_risk_tags", []) or [],
                    "condiments": dish_condiments,
                }
            )

    for item_index, item in enumerate(payload.get("extra_items", []) or []):
        meal_name = item.get("meal_name", "extra")
        ingredient_records.append(
            _ingredient_record(
                ingredient=item,
                meal_name=meal_name,
                meal_time=item.get("meal_time"),
                dish_name=item.get("dish_name") or item.get("name"),
                ingredient_index=item_index,
            )
        )

    # Backward compatibility for the original flat items input.
    for item_index, item in enumerate(payload.get("items", []) or []):
        if item.get("nutrients") or not payload.get("meals"):
            ingredient_records.append(
                _ingredient_record(
                    ingredient=item,
                    meal_name=item.get("meal_name"),
                    meal_time=item.get("meal_time"),
                    dish_name=item.get("dish_name") or item.get("name"),
                    ingredient_index=item_index,
                )
            )

    condiments.extend(payload.get("condiments", []) or [])
    return {
        "ingredient_records": ingredient_records,
        "dish_records": dish_records,
        "condiments": condiments,
    }


def _ingredient_record(
    ingredient: dict[str, Any],
    meal_name: str | None,
    meal_time: str | None,
    dish_name: str | None,
    ingredient_index: int,
) -> dict[str, Any]:
    """将单个输入原料转换为内部 Ingredient Record。"""
    name = str(ingredient.get("name") or "").strip()
    amount_g = float(ingredient.get("amount_g") or 0)
    safe_meal = meal_name or "unknown_meal"
    safe_dish = dish_name or "unknown_dish"
    safe_name = name or f"ingredient_{ingredient_index + 1}"
    return {
        "ingredient_id": ingredient.get("ingredient_id")
        or f"{safe_meal}:{safe_dish}:{safe_name}:{ingredient_index + 1}",
        "meal_name": meal_name,
        "meal_time": meal_time,
        "dish_name": dish_name,
        "name": name,
        "amount_g": amount_g,
        "edible": ingredient.get("edible", True),
        "food_group": ingredient.get("food_group"),
        "classification_source": ingredient.get("classification_source"),
        "classification_confidence": ingredient.get("classification_confidence"),
        "processing_level": ingredient.get("processing_level"),
        "processing_level_source": ingredient.get("processing_level_source"),
        "processing_level_confidence": ingredient.get("processing_level_confidence"),
        "fatsecret_food_id": ingredient.get("fatsecret_food_id"),
        "nutrients": ingredient.get("nutrients"),
        "nutrition_estimation_status": ingredient.get("nutrition_estimation_status"),
    }
