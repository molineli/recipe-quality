from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from recipe_quality.fatsecret import FatSecretClient


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python scripts/fatsecret_get_food.py <food_id>", file=sys.stderr)
        return 2
    result = FatSecretClient().get_food(sys.argv[1])
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

