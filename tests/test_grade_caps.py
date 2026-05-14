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


def test_grade_caps_limit_edible_weight_outside_range():
    caps = evaluate_grade_caps(
        {
            "energy_kcal": 2000,
            "ingredient_records": [
                {"name": "small meal", "amount_g": 500, "nutrients": {"energy_kcal": 2000}},
                {"name": "bone", "amount_g": 300, "edible": False, "nutrients": {"energy_kcal": 0}},
            ],
        }
    )

    triggers = {cap["trigger"] for cap in caps}
    assert "edible_weight_outside_range" in triggers


def test_grade_caps_limit_energy_density_outside_range():
    caps = evaluate_grade_caps(
        {
            "energy_kcal": 2600,
            "ingredient_records": [
                {"name": "dense meal", "amount_g": 700, "nutrients": {"energy_kcal": 2600}},
            ],
        }
    )

    triggers = {cap["trigger"] for cap in caps}
    assert "energy_density_outside_range" in triggers


def test_grade_caps_limit_max_meal_energy_ratio():
    caps = evaluate_grade_caps(
        {
            "energy_kcal": 2000,
            "ingredient_records": [
                {"meal_name": "lunch", "amount_g": 600, "nutrients": {"energy_kcal": 1700}},
                {"meal_name": "breakfast", "amount_g": 300, "nutrients": {"energy_kcal": 200}},
                {"meal_name": "dinner", "amount_g": 300, "nutrients": {"energy_kcal": 100}},
            ],
        }
    )

    assert {
        "trigger": "max_meal_energy_ratio_above_80_percent",
        "value": 0.85,
        "cap_grade": "E",
    } in caps


def test_grade_caps_limit_abnormal_three_meal_distribution():
    caps = evaluate_grade_caps(
        {
            "energy_kcal": 2000,
            "ingredient_records": [
                {"meal_name": "breakfast", "amount_g": 100, "nutrients": {"energy_kcal": 100}},
                {"meal_name": "lunch", "amount_g": 500, "nutrients": {"energy_kcal": 1000}},
                {"meal_name": "dinner", "amount_g": 500, "nutrients": {"energy_kcal": 900}},
            ],
        }
    )

    triggers = {cap["trigger"] for cap in caps}
    assert "main_meal_energy_ratio_abnormal" in triggers


def test_grade_caps_limit_two_main_meals_concentrated_energy():
    caps = evaluate_grade_caps(
        {
            "energy_kcal": 2000,
            "ingredient_records": [
                {"meal_name": "breakfast", "amount_g": 100, "nutrients": {"energy_kcal": 80}},
                {"meal_name": "lunch", "amount_g": 500, "nutrients": {"energy_kcal": 1000}},
                {"meal_name": "dinner", "amount_g": 500, "nutrients": {"energy_kcal": 920}},
            ],
        }
    )

    triggers = {cap["trigger"] for cap in caps}
    assert "two_main_meals_energy_ratio_above_90_percent" in triggers


def test_grade_caps_limit_snack_energy_ratio():
    caps = evaluate_grade_caps(
        {
            "energy_kcal": 2000,
            "ingredient_records": [
                {"meal_name": "snack", "amount_g": 300, "nutrients": {"energy_kcal": 1100}},
                {"meal_name": "lunch", "amount_g": 700, "nutrients": {"energy_kcal": 900}},
            ],
        }
    )

    triggers = {cap["trigger"] for cap in caps}
    assert "snack_energy_ratio_above_50_percent" in triggers
