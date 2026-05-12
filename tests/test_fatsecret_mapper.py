from recipe_quality.fatsecret.mapper import scale_serving_to_amount, serving_metric_amount, serving_to_nutrients


def test_serving_to_nutrients_maps_known_fields():
    serving = {
        "calories": "130",
        "protein": "2.7",
        "fat": "0.3",
        "saturated_fat": "0.1",
        "carbohydrate": "28",
        "fiber": "0.4",
        "sodium": "1",
        "potassium": "35",
        "calcium": "10",
        "iron": "1.2",
        "vitamin_c": "0",
        "added_sugars": "0",
    }

    nutrients = serving_to_nutrients(serving)

    assert nutrients.energy_kcal == 130
    assert nutrients.protein_g == 2.7
    assert nutrients.sodium_mg == 1


def test_scale_serving_to_amount_uses_metric_serving_amount():
    serving = {
        "metric_serving_amount": "100",
        "metric_serving_unit": "g",
        "calories": "130",
        "protein": "2.7",
    }

    nutrients, base_amount = scale_serving_to_amount(serving, 200)

    assert base_amount == 100
    assert nutrients.energy_kcal == 260
    assert nutrients.protein_g == 5.4


def test_serving_metric_amount_handles_100g_description():
    assert serving_metric_amount({"serving_description": "100 g"}) == 100

