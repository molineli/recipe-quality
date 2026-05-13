from __future__ import annotations

from typing import Any

from recipe_quality.config_loader import load_cooking_method_scores, load_processing_level_scores


COOKING_METHOD_SCORES = load_cooking_method_scores()
PROCESSING_LEVEL_SCORES = load_processing_level_scores()
LOW_CONFIDENCE_THRESHOLD = 0.6
UNKNOWN_COOKING_METHOD = "unknown_cooking_method"
UNKNOWN_PROCESSING_LEVEL = "unknown_processing_level"


def score_cooking_processing_safety(daily_totals: dict) -> tuple[float, dict]:
    """Calculate C1 cooking method and C2 ingredient processing scores."""
    warnings: list[str] = []
    cooking_score, cooking_details = score_cooking_methods(daily_totals, warnings)
    processing_score, processing_details = score_processing_levels(daily_totals, warnings)
    total = round(cooking_score + processing_score, 2)
    details = {
        "score": total,
        "max_score": 15,
        "cooking_method": round(cooking_score, 2),
        "processing_level": round(processing_score, 2),
        "food_safety": 0.0,
        "dish_scores": cooking_details,
        "ingredient_processing_scores": processing_details,
        "warnings": warnings,
    }
    return total, details


def score_cooking_methods(daily_totals: dict, warnings: list[str] | None = None) -> tuple[float, list[dict[str, Any]]]:
    """Score C1 from dish-level cooking_method labels."""
    warnings = warnings if warnings is not None else []
    dish_records = daily_totals.get("dish_records") or []
    if not dish_records:
        warnings.append("C1 cooking method score is 0 because no dish records were provided.")
        return 0.0, []

    weight_key = _choose_weight_key(dish_records, energy_path=None, weight_key="total_weight_g")
    if weight_key != "energy_kcal":
        warnings.append("C1 cooking method score used dish weight fallback because dish energy was incomplete.")

    weighted_values: list[tuple[float, float]] = []
    details: list[dict[str, Any]] = []
    for dish in dish_records:
        method, label_warning = _validated_label(
            record=dish,
            label_key="cooking_method",
            confidence_key="cooking_method_confidence",
            scores=COOKING_METHOD_SCORES,
            unknown_label=UNKNOWN_COOKING_METHOD,
        )
        if label_warning:
            warnings.append(f"C1 {dish.get('dish_name') or 'unknown dish'}: {label_warning}")
        base_score = COOKING_METHOD_SCORES[method]
        normalized_score = 8 * (base_score / 10)
        weight = _to_float(dish.get(weight_key)) or 0.0
        if weight <= 0:
            continue
        weighted_values.append((normalized_score, weight))
        details.append(
            {
                "dish_name": dish.get("dish_name"),
                "cooking_method": dish.get("cooking_method"),
                "method_used": method,
                "base_score": base_score,
                "score": round(normalized_score, 2),
                "weight": round(weight, 2),
                "weight_source": weight_key,
            }
        )

    return round(_weighted_average(weighted_values), 2), details


def score_processing_levels(
    daily_totals: dict,
    warnings: list[str] | None = None,
) -> tuple[float, list[dict[str, Any]]]:
    """Score C2 from ingredient-level processing_level labels."""
    warnings = warnings if warnings is not None else []
    ingredient_records = [
        item for item in daily_totals.get("ingredient_records") or [] if item.get("edible", True)
    ]
    if not ingredient_records:
        warnings.append("C2 processing level score is 0 because no ingredient records were provided.")
        return 0.0, []

    weight_key = _choose_weight_key(ingredient_records, energy_path=("nutrients", "energy_kcal"), weight_key="amount_g")
    if weight_key != "energy_kcal":
        warnings.append("C2 processing level score used ingredient weight fallback because ingredient energy was incomplete.")

    weighted_values: list[tuple[float, float]] = []
    details: list[dict[str, Any]] = []
    for ingredient in ingredient_records:
        level, label_warning = _validated_label(
            record=ingredient,
            label_key="processing_level",
            confidence_key="processing_level_confidence",
            scores=PROCESSING_LEVEL_SCORES,
            unknown_label=UNKNOWN_PROCESSING_LEVEL,
        )
        if label_warning:
            warnings.append(f"C2 {ingredient.get('name') or 'unknown ingredient'}: {label_warning}")
        score = PROCESSING_LEVEL_SCORES[level]
        weight = _record_energy(ingredient) if weight_key == "energy_kcal" else _to_float(ingredient.get("amount_g"))
        weight = weight or 0.0
        if weight <= 0:
            continue
        weighted_values.append((score, weight))
        details.append(
            {
                "ingredient_id": ingredient.get("ingredient_id"),
                "name": ingredient.get("name"),
                "processing_level": ingredient.get("processing_level"),
                "level_used": level,
                "score": round(score, 2),
                "weight": round(weight, 2),
                "weight_source": weight_key,
            }
        )

    return round(_weighted_average(weighted_values), 2), details


def _choose_weight_key(
    records: list[dict[str, Any]],
    energy_path: tuple[str, str] | None,
    weight_key: str,
) -> str:
    if all((_record_energy(record) if energy_path else _to_float(record.get("energy_kcal"))) for record in records):
        return "energy_kcal"
    return weight_key


def _validated_label(
    record: dict[str, Any],
    label_key: str,
    confidence_key: str,
    scores: dict[str, float],
    unknown_label: str,
) -> tuple[str, str | None]:
    label = record.get(label_key)
    confidence = _to_float(record.get(confidence_key))
    if confidence is not None and confidence < LOW_CONFIDENCE_THRESHOLD:
        return unknown_label, f"{label_key} confidence is below {LOW_CONFIDENCE_THRESHOLD}; used {unknown_label}."
    if not label:
        return unknown_label, f"{label_key} is missing; used {unknown_label}."
    label = str(label)
    if label not in scores:
        return unknown_label, f"{label_key}={label} is not configured; used {unknown_label}."
    return label, None


def _weighted_average(values: list[tuple[float, float]]) -> float:
    total_weight = sum(weight for _, weight in values)
    if total_weight <= 0:
        return 0.0
    return sum(value * weight for value, weight in values) / total_weight


def _record_energy(record: dict[str, Any]) -> float | None:
    nutrients = record.get("nutrients") or {}
    if isinstance(nutrients, dict):
        value = nutrients.get("energy_kcal")
        if value is not None:
            return _to_float(value)
    return _to_float(record.get("energy_kcal"))


def _to_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
