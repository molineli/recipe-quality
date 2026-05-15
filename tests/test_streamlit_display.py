import re
from pathlib import Path

from streamlit_app import (
    _core_nutrition_cards,
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
    _meal_energy_rows_from_result,
    _meal_energy_rows,
    _module_score_rows,
    _nutrition_display_targets,
    _nutrition_progress_rows,
    _primary_limiting_factor,
    _recipe_payload_to_session_state,
    _run_pipeline,
    _stable_payload_hash,
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


def test_meal_energy_rows_sum_main_meals_and_ignore_snacks_unknown_or_missing_energy():
    rows = _meal_energy_rows(
        [
            {"meal_name": "breakfast", "nutrients": {"energy_kcal": 100}},
            {"meal_name": "breakfast", "nutrients": {"energy_kcal": "50.25"}},
            {"meal_name": "lunch", "nutrients": {"energy_kcal": 620.126}},
            {"meal_name": "dinner", "energy_kcal": 480},
            {"meal_name": "snack", "nutrients": {"energy_kcal": 210}},
            {"meal_name": "late_night", "nutrients": {"energy_kcal": 90}},
            {"meal_name": "lunch", "nutrients": {"energy_kcal": None}},
            {"meal_name": "dinner", "nutrients": {"energy_kcal": "unknown"}},
        ]
    )

    assert rows == [
        {"餐次": "早餐", "能量 kcal": 150.25},
        {"餐次": "午餐", "能量 kcal": 620.13},
        {"餐次": "晚餐", "能量 kcal": 480.0},
    ]


def test_meal_energy_rows_returns_empty_without_main_meal_energy():
    rows = _meal_energy_rows(
        [
            {"meal_name": "snack", "nutrients": {"energy_kcal": 210}},
            {"meal_name": "breakfast", "nutrients": {"energy_kcal": None}},
            {"meal_name": "lunch", "nutrients": {"energy_kcal": "unknown"}},
        ]
    )

    assert rows == []


def test_meal_energy_rows_from_result_uses_compact_pipeline_resolved_items():
    rows = _meal_energy_rows_from_result(
        {
            "daily_totals": {"energy_kcal": 900},
            "resolved_items": [
                {"meal_name": "breakfast", "nutrients": {"energy_kcal": 100}},
                {"meal_name": "lunch", "nutrients": {"energy_kcal": 500}},
                {"meal_name": "dinner", "nutrients": {"energy_kcal": 300}},
            ],
        }
    )

    assert rows == [
        {"餐次": "早餐", "能量 kcal": 100.0},
        {"餐次": "午餐", "能量 kcal": 500.0},
        {"餐次": "晚餐", "能量 kcal": 300.0},
    ]


def test_stable_payload_hash_is_repeatable_for_same_payload():
    payload = {
        "date": "2026-05-15",
        "meals": [{"meal_name": "breakfast", "dishes": []}],
    }

    assert _stable_payload_hash(payload) == _stable_payload_hash(payload)


def test_stable_payload_hash_ignores_dict_field_order():
    first = {
        "date": "2026-05-15",
        "target_user": {"age": 30, "sex": "female"},
        "meals": [{"meal_name": "breakfast", "dishes": []}],
    }
    second = {
        "meals": [{"dishes": [], "meal_name": "breakfast"}],
        "target_user": {"sex": "female", "age": 30},
        "date": "2026-05-15",
    }

    assert _stable_payload_hash(first) == _stable_payload_hash(second)


def test_stable_payload_hash_changes_when_payload_content_changes():
    first = {"meals": [{"meal_name": "breakfast", "dishes": []}]}
    second = {"meals": [{"meal_name": "lunch", "dishes": []}]}

    assert _stable_payload_hash(first) != _stable_payload_hash(second)


def test_run_pipeline_reuses_cached_result_for_same_payload(monkeypatch):
    calls = []

    def fake_evaluate_full_pipeline(payload, progress_callback=None):
        calls.append(payload)
        if progress_callback:
            progress_callback("completed", "done")
        return {"total_score": 88, "payload": payload}

    class FakeStatus:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def update(self, **kwargs):
            return None

    class FakeProgress:
        def progress(self, value, text=None):
            return None

    class FakeStreamlit:
        def __init__(self):
            self.session_state = {}
            self.infos = []

        def status(self, label, expanded=False):
            return FakeStatus()

        def progress(self, value, text=None):
            return FakeProgress()

        def write(self, message):
            return None

        def error(self, message):
            raise AssertionError(message)

        def exception(self, exc):
            raise exc

        def info(self, message):
            self.infos.append(message)

    monkeypatch.setattr("streamlit_app.evaluate_full_pipeline", fake_evaluate_full_pipeline)
    st = FakeStreamlit()
    payload = {"date": "2026-05-15", "meals": [{"meal_name": "breakfast", "dishes": []}]}

    _run_pipeline(st, payload)
    _run_pipeline(st, {"meals": [{"dishes": [], "meal_name": "breakfast"}], "date": "2026-05-15"})

    assert len(calls) == 1
    assert st.session_state["pipeline_result"]["total_score"] == 88
    assert st.infos == ["输入未变化，已复用上次计算结果。"]


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


def test_nutrition_cards_and_progress_rows_use_targets_and_status_labels():
    targets = _nutrition_display_targets(
        {"sex": "female", "age": 30, "height_cm": 165, "weight_kg": 58, "activity_level": "light"}
    )
    daily_totals = {
        "energy_kcal": 1303.1,
        "protein_g": 80.43,
        "fat_g": 36.69,
        "carbohydrate_g": 164.93,
        "fiber_g": 16.16,
        "sodium_mg": 3281,
        "added_sugar_g": 0,
    }

    cards = _core_nutrition_cards(daily_totals, targets)
    assert [card["label"] for card in cards] == ["能量", "蛋白质", "脂肪", "碳水化合物"]
    assert cards[0]["value_text"] == "1303 kcal"
    assert cards[0]["status"] == "风险"
    assert cards[1]["status"] == "良好"

    progress_rows = _nutrition_progress_rows(daily_totals, targets)
    assert [row["label"] for row in progress_rows] == ["能量", "蛋白质", "膳食纤维", "钠", "添加糖"]
    assert progress_rows[0]["actual_text"] == "1303 kcal"
    assert progress_rows[0]["percent_text"] == "73%"
    assert progress_rows[3]["status"] == "风险"
    assert progress_rows[4]["status"] == "良好"


def test_recipe_payload_to_session_state_loads_ai_generated_json_without_ai_labels():
    raw_json = b"""{
      "evaluation_scope": "whole_day",
      "target_population": "healthy_adult",
      "date": "2026-05-12",
      "target_user": {
        "sex": "female",
        "age": 30,
        "height_cm": 165,
        "weight_kg": 58,
        "activity_level": "light",
        "liked_foods": ["\xe9\xb8\xa1\xe8\x9b\x8b"],
        "disliked_foods": [],
        "dietary_restrictions": [],
        "habit_pattern": "chinese_home_meals"
      },
      "meals": [
        {
          "meal_name": "breakfast",
          "meal_time": "08:00",
          "dishes": [
            {
              "dish_name": "\xe7\x87\x95\xe9\xba\xa6\xe9\xb8\xa1\xe8\x9b\x8b\xe9\xa4\x90",
              "dish_type": "simple_foods",
              "ingredients": [
                {"name": "\xe7\x87\x95\xe9\xba\xa6", "amount_g": 50, "edible": true}
              ],
              "condiments": []
            }
          ]
        },
        {
          "meal_name": "lunch",
          "meal_time": "12:30",
          "dishes": [
            {
              "dish_name": "\xe8\xa5\xbf\xe7\xba\xa2\xe6\x9f\xbf\xe9\xb8\xa1\xe8\x9b\x8b",
              "dish_type": "home_cooked",
              "ingredients": [
                {"name": "\xe7\x95\xaa\xe8\x8c\x84", "amount_g": 200, "edible": true}
              ],
              "condiments": [{"name": "\xe9\xa3\x9f\xe7\x9b\x90", "amount_g": 1.5}]
            }
          ]
        }
      ],
      "extra_items": [
        {"name": "\xe8\x8b\xb9\xe6\x9e\x9c", "amount_g": 180, "meal_name": "snack", "item_type": "fruit"}
      ],
      "record_quality": {
        "has_ingredient_weights": true,
        "has_condiments": true,
        "has_snacks_and_drinks": true,
        "completeness": "complete"
      }
    }"""

    state, error = _recipe_payload_to_session_state(raw_json)

    assert error is None
    assert state["date"] == "2026-05-12"
    assert state["target_user"]["sex"] == "female"
    assert state["ingredient_rows"][0]["meal_name"] == "早餐"
    assert state["ingredient_rows"][0]["dish_type"] == "简单食物"
    assert state["condiment_rows"][0]["meal_name"] == "午餐"
    assert state["extra_item_rows"][0]["meal_name"] == "加餐"
    assert state["extra_item_rows"][0]["item_type"] == "水果"
    assert "search_name" not in state["ingredient_rows"][0]


def test_recipe_payload_to_session_state_rejects_invalid_json_without_state():
    state, error = _recipe_payload_to_session_state("```json\n{}\n```")

    assert state is None
    assert "JSON 解析失败" in error


def test_download_buttons_have_unique_stable_keys_and_plotly_replaces_bar_chart():
    source = Path("streamlit_app.py").read_text(encoding="utf-8")
    keys = re.findall(r"download_button\([\s\S]*?key=\"([^\"]+)\"", source)

    assert keys == ["download_current_input_json", "download_full_result_json"]
    assert len(keys) == len(set(keys))
    assert "st.bar_chart" not in source
    assert "st.plotly_chart" in source
