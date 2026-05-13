from __future__ import annotations

from typing import Any


BASE_BASIC_NUTRITION_TARGETS = {
    "fiber_g": 25.0,
    "calcium_mg": 800.0,
    "potassium_mg": 2000.0,
    "vitamin_c_mg": 100.0,
}

DEFAULT_ENERGY_KCAL = 2000.0
DEFAULT_LIMIT_TARGETS = {
    "sodium_mg_limit": 2000.0,
    "cooking_oil_g_limit": 25.0,
    "added_sugar_g_limit": 25.0,
}
ACTIVITY_FACTORS = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
    "very_active": 1.9,
}
PROTEIN_ENERGY_RATIO = 0.15
IRON_TARGETS_BY_SEX = {
    "male": 12.0,
    "female": 20.0,
}


def resolve_daily_targets(
    target_user: dict[str, Any] | None = None,
) -> dict[str, float]:
    """Resolve daily targets from default limits and target user profile."""
    target_user = target_user or {}
    resolved = dict(DEFAULT_LIMIT_TARGETS)
    resolved["energy_kcal"] = estimate_daily_energy_kcal(target_user)
    return resolved


def estimate_daily_energy_kcal(target_user: dict[str, Any] | None = None) -> float:
    """根据性别、年龄、身高、体重和活动水平估算每日能量需求。"""
    target_user = target_user or {}
    sex = str(target_user.get("sex") or "").lower()
    age = _to_float(target_user.get("age"))
    height_cm = _to_float(target_user.get("height_cm"))
    weight_kg = _to_float(target_user.get("weight_kg"))
    if sex not in {"male", "female"} or not age or not height_cm or not weight_kg:
        return DEFAULT_ENERGY_KCAL
    if sex == "male":
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    else:
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age - 161
    activity_factor = ACTIVITY_FACTORS.get(str(target_user.get("activity_level") or "").lower(), 1.2)
    return round(bmr * activity_factor, 2)


def resolve_basic_nutrition_targets(
    resolved_targets: dict | None = None,
    target_user: dict | None = None,
) -> dict:
    """根据能量目标和用户性别解析 A 模块使用的动态营养目标值。"""
    resolved_targets = resolved_targets or {}
    target_user = target_user or {}
    energy_kcal = float(resolved_targets.get("energy_kcal") or DEFAULT_ENERGY_KCAL)
    sex = str(target_user.get("sex") or "").lower()
    targets = {
        **BASE_BASIC_NUTRITION_TARGETS,
        "protein_g": energy_kcal * PROTEIN_ENERGY_RATIO / 4,
        "iron_mg": IRON_TARGETS_BY_SEX.get(sex, IRON_TARGETS_BY_SEX["male"]),
    }
    for key in ("protein_g", "fiber_g", "calcium_mg", "iron_mg", "potassium_mg", "vitamin_c_mg"):
        if key in resolved_targets:
            targets[key] = float(resolved_targets[key])
    return targets


def _to_float(value: Any) -> float | None:
    """将用户体征输入安全转换为浮点数。"""
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
