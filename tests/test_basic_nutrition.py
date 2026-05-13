from recipe_quality.targets import resolve_basic_nutrition_targets


def test_resolve_targets_uses_15_percent_energy_for_protein_at_2000_kcal():
    """验证 2000 kcal 时蛋白质目标按 15% 供能比计算为 75g。"""
    targets = resolve_basic_nutrition_targets({"energy_kcal": 2000})

    assert targets["protein_g"] == 75


def test_resolve_targets_uses_15_percent_energy_for_protein_at_1800_kcal():
    """验证 1800 kcal 时蛋白质目标按 15% 供能比计算为 67.5g。"""
    targets = resolve_basic_nutrition_targets({"energy_kcal": 1800})

    assert targets["protein_g"] == 67.5


def test_resolve_targets_uses_male_iron_target():
    """验证男性铁目标为 12mg。"""
    targets = resolve_basic_nutrition_targets(target_user={"sex": "male"})

    assert targets["iron_mg"] == 12


def test_resolve_targets_uses_female_iron_target():
    """验证女性铁目标为 20mg。"""
    targets = resolve_basic_nutrition_targets(target_user={"sex": "female"})

    assert targets["iron_mg"] == 20


def test_resolve_targets_defaults_unknown_sex_to_male_iron_target():
    """验证性别缺失或未知时铁目标默认使用 12mg。"""
    targets = resolve_basic_nutrition_targets()

    assert targets["iron_mg"] == 12


def test_resolve_targets_allows_explicit_daily_target_overrides():
    """验证 daily_targets 中显式目标会覆盖动态默认目标。"""
    targets = resolve_basic_nutrition_targets(
        {"energy_kcal": 2000, "protein_g": 60, "iron_mg": 18},
        {"sex": "female"},
    )

    assert targets["protein_g"] == 60
    assert targets["iron_mg"] == 18
