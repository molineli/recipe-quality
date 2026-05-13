from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from recipe_quality.aggregator import resolve_and_aggregate
from recipe_quality.engine import evaluate_daily_diet
from recipe_quality.fatsecret import FatSecretClient, FatSecretResolver
from recipe_quality.normalizer import normalize_recipe_input


def main() -> int:
    """命令行入口：解析全天饮食 JSON，汇总营养并输出初始评分。"""
    if len(sys.argv) < 2:
        print("Usage: python scripts/calculate_initial_totals.py <input_day.json>", file=sys.stderr)
        return 2
    input_path = Path(sys.argv[1])
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    resolver = FatSecretResolver(FatSecretClient())
    normalized = normalize_recipe_input(payload)
    resolved = resolve_and_aggregate(
        resolver,
        normalized["ingredient_records"],
        normalized["condiments"],
        dish_records=normalized["dish_records"],
        record_quality=payload.get("record_quality"),
    )
    enriched = {
        **payload,
        "items": resolved["items"],
        "ingredient_records": resolved["ingredient_records"],
        "dish_records": resolved["dish_records"],
        "daily_totals": resolved["daily_totals"],
    }
    result = {
        "resolved": resolved,
        "evaluation": evaluate_daily_diet(enriched),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
