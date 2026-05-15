import json

import pytest

from recipe_quality.ai_annotation import (
    AIAnnotationError,
    OpenAIAnnotationClient,
    OpenAIAnnotationConfig,
    annotate_recipe_input,
    merge_annotation,
)
from recipe_quality.engine import evaluate_daily_diet


class FakeResponse:
    status_code = 200

    def __init__(self, payload):
        self._payload = payload
        self.text = json.dumps(payload)

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, annotation):
        self.annotation = annotation
        self.last_request = None

    def post(self, url, headers, json, timeout):
        self.last_request = {
            "url": url,
            "headers": headers,
            "json": json,
            "timeout": timeout,
        }
        return FakeResponse(
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": json_module_dumps(self.annotation),
                        }
                    }
                ]
            }
        )


def json_module_dumps(value):
    return json.dumps(value)


def sample_payload():
    return {
        "target_user": {
            "liked_foods": ["tomato"],
            "habit_pattern": "chinese_home_meals",
        },
        "meals": [
            {
                "meal_name": "lunch",
                "dishes": [
                    {
                        "dish_name": "tomato eggs",
                        "ingredients": [
                            {"name": "tomato", "amount_g": 200},
                            {"name": "egg", "amount_g": 100},
                        ],
                    }
                ],
            }
        ],
        "extra_items": [{"name": "apple", "amount_g": 180}],
    }


def sample_annotation():
    return {
        "dish_annotations": [
            {
                "meal_index": 0,
                "dish_index": 0,
                "cooking_method": "stir_fry_low_oil",
                "cooking_method_confidence": 0.88,
                "cooking_method_reason": "The dish is a light stir-fry.",
            }
        ],
        "ingredient_annotations": [
            {
                "location_type": "dish_ingredient",
                "meal_index": 0,
                "dish_index": 0,
                "ingredient_index": 0,
                "extra_item_index": None,
                "food_group": "vegetables",
                "processing_level": "unprocessed",
                "processing_level_confidence": 0.9,
                "processing_level_reason": "Fresh tomato.",
                "search_name": "tomato",
                "liked_food_matches": ["tomato"],
                "liked_food_use_quality": "reasonable",
            },
            {
                "location_type": "extra_item",
                "meal_index": None,
                "dish_index": None,
                "ingredient_index": None,
                "extra_item_index": 0,
                "food_group": "fruits",
                "processing_level": "unprocessed",
                "processing_level_confidence": 0.92,
                "processing_level_reason": "Fresh fruit.",
                "search_name": "apple",
                "liked_food_matches": [],
                "liked_food_use_quality": "unknown",
            },
        ],
        "habit_match_level": "full",
        "diet_pattern_tags": ["home_cooked", "vegetable_dish"],
        "feasibility": {
            "estimated_prep_time_min": 20,
            "step_complexity": "simple",
            "ingredient_availability": "common",
            "cost_level": "low",
            "special_equipment_required": False,
        },
        "warnings": [],
    }


def test_openai_annotation_client_sends_schema_and_merges_annotations():
    session = FakeSession(sample_annotation())
    client = OpenAIAnnotationClient(
        OpenAIAnnotationConfig(api_key="test-key", model="test-model"),
        session=session,
    )

    annotated = annotate_recipe_input(sample_payload(), client=client)

    request_payload = session.last_request["json"]
    system_prompt = request_payload["messages"][0]["content"]
    assert session.last_request["url"].endswith("/chat/completions")
    assert request_payload["response_format"] == {"type": "json_object"}
    assert request_payload["temperature"] == 0.0
    assert "stir_fry_low_oil" in system_prompt
    assert "unprocessed" in system_prompt
    assert "vegetables" in system_prompt
    assert "search_name" in system_prompt
    dish = annotated["meals"][0]["dishes"][0]
    assert dish["cooking_method"] == "stir_fry_low_oil"
    assert dish["cooking_method_source"] == "ai"
    ingredient = dish["ingredients"][0]
    assert ingredient["food_group"] == "vegetables"
    assert ingredient["food_group_source"] == "ai"
    assert ingredient["processing_level"] == "unprocessed"
    assert ingredient["search_name"] == "tomato"
    assert ingredient["search_name_source"] == "ai"
    assert ingredient["liked_food_matches"] == ["tomato"]
    assert annotated["extra_items"][0]["processing_level"] == "unprocessed"
    assert annotated["extra_items"][0]["food_group"] == "fruits"
    assert annotated["extra_items"][0]["search_name"] == "apple"
    assert annotated["habit_match_level"] == "full"
    assert annotated["feasibility"]["step_complexity"] == "simple"
    assert annotated["ai_annotation_meta"]["model"] == "test-model"


