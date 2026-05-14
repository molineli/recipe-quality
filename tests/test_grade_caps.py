from recipe_quality.scoring.grade import evaluate_grade_caps


def test_grade_caps_limit_multiple_restricted_components_and_saturated_fat():
    caps = evaluate_grade_caps(
        {
            "energy_kcal": 2000,
            "sodium_mg": 3100,
            "cooking_oil_g": 38,
            "added_sugar_g": 0,
            "saturated_fat_g": 34,
        }
    )

    triggers = {cap["trigger"] for cap in caps}
    assert "multiple_limited_components_above_1_5x_limit" in triggers
    assert "saturated_fat_energy_ratio_above_15_percent" in triggers


def test_grade_caps_limit_missing_vegetables_fruits_and_single_food_group():
    caps = evaluate_grade_caps(
        {
            "energy_kcal": 2000,
            "food_group_amounts_g": {"grains_and_tubers": 300},
            "food_group_count": 1,
        }
    )

    triggers = {cap["trigger"] for cap in caps}
    assert "missing_vegetables_and_fruits" in triggers
    assert "food_group_count_at_most_2" in triggers
