from recipe_quality.scoring.basic_nutrition import FOOD_GROUP_TARGETS, score_food_group_coverage
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


def test_resolve_targets_allows_resolved_target_overrides():
    """验证已解析目标会覆盖 A 模块动态默认目标。"""
    targets = resolve_basic_nutrition_targets(
        {"energy_kcal": 2000, "protein_g": 60, "iron_mg": 18},
        {"sex": "female"},
    )

    assert targets["protein_g"] == 60
    assert targets["iron_mg"] == 18


def test_food_group_targets_are_loaded_from_config():
    """验证 A1 食物组目标值来自 configs/food_groups.yaml。"""
    assert FOOD_GROUP_TARGETS["vegetables"]["target_g"] == 400

    _, details = score_food_group_coverage(
        {
            "food_group_amounts_g": {"vegetables": 200},
            "food_group_count": 1,
        }
    )

    assert details["group_scores"]["vegetables"] == 1.5
