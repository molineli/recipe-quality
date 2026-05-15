from recipe_quality.aggregator import aggregate_daily_totals
from recipe_quality.models import Nutrients, ResolvedFoodItem


def test_aggregate_daily_totals_adds_items_and_condiment_salt():
    """验证全天汇总会叠加食物营养，并将食盐换算为钠。"""
    items = [
        ResolvedFoodItem(
            name="rice",
            amount_g=200,
            food_group="grains_and_tubers",
            nutrition_estimation_status="resolved",
            nutrients=Nutrients(energy_kcal=260, protein_g=5, sodium_mg=2),
        )
    ]

    totals = aggregate_daily_totals(
        items,
        condiments=[
            {"name": "食盐", "amount_g": 3},
            {"name": "烹调油", "amount_g": 20},
        ],
    )

    assert totals["energy_kcal"] == 260
    assert round(totals["sodium_mg"], 1) == 1182.2
    assert totals["cooking_oil_g"] == 20
    assert totals["food_group_amounts_g"]["grains_and_tubers"] == 200
    assert totals["food_group_count"] == 1
    assert totals["data_quality"]["status"] == "complete"


def test_aggregate_daily_totals_classifies_common_cooking_oil_names():
    totals = aggregate_daily_totals(
        [],
        condiments=[
            {"name": "菜籽油", "amount_g": 8},
            {"name": "芝麻油", "amount_g": 3},
            {"name": "香油", "amount_g": 2},
            {"name": "植物油", "amount_g": 4},
            {"name": "生姜", "amount_g": 5},
        ],
    )

    assert totals["cooking_oil_g"] == 17


def test_aggregate_daily_totals_classifies_common_salt_and_soy_sauce_names():
    totals = aggregate_daily_totals(
        [],
        condiments=[
            {"name": "碘盐", "amount_g": 1},
            {"name": "酱油", "amount_g": 10},
            {"name": "低钠酱油", "amount_g": 10},
            {"name": "蒸鱼豉油", "amount_g": 5},
            {"name": "生抽", "amount_g": 2, "sodium_mg": 120},
        ],
    )

    assert round(totals["sodium_mg"], 1) == 1688.4
