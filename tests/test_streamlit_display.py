import re
from pathlib import Path

from streamlit_app import (
    _display_condiment_rows,
    _display_extra_item_rows,
    _display_ingredient_rows,
    _food_group_rows,
    _grade_badge_class,
    _grade_cap_messages,
    _internalize_condiment_rows,
    _internalize_extra_item_rows,
    _internalize_ingredient_rows,
    _label_activity_level,
    _label_food_group,
    _label_habit_pattern,
    _label_meal_name,
    _label_module_key,
    _label_sex,
    _label_status,
    _module_score_rows,
    _primary_limiting_factor,
)


def test_module_score_rows_use_chinese_labels_and_keep_unknown_keys():
    rows = _module_score_rows(
        {
            "basic_nutrition_quality": 30.264,
            "daily_intake_fit": 4.58,
            "custom_module": 1,
        }
    )

    assert rows == [
        {"模块": "基础营养质量", "得分": 30.26},
        {"模块": "全天摄入适配", "得分": 4.58},
        {"模块": "custom_module", "得分": 1.0},
    ]
    assert _label_module_key("missing_key") == "missing_key"


def test_food_group_rows_use_chinese_labels_and_sort_by_weight():
    rows = _food_group_rows(
        {
            "dairy": 250,
            "vegetables": 400,
            "unknown_group": 5,
        }
    )

    assert rows == [
        {"食物组": "蔬菜类", "重量 g": 400.0},
        {"食物组": "奶类", "重量 g": 250.0},
        {"食物组": "unknown_group", "重量 g": 5.0},
    ]
    assert _label_food_group("unknown_group") == "unknown_group"


def test_grade_cap_message_explains_energy_ratio_in_plain_chinese():
    messages = _grade_cap_messages(
        [
            {
                "trigger": "energy_ratio_outside_range",
                "value": 0.728868355110077,
                "cap_grade": "C",
            }
        ]
    )

    assert messages == [
        "本次最终等级被限制为 C，原因是全天能量摄入约为目标的 73%，全天能量摄入明显偏离推荐范围。"
    ]
    assert _primary_limiting_factor(
        [{"trigger": "energy_ratio_outside_range", "value": 0.72, "cap_grade": "C"}]
    ) == "全天能量摄入明显偏离推荐范围"
    assert _primary_limiting_factor([]) == "未触发等级封顶"


def test_status_label_falls_back_to_raw_value():
    assert _label_status("resolved") == "已解析"
    assert _label_status("custom_status") == "custom_status"
    assert _grade_badge_class("A") == "rq-grade-a"
    assert _grade_badge_class("unknown") == "rq-grade-c"


def test_basic_user_facing_labels_are_chinese_with_fallbacks():
    assert _label_sex("female") == "女性"
    assert _label_activity_level("light") == "轻体力活动"
    assert _label_habit_pattern("chinese_home_meals") == "中式家常饮食"
    assert _label_meal_name("breakfast") == "早餐"
    assert _label_meal_name("late_night") == "late_night"


def test_demo_table_rows_display_chinese_and_convert_back_to_internal_values():
    ingredient_rows = _display_ingredient_rows(
        [
            {
                "meal_name": "breakfast",
                "meal_time": "08:00",
                "dish_name": "牛奶鸡蛋早餐",
                "dish_type": "simple_foods",
                "ingredient_name": "牛奶",
                "amount_g": 250,
                "edible": True,
            }
        ]
    )
    condiment_rows = _display_condiment_rows(
        [{"meal_name": "lunch", "dish_name": "番茄炒蛋", "condiment_name": "食盐", "amount_g": 1.5}]
    )
    extra_rows = _display_extra_item_rows(
        [{"meal_name": "snack", "name": "苹果", "amount_g": 180, "item_type": "fruit"}]
    )

    assert ingredient_rows[0]["meal_name"] == "早餐"
    assert ingredient_rows[0]["dish_type"] == "简单食物"
    assert condiment_rows[0]["meal_name"] == "午餐"
    assert extra_rows[0]["meal_name"] == "加餐"
    assert extra_rows[0]["item_type"] == "水果"

    assert _internalize_ingredient_rows(ingredient_rows)[0]["meal_name"] == "breakfast"
    assert _internalize_ingredient_rows(ingredient_rows)[0]["dish_type"] == "simple_foods"
    assert _internalize_condiment_rows(condiment_rows)[0]["meal_name"] == "lunch"
    assert _internalize_extra_item_rows(extra_rows)[0]["meal_name"] == "snack"
    assert _internalize_extra_item_rows(extra_rows)[0]["item_type"] == "fruit"


def test_download_buttons_have_unique_stable_keys_and_plotly_replaces_bar_chart():
    source = Path("streamlit_app.py").read_text(encoding="utf-8")
    keys = re.findall(r"download_button\([\s\S]*?key=\"([^\"]+)\"", source)

    assert keys == ["download_current_input_json", "download_full_result_json"]
    assert len(keys) == len(set(keys))
    assert "st.bar_chart" not in source
    assert "st.plotly_chart" in source
