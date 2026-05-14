from __future__ import annotations

import json
import os
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from recipe_quality.config_loader import (
    load_cooking_method_scores,
    load_food_group_targets,
    load_processing_level_scores,
)


SCHEMA_VERSION = "recipe_ai_annotation_v1"
DEFAULT_OPENAI_MODEL = "qwen-plus"
DEFAULT_OPENAI_API_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
UNKNOWN_COOKING_METHOD = "unknown_cooking_method"
UNKNOWN_PROCESSING_LEVEL = "unknown_processing_level"
LIKED_FOOD_USE_QUALITIES = {"reasonable", "risky", "unknown"}
HABIT_MATCH_LEVELS = {"full", "partial", "mismatch", "unknown"}
STEP_COMPLEXITIES = {"simple", "moderate", "complex", "unknown"}
AVAILABILITY_LEVELS = {"common", "mixed", "hard_to_find", "unknown"}
COST_LEVELS = {"low", "medium", "high", "unknown"}
DIRECT_SCORE_KEYS = {
    "score",
    "c1_score",
    "c2_score",
    "e_score",
    "e1_score",
    "e2_score",
    "e3_score",
    "cooking_score",
    "processing_score",
    "personalization_score",
}


class AIAnnotationError(RuntimeError):
    """Raised when AI annotation cannot be completed."""


@dataclass(slots=True)
class OpenAIAnnotationConfig:
    api_key: str
    model: str = DEFAULT_OPENAI_MODEL
    api_url: str = DEFAULT_OPENAI_API_URL
    timeout_seconds: float = 30.0

    @classmethod
    def from_env(cls) -> "OpenAIAnnotationConfig":
        """Load annotation settings from environment variables or .env."""
        try:
            from dotenv import load_dotenv
        except ModuleNotFoundError:
            load_dotenv = None
        if load_dotenv:
            load_dotenv()

        api_key = os.getenv("OPENAI_API_KEY")
        model = os.getenv("OPENAI_MODEL")
        api_url = os.getenv("OPENAI_API_URL")

        if not api_key:
            raise AIAnnotationError("Missing OPENAI_API_KEY in environment.")

        timeout = _to_float(os.getenv("OPENAI_TIMEOUT_SECONDS")) or 30.0
        return cls(
            api_key=api_key,
            model=model or DEFAULT_OPENAI_MODEL,
            api_url=_normalize_chat_completions_url(api_url or DEFAULT_OPENAI_API_URL),
            timeout_seconds=timeout,
        )


class OpenAIAnnotationClient:
    def __init__(
        self,
        config: OpenAIAnnotationConfig | None = None,
        session: Any | None = None,
    ):
        """Create an OpenAI-compatible chat client for recipe annotation."""
        self.config = config or OpenAIAnnotationConfig.from_env()
        if session is None:
            try:
                import requests
            except ModuleNotFoundError as exc:
                raise AIAnnotationError(
                    "The 'requests' package is required for Qwen annotation calls."
                ) from exc
            session = requests.Session()
        self.session = session

    def annotate(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Call Chat Completions and return parsed structured annotation JSON."""
        response = self.session.post(
            _normalize_chat_completions_url(self.config.api_url),
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            },
            json=self._request_payload(payload),
            timeout=self.config.timeout_seconds,
        )
        self._raise_for_response(response)
        return _extract_structured_output(response.json())

    def _request_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Build a qwen-plus/OpenAI-compatible chat completions request."""
        schema = build_annotation_schema(
            cooking_methods=sorted(load_cooking_method_scores()),
            food_groups=sorted(load_food_group_targets()),
            processing_levels=sorted(load_processing_level_scores()),
        )
        system_prompt = (
            AI_ANNOTATION_INSTRUCTIONS
            + "\nReturn a JSON object matching this JSON schema exactly:\n"
            + json.dumps(schema, ensure_ascii=False)
        )
        return {
            "model": self.config.model,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": json.dumps(payload, ensure_ascii=False),
                },
            ],
            "response_format": {"type": "json_object"},
        }

    @staticmethod
    def _raise_for_response(response: Any) -> None:
        """Convert an HTTP error response into a domain-specific exception."""
        if response.status_code >= 400:
            try:
                detail = response.json()
            except ValueError:
                detail = response.text
            raise AIAnnotationError(f"Qwen annotation request failed: HTTP {response.status_code} {detail}")


