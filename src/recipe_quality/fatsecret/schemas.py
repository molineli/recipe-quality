from __future__ import annotations

from typing import Any


def as_list(value: Any) -> list[Any]:
    """将 FatSecret 可能返回的单对象或列表统一转换为列表。"""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def extract_foods(search_payload: dict[str, Any]) -> list[dict[str, Any]]:
    """从 foods.search 响应中提取食物候选列表。"""
    foods = search_payload.get("foods") or {}
    return as_list(foods.get("food"))


def extract_food(food_payload: dict[str, Any]) -> dict[str, Any]:
    """从 food.get 响应中提取食物主体对象。"""
    return food_payload.get("food") or {}


def extract_servings(food_payload: dict[str, Any]) -> list[dict[str, Any]]:
    """从 food.get 响应中提取 serving 列表。"""
    food = extract_food(food_payload)
    servings = food.get("servings") or {}
    return as_list(servings.get("serving"))
