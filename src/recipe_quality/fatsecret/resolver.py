from __future__ import annotations

from typing import Any

from recipe_quality.fatsecret.client import FatSecretClient, FatSecretError
from recipe_quality.fatsecret.mapper import scale_serving_to_amount, serving_label, serving_metric_amount
from recipe_quality.fatsecret.schemas import extract_food, extract_foods, extract_servings
from recipe_quality.models import ResolvedFoodItem


class FatSecretResolver:
    def __init__(self, client: FatSecretClient):
        self.client = client

    def resolve_item(self, item: dict[str, Any]) -> ResolvedFoodItem:
        name = str(item.get("name") or "").strip()
        amount_g = float(item.get("amount_g") or 0)
        meal_name = item.get("meal_name")
        if not name or amount_g <= 0:
            return ResolvedFoodItem(
                name=name,
                amount_g=amount_g,
                meal_name=meal_name,
                error="name and positive amount_g are required",
            )

        try:
            food_id = str(item.get("fatsecret_food_id") or "")
            candidates: list[dict[str, Any]] = []
            if not food_id:
                search_payload = self.client.search_foods(name)
                candidates = self.rank_candidates(name, extract_foods(search_payload))
                if not candidates:
                    return ResolvedFoodItem(
                        name=name,
                        amount_g=amount_g,
                        meal_name=meal_name,
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
                fatsecret_food_id=food_id,
                fatsecret_food_name=food.get("food_name"),
                serving_used=serving_label(serving),
                match_confidence=match_confidence(name, food, candidates),
                nutrition_estimation_status=status,
                nutrients=nutrients,
                candidates=candidates[:5],
                error=error,
            )
        except FatSecretError as exc:
            return ResolvedFoodItem(name=name, amount_g=amount_g, meal_name=meal_name, error=str(exc))

    def resolve_items(self, items: list[dict[str, Any]]) -> list[ResolvedFoodItem]:
        return [self.resolve_item(item) for item in items]

    @staticmethod
    def rank_candidates(query: str, foods: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized_query = query.casefold()

        def score(food: dict[str, Any]) -> tuple[int, str]:
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
    if not servings:
        return None

    def score(serving: dict[str, Any]) -> tuple[int, str]:
        amount = serving_metric_amount(serving)
        label = serving_label(serving).lower()
        if amount == 100:
            return (0, label)
        if amount:
            return (1, label)
        return (2, label)

    best = sorted(servings, key=score)[0]
    return best if serving_metric_amount(best) else None


def match_confidence(query: str, food: dict[str, Any], candidates: list[dict[str, Any]]) -> str:
    name = str(food.get("food_name") or "")
    if name.casefold() == query.casefold():
        return "high"
    if candidates and str(candidates[0].get("food_type") or "").casefold() == "generic":
        return "medium"
    return "low"

