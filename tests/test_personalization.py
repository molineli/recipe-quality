from recipe_quality.scoring.personalization import score_personalization


def test_personalization_scores_likes_habit_and_feasibility_from_recipe_facts():
    score, details = score_personalization(
        {
            "target_user": {
                "liked_foods": ["tomato", "egg"],
                "habit_pattern": "chinese_home_meals",
            },
            "meals": [
                {
                    "meal_name": "lunch",
                    "dishes": [
                        {
                            "dish_name": "tomato eggs",
                            "cooking_method": "stir_fry_low_oil",
                            "ingredients": [
                                {
                                    "name": "tomato",
                                    "amount_g": 200,
                                    "food_group": "vegetables",
                                    "processing_level": "unprocessed",
                                },
                                {
                                    "name": "egg",
                                    "amount_g": 100,
                                    "food_group": "eggs",
                                    "processing_level": "unprocessed",
                                },
                            ],
                        }
                    ],
                }
            ],
        }
    )

    assert score == 8
    assert details["liked_foods_reasonable_use"] == 3
    assert details["habit_match"] == 2
    assert details["feasibility"] == 3


def test_liked_food_score_is_limited_when_liked_food_is_used_riskily():
    score, details = score_personalization(
        {
            "target_user": {"liked_foods": ["chicken"]},
            "meals": [
                {
                    "meal_name": "dinner",
                    "dishes": [
                        {
                            "dish_name": "fried chicken",
                            "cooking_method": "deep_fry",
                            "ingredients": [
                                {
                                    "name": "chicken",
                                    "amount_g": 150,
                                    "food_group": "livestock_poultry_meat",
                                }
                            ],
                        }
                    ],
                }
            ],
        }
    )

    assert details["liked_foods_reasonable_use"] == 1
    assert details["liked_foods_details"]["risk_limited"] is True
    assert score == 4


def test_personalization_uses_explicit_habit_label_and_structured_feasibility_factors():
    score, details = score_personalization(
        {
            "target_user": {
                "liked_foods": [],
                "habit_pattern": "chinese_home_meals",
            },
            "habit_match_level": "partial",
            "feasibility": {
                "estimated_prep_time_min": 75,
                "step_complexity": "complex",
                "ingredient_availability": "common",
                "cost_level": "medium",
                "special_equipment_required": False,
            },
            "meals": [
                {
                    "meal_name": "dinner",
                    "dishes": [
                        {
                            "dish_name": "complex stew",
                            "cooking_method": "stew_clear",
                            "ingredients": [{"name": "beef", "amount_g": 150}],
                        }
                    ],
                }
            ],
        }
    )

    assert score == 2
    assert details["liked_foods_reasonable_use"] == 0
    assert details["habit_match"] == 1
    assert details["habit_match_details"]["source"] == "explicit_label"
    assert details["feasibility"] == 1
    assert details["feasibility_details"]["penalties"] == [
        "prep_time_over_60_min",
        "complex_steps",
    ]


def test_liked_food_score_prefers_ai_liked_food_matches():
    score, details = score_personalization(
        {
            "target_user": {"liked_foods": ["tomato"], "habit_pattern": "chinese_home_meals"},
            "meals": [
                {
                    "meal_name": "lunch",
                    "dishes": [
                        {
                            "dish_name": "alias dish",
                            "cooking_method": "steam",
                            "ingredients": [
                                {
                                    "name": "red vegetable",
                                    "amount_g": 100,
                                    "food_group": "vegetables",
                                    "liked_food_matches": ["tomato"],
                                    "liked_food_use_quality": "reasonable",
                                }
                            ],
                        }
                    ],
                }
            ],
        }
    )

    assert details["liked_foods_reasonable_use"] == 1.5
    assert details["liked_foods_details"]["matched_foods"][0]["match_source"] == "ai_label"
    assert score == 5.5


def test_ai_risky_liked_food_quality_limits_e1_score():
    score, details = score_personalization(
        {
            "target_user": {"liked_foods": ["potato"], "habit_pattern": "chinese_home_meals"},
            "meals": [
                {
                    "meal_name": "dinner",
                    "dishes": [
                        {
                            "dish_name": "sweet potato",
                            "cooking_method": "steam",
                            "ingredients": [
                                {
                                    "name": "potato",
                                    "amount_g": 150,
                                    "food_group": "grains_and_tubers",
                                    "liked_food_matches": ["potato"],
                                    "liked_food_use_quality": "risky",
                                }
                            ],
                        }
                    ],
                }
            ],
        }
    )

    assert details["liked_foods_reasonable_use"] == 1
    assert details["liked_foods_details"]["risk_limited"] is True
    assert score == 5
