from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from recipe_quality.fatsecret import FatSecretClient


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python scripts/fatsecret_search.py <query> [max_results]", file=sys.stderr)
        return 2
    query = sys.argv[1]
    max_results = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    result = FatSecretClient().search_foods(query, max_results=max_results)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

