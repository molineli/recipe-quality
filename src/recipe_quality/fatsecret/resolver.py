from __future__ import annotations

from typing import Any

from recipe_quality.fatsecret.client import FatSecretClient, FatSecretError
from recipe_quality.fatsecret.mapper import (
    is_100g_or_100ml_serving,
    scale_serving_to_amount,
    serving_label,
    serving_metric_amount,
)
from recipe_quality.fatsecret.schemas import extract_food, extract_foods, extract_servings
from recipe_quality.models import ResolvedFoodItem


class FatSecretResolver:
    def __init__(self, client: FatSecretClient):
        """保存 FatSecret 客户端，用于后续搜索和详情查询。"""
        self.client = client

    def resolve_item(self, item: dict[str, Any]) -> ResolvedFoodItem:
        """解析单个食物项，返回匹配结果、serving 信息和换算后的营养值。"""
        name = str(item.get("name") or "").strip()
        search_name = str(item.get("search_name") or name).strip()
        amount_g = float(item.get("amount_g") or 0)
        meal_name = item.get("meal_name")
        common_fields = {
            "ingredient_id": item.get("ingredient_id"),
            "dish_name": item.get("dish_name"),
            "search_name": search_name or None,
            "search_name_source": item.get("search_name_source"),
            "edible": item.get("edible", True),
            "food_group": item.get("food_group"),
            "classification_source": item.get("classification_source"),
            "classification_confidence": item.get("classification_confidence"),
            "processing_level": item.get("processing_level"),
            "processing_level_source": item.get("processing_level_source"),
            "processing_level_confidence": item.get("processing_level_confidence"),
        }
        if not name or amount_g <= 0:
            return ResolvedFoodItem(
                name=name,
                amount_g=amount_g,
                meal_name=meal_name,
                **common_fields,
                error="name and positive amount_g are required",
            )

        try:
            food_id = str(item.get("fatsecret_food_id") or "")
            candidates: list[dict[str, Any]] = []
            if not food_id:
                search_payload = self.client.search_foods(search_name)
                candidates = self.rank_candidates(search_name, extract_foods(search_payload))
                if not candidates:
                    return ResolvedFoodItem(
                        name=name,
                        amount_g=amount_g,
                        meal_name=meal_name,
                        **common_fields,
                        candidates=[],
                        error="no FatSecret candidates found",
                    )
                food_id = str(candidates[0]["food_id"])

            food_payload = self.client.get_food(food_id)
            food = extract_food(food_payload)
            serving = choose_serving(extract_servings(food_payload))
            if not serving:
                return ResolvedFoodItem(
                    name=name,
                    amount_g=amount_g,
                    meal_name=meal_name,
                    **common_fields,
                    fatsecret_food_id=food_id,
                    fatsecret_food_name=food.get("food_name"),
                    candidates=candidates,
                    error="no gram/ml serving available",
                )

            nutrients, base_amount = scale_serving_to_amount(serving, amount_g)
            if base_amount is None:
                status = "unresolved"
                error = "serving cannot be converted to grams/ml"
            else:
                status = "resolved"
                error = None

            return ResolvedFoodItem(
                name=name,
                amount_g=amount_g,
                meal_name=meal_name,
                **common_fields,
                fatsecret_food_id=food_id,
                fatsecret_food_name=food.get("food_name"),
                serving_used=serving_label(serving),
                match_confidence=match_confidence(search_name, food, candidates),
                nutrition_estimation_status=status,
                nutrients=nutrients,
                candidates=candidates[:5],
                error=error,
            )
        except FatSecretError as exc:
            return ResolvedFoodItem(
                name=name,
                amount_g=amount_g,
                meal_name=meal_name,
                **common_fields,
                error=str(exc),
            )

    def resolve_items(self, items: list[dict[str, Any]]) -> list[ResolvedFoodItem]:
        """批量解析食物项列表。"""
        return [self.resolve_item(item) for item in items]

    @staticmethod
    def rank_candidates(query: str, foods: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """按保守策略对 FatSecret 搜索候选排序，优先 Generic 和名称匹配。"""
        normalized_query = query.casefold()

        def score(food: dict[str, Any]) -> tuple[int, str]:
            """计算单个候选食物的排序键。"""
            name = str(food.get("food_name") or "")
            food_type = str(food.get("food_type") or "")
            lowered_name = name.casefold()
            value = 0
            if food_type.casefold() == "generic":
                value += 50
            if lowered_name == normalized_query:
                value += 40
            elif normalized_query in lowered_name:
                value += 20
            if "brand_name" in food and food["brand_name"]:
                value -= 10
            return (-value, name)

        return sorted(foods, key=score)


def choose_serving(servings: list[dict[str, Any]]) -> dict[str, Any] | None:
    """从 serving 列表中选择最适合按克数换算的 serving。"""
    if not servings:
        return None

    def score(serving: dict[str, Any]) -> tuple[int, str]:
        """计算 serving 的排序键，优先 100g/100ml。"""
        amount = serving_metric_amount(serving)
        label = serving_label(serving).lower()
        if is_100g_or_100ml_serving(serving):
            return (0, label)
        if amount:
            return (1, label)
        return (2, label)

    best = sorted(servings, key=score)[0]
    return best if serving_metric_amount(best) else None


def match_confidence(query: str, food: dict[str, Any], candidates: list[dict[str, Any]]) -> str:
    """根据名称和候选类型估算食物匹配置信度。"""
    name = str(food.get("food_name") or "")
    if name.casefold() == query.casefold():
        return "high"
    if candidates and str(candidates[0].get("food_type") or "").casefold() == "generic":
        return "medium"
    return "low"