def test_openai_annotation_config_reads_temperature_from_env(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_TEMPERATURE", "0.15")

    config = OpenAIAnnotationConfig.from_env()

    assert config.temperature == 0.15


def test_merge_annotation_falls_back_for_invalid_labels_and_ignores_scores():
    annotation = sample_annotation()
    annotation["dish_annotations"][0]["cooking_method"] = "not_a_method"
    annotation["ingredient_annotations"][0]["food_group"] = "not_a_group"
    annotation["ingredient_annotations"][0]["processing_level"] = "industrial"
    annotation["ingredient_annotations"][0]["liked_food_use_quality"] = "excellent"
    annotation["e_score"] = 8

    annotated = merge_annotation(sample_payload(), annotation, model="test-model")

    dish = annotated["meals"][0]["dishes"][0]
    ingredient = dish["ingredients"][0]
    warnings = annotated["ai_annotation_meta"]["warnings"]
    assert dish["cooking_method"] == "unknown_cooking_method"
    assert ingredient["processing_level"] == "unknown_processing_level"
    assert ingredient["liked_food_use_quality"] == "unknown"
    assert "e_score" not in annotated
    assert any("Invalid cooking_method" in warning for warning in warnings)
    assert any("Invalid food_group" in warning for warning in warnings)
    assert any("Invalid processing_level" in warning for warning in warnings)
    assert any("Ignored direct AI score field: e_score" in warning for warning in warnings)


def test_annotated_payload_is_consumed_by_c_and_e_scoring():
    payload = {
        "target_user": {
            "liked_foods": ["tomato"],
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
                                "name": "red vegetable",
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
                    }
                ],
            }
        ],
    }
    annotation = sample_annotation()

    annotated = merge_annotation(payload, annotation, model="test-model")
    result = evaluate_daily_diet(annotated)

    c_details = result["module_details"]["cooking_processing_safety"]
    e_details = result["module_details"]["personalization_feasibility"]
    assert c_details["dish_scores"][0]["method_used"] == "stir_fry_low_oil"
    assert c_details["ingredient_processing_scores"][0]["level_used"] == "unprocessed"
    assert e_details["liked_foods_details"]["matched_foods"][0]["match_source"] == "ai_label"
    assert e_details["habit_match_details"]["source"] == "explicit_label"
    assert e_details["feasibility_details"]["source"] == "structured_factors"


def test_ai_annotate_api_returns_annotated_payload(monkeypatch):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient
    from recipe_quality.api.app import app

    def fake_annotate(payload):
        return {
            **payload,
            "habit_match_level": "full",
            "ai_annotation_meta": {"provider": "openai", "warnings": []},
        }

    monkeypatch.setattr("recipe_quality.api.routes.annotate_recipe_input", fake_annotate)
    client = TestClient(app)

    response = client.post("/ai/annotate", json={"meals": []})

    assert response.status_code == 200
    data = response.json()
    assert data["annotated_input"]["habit_match_level"] == "full"
    assert data["ai_annotation_meta"]["provider"] == "openai"


def test_ai_annotate_api_returns_clear_error(monkeypatch):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient
    from recipe_quality.api.app import app

    def fake_annotate(_):
        raise AIAnnotationError("Missing OPENAI_API_KEY in environment.")

    monkeypatch.setattr("recipe_quality.api.routes.annotate_recipe_input", fake_annotate)
    client = TestClient(app)

    response = client.post("/ai/annotate", json={"meals": []})

    assert response.status_code == 503
    assert response.json()["detail"] == "Missing OPENAI_API_KEY in environment."