AI_ANNOTATION_INSTRUCTIONS = """Annotate the recipe for deterministic rule scoring.

Return only fields allowed by the JSON schema. Do not return any final scores.
Use the provided enum values for cooking_method and processing_level. Prefer
unknown labels when the recipe does not provide enough evidence.
For each ingredient, classify food_group using the provided enum values.
For each ingredient, provide search_name as a concise English FatSecret US
database query term while preserving the original ingredient name in the input.
"""


def annotate_recipe_input(
    payload: dict[str, Any],
    client: OpenAIAnnotationClient | None = None,
) -> dict[str, Any]:
    """Return a copy of payload enriched with AI-generated labels."""
    client = client or OpenAIAnnotationClient()
    annotation = client.annotate(payload)
    return merge_annotation(payload, annotation, model=client.config.model)


def merge_annotation(
    payload: dict[str, Any],
    annotation: dict[str, Any],
    model: str | None = None,
) -> dict[str, Any]:
    """Merge structured AI labels into a recipe payload by stable indices."""
    allowed_cooking = set(load_cooking_method_scores())
    allowed_food_groups = set(load_food_group_targets())
    allowed_processing = set(load_processing_level_scores())
    output = deepcopy(payload)
    warnings = _direct_score_warnings(annotation)

    for dish_annotation in annotation.get("dish_annotations") or []:
        dish = _dish_at(output, dish_annotation.get("meal_index"), dish_annotation.get("dish_index"))
        if dish is None:
            warnings.append(f"Skipped dish annotation with invalid indices: {dish_annotation}.")
            continue
        method = str(dish_annotation.get("cooking_method") or UNKNOWN_COOKING_METHOD)
        if method not in allowed_cooking:
            warnings.append(f"Invalid cooking_method={method}; used {UNKNOWN_COOKING_METHOD}.")
            method = UNKNOWN_COOKING_METHOD
        dish["cooking_method"] = method
        dish["cooking_method_source"] = "ai"
        dish["cooking_method_confidence"] = _bounded_confidence(
            dish_annotation.get("cooking_method_confidence")
        )
        dish["cooking_method_reason"] = str(dish_annotation.get("cooking_method_reason") or "")

    for ingredient_annotation in annotation.get("ingredient_annotations") or []:
        ingredient = _ingredient_at(output, ingredient_annotation)
        if ingredient is None:
            warnings.append(f"Skipped ingredient annotation with invalid indices: {ingredient_annotation}.")
            continue
        level = str(ingredient_annotation.get("processing_level") or UNKNOWN_PROCESSING_LEVEL)
        if level not in allowed_processing:
            warnings.append(f"Invalid processing_level={level}; used {UNKNOWN_PROCESSING_LEVEL}.")
            level = UNKNOWN_PROCESSING_LEVEL
        use_quality = str(ingredient_annotation.get("liked_food_use_quality") or "unknown")
        if use_quality not in LIKED_FOOD_USE_QUALITIES:
            warnings.append(f"Invalid liked_food_use_quality={use_quality}; used unknown.")
            use_quality = "unknown"
        search_name = str(ingredient_annotation.get("search_name") or "").strip()
        if not search_name:
            warnings.append(
                f"Missing search_name for ingredient {ingredient.get('name') or 'unknown ingredient'}."
            )
        food_group = str(ingredient_annotation.get("food_group") or "").strip()
        if food_group not in allowed_food_groups:
            warnings.append(
                f"Invalid food_group={food_group or 'missing'} for ingredient {ingredient.get('name') or 'unknown ingredient'}; left unset."
            )
            food_group = ""
        if food_group:
            ingredient["food_group"] = food_group
            ingredient["food_group_source"] = "ai"
        ingredient["processing_level"] = level
        ingredient["processing_level_source"] = "ai"
        ingredient["processing_level_confidence"] = _bounded_confidence(
            ingredient_annotation.get("processing_level_confidence")
        )
        ingredient["processing_level_reason"] = str(
            ingredient_annotation.get("processing_level_reason") or ""
        )
        ingredient["liked_food_matches"] = _string_list(
            ingredient_annotation.get("liked_food_matches")
        )
        ingredient["liked_food_use_quality"] = use_quality
        if search_name:
            ingredient["search_name"] = search_name
            ingredient["search_name_source"] = "ai"

    habit_match_level = str(annotation.get("habit_match_level") or "unknown")
    if habit_match_level not in HABIT_MATCH_LEVELS:
        warnings.append(f"Invalid habit_match_level={habit_match_level}; used unknown.")
        habit_match_level = "unknown"
    output["habit_match_level"] = habit_match_level
    output["diet_pattern_tags"] = _string_list(annotation.get("diet_pattern_tags"))
    output["feasibility"] = _validated_feasibility(annotation.get("feasibility") or {}, warnings)
    warnings.extend(_string_list(annotation.get("warnings")))
    output["ai_annotation_meta"] = {
        "provider": "Qwen",
        "model": model or annotation.get("model") or DEFAULT_OPENAI_MODEL,
        "schema_version": SCHEMA_VERSION,
        "warnings": warnings,
    }
    return output


