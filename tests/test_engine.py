from recipe_quality.engine import evaluate_daily_diet


def test_engine_applies_sodium_grade_cap():
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

