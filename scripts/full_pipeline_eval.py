from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from recipe_quality.pipeline import evaluate_full_pipeline


def main() -> int:
    if len(sys.argv) < 2:
        print(
            "Usage: python scripts/full_pipeline_eval.py <input_day.json>",
            file=sys.stderr,
        )
        return 2

    input_path = Path(sys.argv[1])
    payload = json.loads(input_path.read_text(encoding="utf-8"))

    result = evaluate_full_pipeline(payload)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
