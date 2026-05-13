from recipe_quality.normalizer import normalize_recipe_input


def test_normalize_recipe_input_flattens_meals_dishes_and_extra_items():
    """验证统一食谱输入会被拍平成原料、菜品和调味品记录。"""
    payload = {
        "meals": [
            {
                "meal_name": "lunch",
                "meal_time": "12:00",
                "dishes": [
                    {
                        "dish_name": "番茄炒蛋",
                        "cooking_method": "stir_fry_low_oil",
                        "ingredients": [
                            {"name": "番茄", "amount_g": 200, "food_group": "vegetables"},
                            {"name": "鸡蛋", "amount_g": 100, "food_group": "eggs"},
                        ],
                        "condiments": [{"name": "食盐", "amount_g": 1}],
                    }
                ],
            }
        ],
        "extra_items": [{"name": "苹果", "amount_g": 180, "food_group": "fruits"}],
    }

    normalized = normalize_recipe_input(payload)

    assert len(normalized["ingredient_records"]) == 3
    assert len(normalized["dish_records"]) == 1
    assert normalized["condiments"][0]["dish_name"] == "番茄炒蛋"
    assert normalized["ingredient_records"][0]["food_group"] == "vegetables"
