from recipe_quality.fatsecret.mapper import (
    is_100g_or_100ml_serving,
    scale_serving_to_amount,
    serving_metric_amount,
    serving_to_nutrients,
)


def test_serving_to_nutrients_maps_known_fields():
    """验证 FatSecret serving 字段能正确映射为内部营养字段。"""
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
    """验证 serving 营养值会按 metric_serving_amount 换算到实际克数。"""
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
    """验证缺少 metric 字段时可从 100 g 描述中推断基准重量。"""
    assert serving_metric_amount({"serving_description": "100 g"}) == 100


def test_is_100g_or_100ml_serving_only_accepts_standard_100_units():
    assert is_100g_or_100ml_serving(
        {"metric_serving_amount": "100", "metric_serving_unit": "g"}
    )
    assert not is_100g_or_100ml_serving(
        {"metric_serving_amount": "100", "metric_serving_unit": "oz"}
    )
