from recipe_quality.demo_input import build_payload_from_demo_tables


def test_build_payload_from_demo_tables_groups_rows_into_meals_and_dishes():
    payload = build_payload_from_demo_tables(
        target_user={
            "sex": "female",
            "age": "30",
            "height_cm": "165",
            "weight_kg": "58",
            "liked_foods": "鸡蛋，番茄",
            "dietary_restrictions": "",
        },
        ingredient_rows=[
            {
                "meal_name": "lunch",
                "meal_time": "12:30",
                "dish_name": "番茄炒蛋",
                "dish_type": "home_cooked",
                "ingredient_name": "番茄",
                "amount_g": "200",
                "edible": "是",
            },
            {
                "meal_name": "lunch",
                "meal_time": "12:30",
                "dish_name": "番茄炒蛋",
                "dish_type": "home_cooked",
                "ingredient_name": "鸡蛋",
                "amount_g": 100,
                "edible": True,
            },
        ],
        condiment_rows=[
            {
                "meal_name": "lunch",
                "dish_name": "番茄炒蛋",
                "condiment_name": "食盐",
                "amount_g": "1.5",
            }
        ],
        extra_item_rows=[
            {
                "name": "苹果",
                "amount_g": 180,
                "meal_name": "snack",
                "meal_time": "15:00",
                "item_type": "fruit",
            }
        ],
        date="2026-05-12",
    )

    assert payload["date"] == "2026-05-12"
    assert payload["target_user"]["liked_foods"] == ["鸡蛋", "番茄"]
    assert payload["target_user"]["age"] == 30
    assert payload["meals"][0]["meal_name"] == "lunch"
    assert payload["meals"][0]["dishes"][0]["dish_name"] == "番茄炒蛋"
    assert [item["name"] for item in payload["meals"][0]["dishes"][0]["ingredients"]] == [
        "番茄",
        "鸡蛋",
    ]
    assert payload["meals"][0]["dishes"][0]["condiments"] == [{"name": "食盐", "amount_g": 1.5}]
    assert payload["extra_items"][0]["meal_time"] == "15:00"
    assert payload["record_quality"]["completeness"] == "complete"
