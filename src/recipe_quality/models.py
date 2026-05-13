from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


NUTRIENT_KEYS = (
    "energy_kcal",
    "protein_g",
    "fat_g",
    "saturated_fat_g",
    "carbohydrate_g",
    "fiber_g",
    "sodium_mg",
    "potassium_mg",
    "calcium_mg",
    "iron_mg",
    "vitamin_c_mg",
    "added_sugar_g",
)


@dataclass(slots=True)
class Nutrients:
    energy_kcal: float | None = None
    protein_g: float | None = None
    fat_g: float | None = None
    saturated_fat_g: float | None = None
    carbohydrate_g: float | None = None
    fiber_g: float | None = None
    sodium_mg: float | None = None
    potassium_mg: float | None = None
    calcium_mg: float | None = None
    iron_mg: float | None = None
    vitamin_c_mg: float | None = None
    added_sugar_g: float | None = None

    @classmethod
    def from_mapping(cls, data: dict[str, Any] | None) -> "Nutrients":
        """从字典中读取营养字段，转换为 Nutrients 对象。"""
        data = data or {}
        return cls(**{key: _to_optional_float(data.get(key)) for key in NUTRIENT_KEYS})

    def to_dict(self) -> dict[str, float | None]:
        """将营养对象转换为可 JSON 序列化的字典。"""
        return {key: getattr(self, key) for key in NUTRIENT_KEYS}

    def scaled(self, factor: float) -> "Nutrients":
        """按指定比例缩放所有已有营养数值。"""
        return Nutrients(
            **{
                key: None if getattr(self, key) is None else getattr(self, key) * factor
                for key in NUTRIENT_KEYS
            }
        )


@dataclass(slots=True)
class ResolvedFoodItem:
    name: str
    amount_g: float
    ingredient_id: str | None = None
    meal_name: str | None = None
    dish_name: str | None = None
    edible: bool = True
    food_group: str | None = None
    classification_source: str | None = None
    classification_confidence: float | None = None
    fatsecret_food_id: str | None = None
    fatsecret_food_name: str | None = None
    serving_used: str | None = None
    match_confidence: str = "unresolved"
    nutrition_estimation_status: str = "unresolved"
    nutrients: Nutrients = field(default_factory=Nutrients)
    candidates: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """将解析后的食物项转换为 API/脚本输出使用的字典。"""
        return {
            "ingredient_id": self.ingredient_id,
            "name": self.name,
            "amount_g": self.amount_g,
            "meal_name": self.meal_name,
            "dish_name": self.dish_name,
            "edible": self.edible,
            "food_group": self.food_group,
            "classification_source": self.classification_source,
            "classification_confidence": self.classification_confidence,
            "fatsecret_food_id": self.fatsecret_food_id,
            "fatsecret_food_name": self.fatsecret_food_name,
            "serving_used": self.serving_used,
            "match_confidence": self.match_confidence,
            "nutrition_estimation_status": self.nutrition_estimation_status,
            "nutrients": self.nutrients.to_dict(),
            "candidates": self.candidates,
            "error": self.error,
        }


def _to_optional_float(value: Any) -> float | None:
    """将输入值安全转换为浮点数；缺失或非法值返回 None。"""
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
