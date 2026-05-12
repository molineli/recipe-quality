from __future__ import annotations


GRADE_ORDER = ["A", "B", "C", "D", "E"]


def score_to_grade(score: float) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "E"


def apply_grade_caps(raw_grade: str, caps: list[dict]) -> str:
    final_grade = raw_grade
    for cap in caps:
        cap_grade = cap["cap_grade"]
        if GRADE_ORDER.index(cap_grade) > GRADE_ORDER.index(final_grade):
            final_grade = cap_grade
    return final_grade


def evaluate_grade_caps(daily_totals: dict, daily_targets: dict | None = None) -> list[dict]:
    targets = {
        "energy_kcal": 2000.0,
        "sodium_mg_limit": 2000.0,
        "cooking_oil_g_limit": 25.0,
        "added_sugar_g_limit": 25.0,
        **(daily_targets or {}),
    }
    caps: list[dict] = []
    energy = daily_totals.get("energy_kcal") or 0
    if targets["energy_kcal"]:
        ratio = energy / targets["energy_kcal"]
        if ratio < 0.70 or ratio > 1.30:
            caps.append({"trigger": "energy_ratio_severe", "value": ratio, "cap_grade": "D"})
        elif ratio < 0.80 or ratio > 1.20:
            caps.append({"trigger": "energy_ratio_outside_range", "value": ratio, "cap_grade": "C"})

    for key, limit_key, label in (
        ("sodium_mg", "sodium_mg_limit", "sodium"),
        ("cooking_oil_g", "cooking_oil_g_limit", "cooking_oil"),
        ("added_sugar_g", "added_sugar_g_limit", "added_sugar"),
    ):
        value = daily_totals.get(key) or 0
        limit = targets[limit_key]
        if value >= 3 * limit:
            caps.append({"trigger": f"{label}_above_3x_limit", "value": value, "cap_grade": "D"})
        elif value >= 2 * limit:
            caps.append({"trigger": f"{label}_above_2x_limit", "value": value, "cap_grade": "C"})

    data_quality = daily_totals.get("data_quality") or {}
    if data_quality.get("status") == "insufficient":
        caps.append({"trigger": "insufficient_nutrition_data", "value": data_quality, "cap_grade": "C"})
    return caps

