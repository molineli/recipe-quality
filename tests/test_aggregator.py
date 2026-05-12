from recipe_quality.aggregator import aggregate_daily_totals
from recipe_quality.models import Nutrients, ResolvedFoodItem


def test_aggregate_daily_totals_adds_items_and_condiment_salt():
    items = [
        ResolvedFoodItem(
            name="rice",
            amount_g=200,
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
    assert totals["data_quality"]["status"] == "complete"

