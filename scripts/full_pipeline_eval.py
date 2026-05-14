from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from recipe_quality.aggregator import resolve_and_aggregate
from recipe_quality.ai_annotation import annotate_recipe_input
from recipe_quality.engine import evaluate_daily_diet
from recipe_quality.fatsecret import FatSecretClient, FatSecretResolver
from recipe_quality.normalizer import normalize_recipe_input


def main() -> int:
    if len(sys.argv) < 2:
        print(
            "Usage: python scripts/full_pipeline_eval.py <input_day.json>",
            file=sys.stderr,
        )
        return 2

    input_path = Path(sys.argv[1])
    payload = json.loads(input_path.read_text(encoding="utf-8"))

    annotated = annotate_recipe_input(payload)
    normalized = normalize_recipe_input(annotated)
    resolver = FatSecretResolver(FatSecretClient())
    resolved = resolve_and_aggregate(
        resolver,
        normalized["ingredient_records"],
        normalized["condiments"],
        dish_records=normalized["dish_records"],
        record_quality=payload.get("record_quality"),
    )
    enriched = {
        **annotated,
        "items": resolved["items"],
        "ingredient_records": resolved["ingredient_records"],
        "dish_records": resolved["dish_records"],
        "daily_totals": resolved["daily_totals"],
    }
    evaluation = evaluate_daily_diet(enriched)

    print(json.dumps(_summary(annotated, resolved, evaluation), ensure_ascii=False, indent=2))
    return 0


def _summary(
    annotated: dict[str, Any],
    resolved: dict[str, Any],
    evaluation: dict[str, Any],
) -> dict[str, Any]:
    daily_totals = resolved["daily_totals"]
    return {
        "ai_warnings": annotated.get("ai_annotation_meta", {}).get("warnings", []),
        "resolved_items": [
            {
                "name": item.get("name"),
                "search_name": item.get("search_name"),
                "food_group": item.get("food_group"),
                "processing_level": item.get("processing_level"),
                "fatsecret_food_name": item.get("fatsecret_food_name"),
                "serving_used": item.get("serving_used"),
                "status": item.get("nutrition_estimation_status"),
                "error": item.get("error"),
            }
            for item in resolved["items"]
        ],
        "daily_totals": {
            key: daily_totals.get(key)
            for key in [
                "energy_kcal",
                "protein_g",
                "fat_g",
                "saturated_fat_g",
                "carbohydrate_g",
                "fiber_g",
                "sodium_mg",
                "cooking_oil_g",
                "added_sugar_g",
                "food_group_amounts_g",
                "food_group_count",
                "data_quality",
            ]
        },
        "total_score": evaluation["total_score"],
        "raw_grade": evaluation["raw_grade"],
        "final_grade": evaluation["final_grade"],
        "module_scores": evaluation["module_scores"],
        "grade_caps": evaluation["grade_caps"],
    }


if __name__ == "__main__":
    raise SystemExit(main())