def build_annotation_schema(
    cooking_methods: list[str],
    food_groups: list[str],
    processing_levels: list[str],
) -> dict[str, Any]:
    """Build the strict JSON schema sent to Qwen structured outputs.

    The schema constrains model output to the enum labels that the local rule
    engine already understands. This keeps AI annotation separate from scoring.
    """
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "dish_annotations",
            "ingredient_annotations",
            "habit_match_level",
            "diet_pattern_tags",
            "feasibility",
            "warnings",
        ],
        "properties": {
            "dish_annotations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "meal_index",
                        "dish_index",
                        "cooking_method",
                        "cooking_method_confidence",
                        "cooking_method_reason",
                    ],
                    "properties": {
                        "meal_index": {"type": "integer"},
                        "dish_index": {"type": "integer"},
                        "cooking_method": {"type": "string", "enum": cooking_methods},
                        "cooking_method_confidence": {"type": "number", "minimum": 0, "maximum": 1},
                        "cooking_method_reason": {"type": "string"},
                    },
                },
            },
            "ingredient_annotations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "location_type",
                        "meal_index",
                        "dish_index",
                        "ingredient_index",
                        "extra_item_index",
                        "food_group",
                        "processing_level",
                        "processing_level_confidence",
                        "processing_level_reason",
                        "search_name",
                        "liked_food_matches",
                        "liked_food_use_quality",
                    ],
                    "properties": {
                        "location_type": {
                            "type": "string",
                            "enum": ["dish_ingredient", "extra_item"],
                        },
                        "meal_index": {"type": ["integer", "null"]},
                        "dish_index": {"type": ["integer", "null"]},
                        "ingredient_index": {"type": ["integer", "null"]},
                        "extra_item_index": {"type": ["integer", "null"]},
                        "food_group": {"type": "string", "enum": food_groups},
                        "processing_level": {"type": "string", "enum": processing_levels},
                        "processing_level_confidence": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 1,
                        },
                        "processing_level_reason": {"type": "string"},
                        "search_name": {
                            "type": "string",
                            "description": "Concise English query term for searching FatSecret US, for example tomato, egg, cooked white rice.",
                        },
                        "liked_food_matches": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "liked_food_use_quality": {
                            "type": "string",
                            "enum": sorted(LIKED_FOOD_USE_QUALITIES),
                        },
                    },
                },
            },
            "habit_match_level": {"type": "string", "enum": sorted(HABIT_MATCH_LEVELS)},
            "diet_pattern_tags": {"type": "array", "items": {"type": "string"}},
            "feasibility": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "estimated_prep_time_min",
                    "step_complexity",
                    "ingredient_availability",
                    "cost_level",
                    "special_equipment_required",
                ],
                "properties": {
                    "estimated_prep_time_min": {"type": ["number", "null"], "minimum": 0},
                    "step_complexity": {"type": "string", "enum": sorted(STEP_COMPLEXITIES)},
                    "ingredient_availability": {
                        "type": "string",
                        "enum": sorted(AVAILABILITY_LEVELS),
                    },
                    "cost_level": {"type": "string", "enum": sorted(COST_LEVELS)},
                    "special_equipment_required": {"type": "boolean"},
                },
            },
            "warnings": {"type": "array", "items": {"type": "string"}},
        },
    }


