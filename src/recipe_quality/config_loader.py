from __future__ import annotations

from pathlib import Path
from typing import Any


CONFIG_DIR = Path(__file__).resolve().parents[2] / "configs"
FOOD_GROUPS_CONFIG_PATH = CONFIG_DIR / "food_groups.yaml"
COOKING_METHODS_CONFIG_PATH = CONFIG_DIR / "cooking_methods.yaml"
PROCESSING_LEVELS_CONFIG_PATH = CONFIG_DIR / "processing_levels.yaml"


def load_food_group_targets(
    config_path: Path = FOOD_GROUPS_CONFIG_PATH,
) -> dict[str, dict[str, float]]:
    """从 food_groups.yaml 读取 A1 食物组评分目标，并转换为浮点数配置。"""
    config = _load_yaml_mapping(config_path)
    food_groups = config.get("food_groups")
    if not isinstance(food_groups, dict):
        raise ValueError(f"{config_path} must contain a food_groups mapping")

    targets: dict[str, dict[str, float]] = {}
    for group, values in food_groups.items():
        if not isinstance(values, dict):
            raise ValueError(f"{config_path} food_groups.{group} must be a mapping")
        targets[str(group)] = {
            "weight": float(values["weight"]),
            "target_g": float(values["target_g"]),
        }
    return targets


def load_cooking_method_scores(
    config_path: Path = COOKING_METHODS_CONFIG_PATH,
) -> dict[str, float]:
    """Load C1 cooking method base scores."""
    return _load_score_mapping(config_path, "cooking_method_score")


def load_processing_level_scores(
    config_path: Path = PROCESSING_LEVELS_CONFIG_PATH,
) -> dict[str, float]:
    """Load C2 ingredient processing level scores."""
    return _load_score_mapping(config_path, "processing_level_score")


def _load_score_mapping(config_path: Path, root_key: str) -> dict[str, float]:
    config = _load_yaml_mapping(config_path)
    values = config.get(root_key)
    if not isinstance(values, dict):
        raise ValueError(f"{config_path} must contain a {root_key} mapping")
    return {str(key): float(value) for key, value in values.items()}


def _load_yaml_mapping(config_path: Path) -> dict[str, Any]:
    """优先使用 PyYAML 读取配置；缺少 PyYAML 时使用当前配置结构的轻量解析器。"""
    try:
        import yaml
    except ModuleNotFoundError:
        return _parse_simple_yaml_mapping(config_path)

    with config_path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{config_path} must contain a mapping")
    return data


def _parse_simple_yaml_mapping(config_path: Path) -> dict[str, Any]:
    """解析当前 food_groups.yaml 的三层缩进结构，避免新增必需运行时依赖。"""
    data: dict[str, Any] = {}
    current_root: dict[str, Any] | None = None
    current_group: dict[str, Any] | None = None

    for raw_line in config_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        text = line.strip()
        if indent == 0 and text.endswith(":"):
            current_root = {}
            data[text[:-1]] = current_root
            current_group = None
        elif indent == 2 and text.endswith(":") and current_root is not None:
            current_group = {}
            current_root[text[:-1]] = current_group
        elif indent == 2 and ":" in text and current_root is not None:
            key, value = text.split(":", 1)
            current_root[key.strip()] = _parse_scalar(value.strip())
            current_group = None
        elif indent == 4 and ":" in text and current_group is not None:
            key, value = text.split(":", 1)
            current_group[key.strip()] = _parse_scalar(value.strip())
        else:
            raise ValueError(f"Unsupported YAML structure in {config_path}: {raw_line}")

    return data


def _parse_scalar(value: str) -> Any:
    try:
        return float(value)
    except ValueError:
        return value
