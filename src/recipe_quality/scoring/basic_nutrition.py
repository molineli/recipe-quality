from __future__ import annotations


DEFAULT_TARGETS = {
    "protein_g": 60.0,
    "fiber_g": 25.0,
    "calcium_mg": 800.0,
    "iron_mg": 12.0,
    "potassium_mg": 2000.0,
    "vitamin_c_mg": 100.0,
}


def score_basic_nutrition(daily_totals: dict, daily_targets: dict | None = None) -> tuple[float, dict]:
    targets = {**DEFAULT_TARGETS, **(daily_targets or {})}
    protein = 6 * min((daily_totals.get("protein_g") or 0) / targets["protein_g"], 1)
    fiber = 6 * min((daily_totals.get("fiber_g") or 0) / targets["fiber_g"], 1)
    micro_values = []
    for key in ("calcium_mg", "iron_mg", "potassium_mg", "vitamin_c_mg"):
        value = daily_totals.get(key)
        if value is not None:
            micro_values.append(min(value / targets[key], 1))
    micro = 8 * (sum(micro_values) / len(micro_values)) if micro_values else 0
    # Food-group coverage needs local classification and is intentionally left for the rule layer.
    food_group_placeholder = 0.0
    details = {
        "food_group_coverage": food_group_placeholder,
        "protein_adequacy": round(protein, 2),
        "fiber_adequacy": round(fiber, 2),
        "micronutrient_coverage": round(micro, 2),
    }
    return round(sum(details.values()), 2), details

