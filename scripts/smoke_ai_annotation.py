from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from recipe_quality.ai_annotation import annotate_recipe_input
from recipe_quality.engine import evaluate_daily_diet


def main() -> None:
    payload = {
        "target_user": {
            "liked_foods": ["tomato", "egg"],
            "habit_pattern": "chinese_home_meals",
        },
        "meals": [
            {
                "meal_name": "lunch",
                "dishes": [
                    {
                        "dish_name": "tomato eggs",
                        "ingredients": [
                            {
                                "name": "tomato",
                                "amount_g": 200,
                                "food_group": "vegetables",
                                "nutrients": {"energy_kcal": 36, "fiber_g": 2},
                            },
                            {
                                "name": "egg",
                                "amount_g": 100,
                                "food_group": "eggs",
                                "nutrients": {"energy_kcal": 140, "protein_g": 13},
                            },
                        ],
                        "condiments": [{"name": "oil", "amount_g": 8}],
                    }
                ],
            }
        ],
        "record_quality": {"completeness": "complete"},
    }

    annotated = annotate_recipe_input(payload)
    result = evaluate_daily_diet(annotated)
    dish = annotated["meals"][0]["dishes"][0]
    ingredients = dish["ingredients"]
    summary = {
        "cooking_method": dish.get("cooking_method"),
        "ingredient_processing_levels": [
            {
                "name": ingredient.get("name"),
                "processing_level": ingredient.get("processing_level"),
                "liked_food_matches": ingredient.get("liked_food_matches"),
                "liked_food_use_quality": ingredient.get("liked_food_use_quality"),
            }
            for ingredient in ingredients
        ],
        "habit_match_level": annotated.get("habit_match_level"),
        "feasibility": annotated.get("feasibility"),
        "ai_annotation_meta": annotated.get("ai_annotation_meta"),
        "cooking_processing_safety": result["module_details"]["cooking_processing_safety"],
        "personalization_feasibility": result["module_details"]["personalization_feasibility"],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
