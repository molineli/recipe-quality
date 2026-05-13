from recipe_quality.engine import evaluate_daily_diet


def test_engine_applies_sodium_grade_cap():
    """验证钠超过 2 倍上限时会触发等级封顶规则。"""
    result = evaluate_daily_diet(
        {
            "daily_targets": {"energy_kcal": 2000, "sodium_mg_limit": 2000},
            "daily_totals": {
                "energy_kcal": 2000,
                "protein_g": 60,
                "fat_g": 60,
                "saturated_fat_g": 10,
                "carbohydrate_g": 260,
                "fiber_g": 25,
                "sodium_mg": 4200,
                "cooking_oil_g": 20,
                "added_sugar_g": 0,
                "calcium_mg": 800,
                "iron_mg": 12,
                "potassium_mg": 2000,
                "vitamin_c_mg": 100,
                "data_quality": {"status": "complete"},
            },
        }
    )

    assert {"trigger": "sodium_above_2x_limit", "value": 4200, "cap_grade": "C"} in result[
        "grade_caps"
    ]
    assert result["final_grade"] in {"C", "D", "E"}


def test_engine_accepts_meals_dishes_ingredients_shape():
    """验证评分入口支持 meals→dishes→ingredients 的统一输入结构。"""
    result = evaluate_daily_diet(
        {
            "daily_targets": {"energy_kcal": 2000},
            "meals": [
                {
                    "meal_name": "lunch",
                    "dishes": [
                        {
                            "dish_name": "番茄炒蛋",
                            "ingredients": [
                                {
                                    "name": "番茄",
                                    "amount_g": 200,
                                    "food_group": "vegetables",
                                    "nutrients": {"energy_kcal": 36, "fiber_g": 2},
                                },
                                {
                                    "name": "鸡蛋",
                                    "amount_g": 100,
                                    "food_group": "eggs",
                                    "nutrients": {"energy_kcal": 140, "protein_g": 13},
                                },
                            ],
                            "condiments": [{"name": "食盐", "amount_g": 1}],
                        }
                    ],
                }
            ],
            "record_quality": {"completeness": "complete"},
        }
    )

    coverage = result["module_details"]["basic_nutrition_quality"]["food_group_coverage"]
    assert result["daily_totals"]["food_group_amounts_g"]["vegetables"] == 200
    assert coverage["group_scores"]["vegetables"] == 2.0
