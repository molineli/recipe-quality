from recipe_quality.normalizer import normalize_recipe_input


def test_normalize_recipe_input_flattens_meals_dishes_and_extra_items():
    payload = {
        "meals": [
            {
                "meal_name": "lunch",
                "meal_time": "12:00",
                "dishes": [
                    {
                        "dish_name": "tomato eggs",
                        "cooking_method": "stir_fry_low_oil",
                        "processing_level": "minimally_processed",
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
                        "condiments": [{"name": "salt", "amount_g": 1}],
                    }
                ],
            }
        ],
        "extra_items": [{"name": "apple", "amount_g": 180, "food_group": "fruits"}],
    }

    normalized = normalize_recipe_input(payload)

    assert len(normalized["ingredient_records"]) == 3
    assert len(normalized["dish_records"]) == 1
    assert normalized["condiments"][0]["dish_name"] == "tomato eggs"
    assert normalized["ingredient_records"][0]["food_group"] == "vegetables"
    assert normalized["ingredient_records"][0]["processing_level"] == "unprocessed"
    assert "processing_level" not in normalized["dish_records"][0]
