from __future__ import annotations

from typing import Any

from recipe_quality.models import Nutrients


FATSECRET_TO_INTERNAL = {
    "calories": "energy_kcal",
    "protein": "protein_g",
    "fat": "fat_g",
    "saturated_fat": "saturated_fat_g",
    "carbohydrate": "carbohydrate_g",
    "fiber": "fiber_g",
    "sodium": "sodium_mg",
    "potassium": "potassium_mg",
    "calcium": "calcium_mg",
    "iron": "iron_mg",
    "vitamin_c": "vitamin_c_mg",
    "added_sugars": "added_sugar_g",
}


def serving_to_nutrients(serving: dict[str, Any]) -> Nutrients:
    data: dict[str, float | None] = {}
    for external_key, internal_key in FATSECRET_TO_INTERNAL.items():
        data[internal_key] = _to_optional_float(serving.get(external_key))
    return Nutrients.from_mapping(data)


def scale_serving_to_amount(serving: dict[str, Any], amount_g: float) -> tuple[Nutrients, float | None]:
    base_amount = serving_metric_amount(serving)
    if not base_amount or base_amount <= 0:
        return Nutrients(), None
    return serving_to_nutrients(serving).scaled(amount_g / base_amount), base_amount


def serving_metric_amount(serving: dict[str, Any]) -> float | None:
    metric_unit = str(serving.get("metric_serving_unit") or "").lower()
    metric_amount = _to_optional_float(serving.get("metric_serving_amount"))
    if metric_amount and metric_unit in {"g", "gram", "grams", "ml", "milliliter", "milliliters"}:
        return metric_amount

    serving_description = str(serving.get("serving_description") or "").strip().lower()
    if serving_description in {"100 g", "100g", "100 ml", "100ml"}:
        return 100.0
    return None


def serving_label(serving: dict[str, Any]) -> str:
    description = serving.get("serving_description")
    metric_amount = serving.get("metric_serving_amount")
    metric_unit = serving.get("metric_serving_unit")
    if description:
        return str(description)
    if metric_amount and metric_unit:
        return f"{metric_amount} {metric_unit}"
    return "unknown serving"


def _to_optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