def _extract_structured_output(response_payload: dict[str, Any]) -> dict[str, Any]:
    """Extract parsed JSON from common Responses API structured-output shapes."""
    for choice in response_payload.get("choices") or []:
        message = choice.get("message") or {}
        content = message.get("content")
        if content:
            return _loads_object(content)
    if isinstance(response_payload.get("output_parsed"), dict):
        return response_payload["output_parsed"]
    if response_payload.get("output_text"):
        return _loads_object(response_payload["output_text"])
    for output in response_payload.get("output") or []:
        for content in output.get("content") or []:
            if isinstance(content.get("parsed"), dict):
                return content["parsed"]
            text = content.get("text")
            if text:
                return _loads_object(text)
    raise AIAnnotationError("OpenAI annotation response did not include structured output.")


def _loads_object(text: str) -> dict[str, Any]:
    """Parse model text as a JSON object and raise a clear annotation error."""
    text = _strip_json_fence(text)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AIAnnotationError("OpenAI annotation output was not valid JSON.") from exc
    if not isinstance(parsed, dict):
        raise AIAnnotationError("OpenAI annotation output must be a JSON object.")
    return parsed


def _strip_json_fence(text: str) -> str:
    """Remove common markdown code fences from model JSON output."""
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    return stripped


def _dish_at(payload: dict[str, Any], meal_index: Any, dish_index: Any) -> dict[str, Any] | None:
    """Return a dish by AI-provided stable indices, or None if invalid."""
    try:
        return payload["meals"][int(meal_index)]["dishes"][int(dish_index)]
    except (KeyError, IndexError, TypeError, ValueError):
        return None


def _ingredient_at(payload: dict[str, Any], annotation: dict[str, Any]) -> dict[str, Any] | None:
    """Return a dish ingredient or extra item identified by annotation indices."""
    try:
        if annotation.get("location_type") == "extra_item":
            return payload["extra_items"][int(annotation.get("extra_item_index"))]
        return payload["meals"][int(annotation.get("meal_index"))]["dishes"][
            int(annotation.get("dish_index"))
        ]["ingredients"][int(annotation.get("ingredient_index"))]
    except (KeyError, IndexError, TypeError, ValueError):
        return None


def _validated_feasibility(feasibility: dict[str, Any], warnings: list[str]) -> dict[str, Any]:
    """Normalize feasibility labels and collect warnings for unsupported values."""
    step_complexity = _enum_or_unknown(
        feasibility.get("step_complexity"), STEP_COMPLEXITIES, "step_complexity", warnings
    )
    availability = _enum_or_unknown(
        feasibility.get("ingredient_availability"),
        AVAILABILITY_LEVELS,
        "ingredient_availability",
        warnings,
    )
    cost = _enum_or_unknown(feasibility.get("cost_level"), COST_LEVELS, "cost_level", warnings)
    return {
        "estimated_prep_time_min": _to_float(feasibility.get("estimated_prep_time_min")),
        "step_complexity": step_complexity,
        "ingredient_availability": availability,
        "cost_level": cost,
        "special_equipment_required": bool(feasibility.get("special_equipment_required", False)),
    }


def _enum_or_unknown(value: Any, allowed: set[str], field_name: str, warnings: list[str]) -> str:
    """Return an allowed enum value, falling back to unknown with a warning."""
    text = str(value or "unknown")
    if text not in allowed:
        warnings.append(f"Invalid {field_name}={text}; used unknown.")
        return "unknown"
    return text


def _normalize_chat_completions_url(api_url: str) -> str:
    """Accept either a base compatible-mode URL or the full chat completions URL."""
    url = api_url.rstrip("/")
    if url.endswith("/chat/completions"):
        return url
    return f"{url}/chat/completions"


def _direct_score_warnings(value: Any, path: str = "") -> list[str]:
    """Find direct score fields in AI output so callers can ignore and report them."""
    warnings: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            if str(key) in DIRECT_SCORE_KEYS or str(key).endswith("_score"):
                warnings.append(f"Ignored direct AI score field: {child_path}.")
            warnings.extend(_direct_score_warnings(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            warnings.extend(_direct_score_warnings(child, f"{path}[{index}]"))
    return warnings


def _bounded_confidence(value: Any) -> float:
    """Convert confidence to a float in the inclusive 0 to 1 range."""
    confidence = _to_float(value)
    if confidence is None:
        return 0.0
    return min(max(confidence, 0.0), 1.0)


def _string_list(value: Any) -> list[str]:
    """Normalize optional list-like model output to non-empty strings."""
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _to_float(value: Any) -> float | None:
    """Safely convert optional input to float."""
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
