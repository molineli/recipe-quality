from __future__ import annotations


BASE_BASIC_NUTRITION_TARGETS = {
    "fiber_g": 25.0,
    "calcium_mg": 800.0,
    "potassium_mg": 2000.0,
    "vitamin_c_mg": 100.0,
}

DEFAULT_ENERGY_KCAL = 2000.0
PROTEIN_ENERGY_RATIO = 0.15
IRON_TARGETS_BY_SEX = {
    "male": 12.0,
    "female": 20.0,
}


def resolve_basic_nutrition_targets(
    daily_targets: dict | None = None,
    target_user: dict | None = None,
) -> dict:
    """根据能量目标和用户性别解析 A 模块使用的动态营养目标值。"""
    daily_targets = daily_targets or {}
    target_user = target_user or {}
    energy_kcal = float(daily_targets.get("energy_kcal") or DEFAULT_ENERGY_KCAL)
    sex = str(target_user.get("sex") or "").lower()
    targets = {
        **BASE_BASIC_NUTRITION_TARGETS,
        "protein_g": energy_kcal * PROTEIN_ENERGY_RATIO / 4,
        "iron_mg": IRON_TARGETS_BY_SEX.get(sex, IRON_TARGETS_BY_SEX["male"]),
    }
    for key in ("protein_g", "fiber_g", "calcium_mg", "iron_mg", "potassium_mg", "vitamin_c_mg"):
        if key in daily_targets:
            targets[key] = float(daily_targets[key])
    return targets

