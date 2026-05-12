from __future__ import annotations

from typing import Any


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def extract_foods(search_payload: dict[str, Any]) -> list[dict[str, Any]]:
    foods = search_payload.get("foods") or {}
    return as_list(foods.get("food"))


def extract_food(food_payload: dict[str, Any]) -> dict[str, Any]:
    return food_payload.get("food") or {}


def extract_servings(food_payload: dict[str, Any]) -> list[dict[str, Any]]:
    food = extract_food(food_payload)
    servings = food.get("servings") or {}
    return as_list(servings.get("serving"))

