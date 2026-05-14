from __future__ import annotations

from copy import deepcopy
from typing import Any


def target_user_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of target_user for Streamlit form defaults."""
    return deepcopy(payload.get("target_user") or {})


def ingredient_rows_from_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten meals -> dishes -> ingredients into editable table rows."""
    rows: list[dict[str, Any]] = []
    for meal in payload.get("meals", []) or []:
        for dish in meal.get("dishes", []) or []:
            for ingredient in dish.get("ingredients", []) or []:
                rows.append(
                    {
                        "meal_name": meal.get("meal_name", ""),
                        "meal_time": meal.get("meal_time", ""),
                        "dish_name": dish.get("dish_name", ""),
                        "dish_type": dish.get("dish_type", ""),
                        "ingredient_name": ingredient.get("name", ""),
                        "amount_g": ingredient.get("amount_g", 0),
                        "edible": ingredient.get("edible", True),
                    }
                )
    return rows


def condiment_rows_from_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten dish condiments into editable table rows."""
    rows: list[dict[str, Any]] = []
    for meal in payload.get("meals", []) or []:
        for dish in meal.get("dishes", []) or []:
            for condiment in dish.get("condiments", []) or []:
                rows.append(
                    {
                        "meal_name": meal.get("meal_name", ""),
                        "dish_name": dish.get("dish_name", ""),
                        "condiment_name": condiment.get("name", ""),
                        "amount_g": condiment.get("amount_g", 0),
                    }
                )
    return rows


def extra_item_rows_from_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Return extra_items as editable table rows."""
    return [
        {
            "name": item.get("name", ""),
            "amount_g": item.get("amount_g", 0),
            "meal_name": item.get("meal_name", "snack"),
            "meal_time": item.get("meal_time", ""),
            "item_type": item.get("item_type", ""),
        }
        for item in payload.get("extra_items", []) or []
    ]


def build_payload_from_demo_tables(
    *,
    target_user: dict[str, Any],
    ingredient_rows: Any,
    condiment_rows: Any,
    extra_item_rows: Any,
    date: str | None = None,
    record_quality: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the project input JSON from Streamlit table rows."""
    meals: list[dict[str, Any]] = []
    meal_index: dict[str, dict[str, Any]] = {}
    dish_index: dict[tuple[str, str], dict[str, Any]] = {}

    for row in _as_records(ingredient_rows):
        ingredient_name = _clean_text(row.get("ingredient_name") or row.get("name"))
        if not ingredient_name:
            continue
        meal_name = _clean_text(row.get("meal_name")) or "lunch"
        meal_time = _clean_text(row.get("meal_time"))
        dish_name = _clean_text(row.get("dish_name")) or ingredient_name
        dish_type = _clean_text(row.get("dish_type")) or "home_cooked"
        dish = _get_or_create_dish(
            meals,
            meal_index,
            dish_index,
            meal_name=meal_name,
            meal_time=meal_time,
            dish_name=dish_name,
            dish_type=dish_type,
        )
        dish["ingredients"].append(
            {
                "name": ingredient_name,
                "amount_g": _to_float(row.get("amount_g"), default=0.0),
                "edible": _to_bool(row.get("edible"), default=True),
            }
        )

    has_valid_condiments = False
    for row in _as_records(condiment_rows):
        condiment_name = _clean_text(row.get("condiment_name") or row.get("name"))
        if not condiment_name:
            continue
        has_valid_condiments = True
        meal_name = _clean_text(row.get("meal_name")) or "lunch"
        dish_name = _clean_text(row.get("dish_name")) or "未命名菜品"
        dish = _get_or_create_dish(
            meals,
            meal_index,
            dish_index,
            meal_name=meal_name,
            meal_time="",
            dish_name=dish_name,
            dish_type="home_cooked",
        )
        dish["condiments"].append(
            {
                "name": condiment_name,
                "amount_g": _to_float(row.get("amount_g"), default=0.0),
            }
        )

    extra_items = []
    for row in _as_records(extra_item_rows):
        name = _clean_text(row.get("name"))
        if not name:
            continue
        extra_items.append(
            {
                "name": name,
                "amount_g": _to_float(row.get("amount_g"), default=0.0),
                "meal_name": _clean_text(row.get("meal_name")) or "snack",
                "item_type": _clean_text(row.get("item_type")),
            }
        )
        meal_time = _clean_text(row.get("meal_time"))
        if meal_time:
            extra_items[-1]["meal_time"] = meal_time

    output = {
        "evaluation_scope": "whole_day",
        "target_population": "healthy_adult",
        "target_user": _clean_target_user(target_user),
        "meals": meals,
        "extra_items": extra_items,
        "record_quality": record_quality or _default_record_quality(
            has_condiments=has_valid_condiments,
            has_extra_items=bool(extra_items),
        ),
    }
    if date:
        output["date"] = date
    return output


def parse_list_text(value: str) -> list[str]:
    """Parse comma or Chinese-comma separated text into a list."""
    return [part.strip() for part in str(value or "").replace("，", ",").split(",") if part.strip()]


def _get_or_create_dish(
    meals: list[dict[str, Any]],
    meal_index: dict[str, dict[str, Any]],
    dish_index: dict[tuple[str, str], dict[str, Any]],
    *,
    meal_name: str,
    meal_time: str,
    dish_name: str,
    dish_type: str,
) -> dict[str, Any]:
    meal = meal_index.get(meal_name)
    if meal is None:
        meal = {"meal_name": meal_name, "dishes": []}
        if meal_time:
            meal["meal_time"] = meal_time
        meals.append(meal)
        meal_index[meal_name] = meal
    elif meal_time and not meal.get("meal_time"):
        meal["meal_time"] = meal_time

    key = (meal_name, dish_name)
    dish = dish_index.get(key)
    if dish is None:
        dish = {
            "dish_name": dish_name,
            "dish_type": dish_type,
            "ingredients": [],
            "condiments": [],
        }
        meal["dishes"].append(dish)
        dish_index[key] = dish
    return dish


def _clean_target_user(target_user: dict[str, Any]) -> dict[str, Any]:
    output = deepcopy(target_user)
    for key in ("age",):
        if key in output:
            output[key] = int(_to_float(output.get(key), default=0.0))
    for key in ("height_cm", "weight_kg"):
        if key in output:
            output[key] = _to_float(output.get(key), default=0.0)
    for key in ("liked_foods", "disliked_foods", "dietary_restrictions"):
        if isinstance(output.get(key), str):
            output[key] = parse_list_text(output[key])
    return {key: value for key, value in output.items() if value not in (None, "", [])}


def _default_record_quality(has_condiments: bool, has_extra_items: bool) -> dict[str, Any]:
    return {
        "has_ingredient_weights": True,
        "has_condiments": has_condiments,
        "has_snacks_and_drinks": has_extra_items,
        "completeness": "complete",
    }


def _as_records(table: Any) -> list[dict[str, Any]]:
    if table is None:
        return []
    if hasattr(table, "to_dict"):
        return table.to_dict("records")
    return [dict(row) for row in table]


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _to_float(value: Any, default: float) -> float:
    if value in (None, ""):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_bool(value: Any, default: bool) -> bool:
    if value in (None, ""):
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y", "是"}:
        return True
    if text in {"false", "0", "no", "n", "否"}:
        return False
    return default
