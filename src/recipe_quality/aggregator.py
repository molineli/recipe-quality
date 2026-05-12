from __future__ import annotations

from typing import Any

from recipe_quality.models import NUTRIENT_KEYS, ResolvedFoodItem
from recipe_quality.utils.units import salt_g_to_sodium_mg


def aggregate_daily_totals(
    resolved_items: list[ResolvedFoodItem],
    condiments: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    totals: dict[str, Any] = {key: 0.0 for key in NUTRIENT_KEYS}
    missing_nutrients: set[str] = set()

    for item in resolved_items:
        nutrients = item.nutrients.to_dict()
        for key in NUTRIENT_KEYS:
            value = nutrients.get(key)
            if value is None:
                missing_nutrients.add(key)
                continue
            totals[key] += value

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
    totals["data_quality"] = {
        "unresolved_items": unresolved_items,
        "missing_nutrients": sorted(missing_nutrients),
        "status": "complete" if not unresolved_items else "insufficient",
    }
    return totals


def resolve_and_aggregate(
    resolver: Any,
    items: list[dict[str, Any]],
    condiments: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    resolved_items = resolver.resolve_items(items)
    return {
        "items": [item.to_dict() for item in resolved_items],
        "daily_totals": aggregate_daily_totals(resolved_items, condiments),
    }


def _to_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

