from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from recipe_quality.fatsecret import FatSecretClient, FatSecretResolver


def main() -> int:
    """Run a live FatSecret US nutrition lookup with an English search_name."""
    item = {
        "name": "米饭",
        "search_name": "rice",
        "search_name_source": "manual_smoke_test",
        "amount_g": 200,
        "food_group": "grains_and_tubers",
    }
    client = FatSecretClient()
    resolver = FatSecretResolver(client)
    resolved = resolver.resolve_item(item)
    result = {
        "fatsecret_region": client.config.region,
        "fatsecret_language": client.config.language,
        "input_name": resolved.name,
        "search_name": resolved.search_name,
        "fatsecret_food_id": resolved.fatsecret_food_id,
        "fatsecret_food_name": resolved.fatsecret_food_name,
        "serving_used": resolved.serving_used,
        "match_confidence": resolved.match_confidence,
        "nutrition_estimation_status": resolved.nutrition_estimation_status,
        "error": resolved.error,
        "nutrients": resolved.nutrients.to_dict(),
        "top_candidates": [_candidate_summary(candidate) for candidate in resolved.candidates[:3]],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if resolved.error is None else 1


def _candidate_summary(candidate: dict) -> dict:
    return {
        "food_id": candidate.get("food_id"),
        "food_name": candidate.get("food_name"),
        "food_type": candidate.get("food_type"),
        "brand_name": candidate.get("brand_name"),
    }


if __name__ == "__main__":
    raise SystemExit(main())
