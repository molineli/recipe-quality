from recipe_quality.scoring.cooking_processing_safety import score_cooking_processing_safety


def test_cooking_and_processing_scores_use_energy_weighting():
    score, details = score_cooking_processing_safety(
        {
            "dish_records": [
                {"dish_name": "steamed fish", "cooking_method": "steam", "energy_kcal": 100},
                {"dish_name": "fried chicken", "cooking_method": "deep_fry", "energy_kcal": 300},
            ],
            "ingredient_records": [
                {
                    "name": "fish",
                    "amount_g": 100,
                    "processing_level": "unprocessed",
                    "nutrients": {"energy_kcal": 100},
                },
                {
                    "name": "chips",
                    "amount_g": 100,
                    "processing_level": "ultra_processed",
                    "nutrients": {"energy_kcal": 300},
                },
            ],
        }
    )

    assert details["cooking_method"] == 3.2
    assert details["processing_level"] == 1.75
    assert score == 4.95
    assert details["dish_scores"][0]["weight_source"] == "energy_kcal"
    assert details["ingredient_processing_scores"][0]["weight_source"] == "energy_kcal"


def test_cooking_and_processing_scores_fallback_to_weight_when_energy_is_missing():
    score, details = score_cooking_processing_safety(
        {
            "dish_records": [
                {"dish_name": "steamed fish", "cooking_method": "steam", "total_weight_g": 100},
                {"dish_name": "fried chicken", "cooking_method": "deep_fry", "total_weight_g": 300},
            ],
            "ingredient_records": [
                {"name": "fish", "amount_g": 100, "processing_level": "unprocessed"},
                {"name": "chips", "amount_g": 300, "processing_level": "ultra_processed"},
            ],
        }
    )

    assert score == 4.95
    assert any("dish weight fallback" in warning for warning in details["warnings"])
    assert any("ingredient weight fallback" in warning for warning in details["warnings"])


def test_unknown_or_low_confidence_labels_use_unknown_scores():
    score, details = score_cooking_processing_safety(
        {
            "dish_records": [
                {
                    "dish_name": "unclear dish",
                    "cooking_method": "steam",
                    "cooking_method_confidence": 0.2,
                    "energy_kcal": 100,
                }
            ],
            "ingredient_records": [
                {
                    "name": "unclear item",
                    "amount_g": 100,
                    "processing_level": "unprocessed",
                    "processing_level_confidence": 0.2,
                    "nutrients": {"energy_kcal": 100},
                }
            ],
        }
    )

    assert score == 8.8
    assert details["dish_scores"][0]["method_used"] == "unknown_cooking_method"
    assert details["ingredient_processing_scores"][0]["level_used"] == "unknown_processing_level"
    assert any("confidence is below" in warning for warning in details["warnings"])
