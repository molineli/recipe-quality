from recipe_quality.targets import estimate_daily_energy_kcal, resolve_daily_targets


def test_estimate_daily_energy_uses_user_profile_and_activity_level():
    """验证可根据用户性别、年龄、身高、体重和活动水平估算每日能量。"""
    energy = estimate_daily_energy_kcal(
        {
            "sex": "female",
            "age": 30,
            "height_cm": 165,
            "weight_kg": 58,
            "activity_level": "light",
        }
    )

    assert energy == 1787.84


def test_estimate_daily_energy_falls_back_to_default_when_profile_is_incomplete():
    """验证用户资料不完整时每日能量回退到默认 2000 kcal。"""
    assert estimate_daily_energy_kcal({"sex": "female"}) == 2000


def test_resolve_daily_targets_uses_user_profile_energy():
    """验证每日目标会使用 target_user 估算出的能量。"""
    targets = resolve_daily_targets(
        {
            "sex": "female",
            "age": 30,
            "height_cm": 165,
            "weight_kg": 58,
            "activity_level": "light",
        }
    )

    assert targets["energy_kcal"] == 1787.84


def test_resolve_daily_targets_uses_default_limits():
    """验证每日目标会包含内置限制性成分默认值。"""
    targets = resolve_daily_targets()

    assert targets["energy_kcal"] == 2000
    assert targets["sodium_mg_limit"] == 2000
    assert targets["cooking_oil_g_limit"] == 25
    assert targets["added_sugar_g_limit"] == 25
