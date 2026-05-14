from recipe_quality.fatsecret.schemas import extract_foods


def test_extract_foods_supports_v5_foods_search_response():
    payload = {
        "foods_search": {
            "results": {
                "food": [
                    {"food_id": "1", "food_name": "Rice", "food_type": "Generic"},
                    {"food_id": "2", "food_name": "Brown Rice", "food_type": "Generic"},
                ]
            }
        }
    }

    foods = extract_foods(payload)

    assert [food["food_name"] for food in foods] == ["Rice", "Brown Rice"]


def test_extract_foods_keeps_legacy_foods_response_support():
    payload = {
        "foods": {
            "food": {"food_id": "1", "food_name": "Rice", "food_type": "Generic"}
        }
    }

    foods = extract_foods(payload)

    assert len(foods) == 1
    assert foods[0]["food_name"] == "Rice"
