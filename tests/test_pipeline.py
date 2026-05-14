import importlib.util
import json
import sys
from copy import deepcopy
from pathlib import Path

from recipe_quality.models import Nutrients, ResolvedFoodItem
from recipe_quality.pipeline import evaluate_full_pipeline


def test_evaluate_full_pipeline_runs_steps_and_returns_summary(monkeypatch):
    def fake_annotate(payload):
        annotated = deepcopy(payload)
        dish = annotated["meals"][0]["dishes"][0]
        dish["cooking_method"] = "steam"
        dish["cooking_method_source"] = "ai"
        ingredient = dish["ingredients"][0]
        ingredient["search_name"] = "tomato"
        ingredient["search_name_source"] = "ai"
        ingredient["food_group"] = "vegetables"
        ingredient["food_group_source"] = "ai"
        ingredient["processing_level"] = "unprocessed"
        ingredient["processing_level_source"] = "ai"
        annotated["ai_annotation_meta"] = {"warnings": []}
        return annotated

    class FakeResolver:
        def resolve_items(self, items):
            assert items[0]["search_name"] == "tomato"
            return [
                ResolvedFoodItem(
                    name=items[0]["name"],
                    amount_g=items[0]["amount_g"],
                    meal_name=items[0]["meal_name"],
                    dish_name=items[0]["dish_name"],
                    search_name=items[0]["search_name"],
                    food_group=items[0]["food_group"],
                    processing_level=items[0]["processing_level"],
                    fatsecret_food_name="Tomatoes",
                    serving_used="100 g",
                    nutrition_estimation_status="resolved",
                    match_confidence="high",
                    nutrients=Nutrients(
                        energy_kcal=36,
                        protein_g=2,
                        fat_g=0.5,
                        saturated_fat_g=0.1,
                        carbohydrate_g=8,
                        fiber_g=2,
                        sodium_mg=10,
                        potassium_mg=200,
                        calcium_mg=20,
                        iron_mg=1,
                        vitamin_c_mg=20,
                        added_sugar_g=0,
                    ),
                )
            ]

    monkeypatch.setattr("recipe_quality.pipeline.annotate_recipe_input", fake_annotate)
    steps = []

    result = evaluate_full_pipeline(
        {
            "target_user": {"sex": "female", "age": 30, "height_cm": 165, "weight_kg": 58},
            "meals": [
                {
                    "meal_name": "lunch",
                    "dishes": [
                        {
                            "dish_name": "番茄",
                            "ingredients": [{"name": "番茄", "amount_g": 200}],
                            "condiments": [],
                        }
                    ],
                }
            ],
            "record_quality": {"completeness": "complete"},
        },
        progress_callback=lambda step_key, _message: steps.append(step_key),
        resolver=FakeResolver(),
    )

    assert steps == [
        "ai_annotation",
        "normalization",
        "nutrition_resolution",
        "scoring",
        "completed",
    ]
    assert result["resolved_items"][0]["fatsecret_food_name"] == "Tomatoes"
    assert result["daily_totals"]["energy_kcal"] == 36
    assert result["module_scores"]
    assert result["final_grade"] in {"A", "B", "C", "D", "E"}


def test_full_pipeline_eval_script_uses_shared_pipeline(monkeypatch, tmp_path, capsys):
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "full_pipeline_eval.py"
    spec = importlib.util.spec_from_file_location("full_pipeline_eval_for_test", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    input_path = tmp_path / "input.json"
    input_path.write_text(json.dumps({"meals": []}), encoding="utf-8")

    monkeypatch.setattr(module, "evaluate_full_pipeline", lambda payload: {"total_score": 88})
    monkeypatch.setattr(sys, "argv", ["full_pipeline_eval.py", str(input_path)])

    assert module.main() == 0
    assert json.loads(capsys.readouterr().out)["total_score"] == 88
