from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from recipe_quality.demo_input import (
    build_payload_from_demo_tables,
    condiment_rows_from_payload,
    extra_item_rows_from_payload,
    ingredient_rows_from_payload,
    parse_list_text,
    target_user_from_payload,
)
from recipe_quality.pipeline import evaluate_full_pipeline


EXAMPLE_PATH = REPO_ROOT / "examples" / "input_day.json"
ACTIVITY_LEVELS = ["sedentary", "light", "moderate", "active", "very_active"]
SEX_OPTIONS = ["female", "male"]
MEAL_DISPLAY_OPTIONS = ["早餐", "午餐", "晚餐", "加餐"]
PROGRESS_STEPS = {
    "ai_annotation": 15,
    "normalization": 35,
    "nutrition_resolution": 70,
    "scoring": 92,
    "completed": 100,
}
SEX_LABELS = {
    "female": "女性",
    "male": "男性",
}
ACTIVITY_LABELS = {
    "sedentary": "久坐",
    "light": "轻体力活动",
    "moderate": "中等活动",
    "active": "较高活动",
    "very_active": "高强度活动",
}
HABIT_PATTERN_LABELS = {
    "chinese_home_meals": "中式家常饮食",
    "unknown": "不确定",
}
MEAL_LABELS = {
    "breakfast": "早餐",
    "lunch": "午餐",
    "dinner": "晚餐",
    "snack": "加餐",
}
DISH_TYPE_LABELS = {
    "simple_foods": "简单食物",
    "home_cooked": "家常菜",
    "staple": "主食",
    "fruit": "水果",
    "snack": "加餐",
    "other": "其他",
}
ITEM_TYPE_LABELS = {
    "fruit": "水果",
    "snack": "零食/加餐",
    "drink": "饮品",
    "beverage": "饮品",
    "sweets_snacks": "甜食和零食",
    "other": "其他",
}
MODULE_LABELS = {
    "basic_nutrition_quality": "基础营养质量",
    "limiting_components": "限制性成分控制",
    "cooking_processing_safety": "烹调与加工",
    "daily_intake_fit": "全天摄入适配",
    "personalization_feasibility": "个性化与可执行性",
}
FOOD_GROUP_LABELS = {
    "grains_and_tubers": "谷薯类",
    "vegetables": "蔬菜类",
    "fruits": "水果类",
    "livestock_poultry_meat": "畜禽肉类",
    "aquatic_products": "水产类",
    "eggs": "蛋类",
    "dairy": "奶类",
    "soy_products": "大豆及制品",
    "nuts": "坚果类",
    "condiments": "调味品",
    "beverages": "饮品",
    "sweets_snacks": "甜食和零食",
    "other": "其他",
    "unknown": "未知",
}
STATUS_LABELS = {
    "resolved": "已解析",
    "unresolved": "未解析",
    "estimated": "估算",
    "partial": "部分解析",
    "missing_serving": "缺少可换算 serving",
}
COMPONENT_LABELS = {
    "sodium": "钠",
    "cooking_oil": "烹调油",
    "added_sugar": "添加糖",
}
PROCESSING_LABELS = {
    "unprocessed": "未加工",
    "minimally_processed": "少量加工",
    "processed": "加工食品",
    "ultra_processed": "超加工食品",
    "unknown_processing_level": "未知",
}
GRADE_CAP_LABELS = {
    "energy_ratio_severe": "全天能量摄入严重偏离目标",
    "energy_ratio_outside_range": "全天能量摄入明显偏离推荐范围",
    "sodium_above_2x_limit": "钠摄入达到上限的 2 倍以上",
    "sodium_above_3x_limit": "钠摄入达到上限的 3 倍以上",
    "cooking_oil_above_2x_limit": "烹调油达到上限的 2 倍以上",
    "cooking_oil_above_3x_limit": "烹调油达到上限的 3 倍以上",
    "added_sugar_above_2x_limit": "添加糖达到上限的 2 倍以上",
    "added_sugar_above_3x_limit": "添加糖达到上限的 3 倍以上",
    "multiple_limited_components_above_1_5x_limit": "多项限制性成分同时明显超标",
    "saturated_fat_energy_ratio_above_15_percent": "饱和脂肪供能比达到 15% 以上",
    "missing_vegetables_and_fruits": "全天缺少蔬菜和水果",
    "food_group_count_at_most_2": "有效食物组数量过少",
    "edible_weight_outside_range": "可食部总重量明显异常",
    "energy_density_outside_range": "全天食物能量密度明显异常",
    "max_meal_energy_ratio_above_70_percent": "最大单餐能量占比超过 70%",
    "max_meal_energy_ratio_above_80_percent": "最大单餐能量占比超过 80%",
    "snack_energy_ratio_above_50_percent": "零食或加餐能量占比超过 50%",
    "main_meal_energy_ratio_abnormal": "三餐供能比例明显异常",
    "two_main_meals_energy_ratio_above_90_percent": "两餐能量过度集中",
    "insufficient_nutrition_data": "营养数据质量不足",
}


def main() -> None:
    import streamlit as st

    st.set_page_config(page_title="Recipe Quality Demo", layout="wide")
    _init_state(st)

    st.title("Recipe Quality 演示工具")
    st.caption("AI 标注 + FatSecret 营养查询 + 本地规则评分")

    with st.sidebar:
        st.header("目标用户")
        target_user = _target_user_controls(st, st.session_state["target_user"])
        date = st.text_input("日期", value=st.session_state.get("date", ""))
        if st.button("恢复示例输入"):
            _reset_state(st)
            st.rerun()

    should_show_existing_result = bool(st.session_state.get("pipeline_result"))

    input_tab, preview_tab = st.tabs(["表格输入", "JSON 预览"])
    with input_tab:
        ingredient_rows, condiment_rows, extra_rows = _editable_tables(st)

    current_payload = build_payload_from_demo_tables(
        target_user=target_user,
        ingredient_rows=_internalize_ingredient_rows(ingredient_rows),
        condiment_rows=_internalize_condiment_rows(condiment_rows),
        extra_item_rows=_internalize_extra_item_rows(extra_rows),
        date=date,
    )

    with preview_tab:
        st.caption("这里展示的是系统内部 JSON，餐次和活动水平会保留英文代码，便于规则计算。")
        st.json(current_payload)

    left, right = st.columns([1, 1])
    run_clicked = left.button("开始计算", type="primary", use_container_width=True)
    right.download_button(
        "下载当前输入 JSON",
        data=json.dumps(current_payload, ensure_ascii=False, indent=2),
        file_name="input_day.json",
        mime="application/json",
        key="download_current_input_json",
        use_container_width=True,
    )

    if run_clicked:
        _run_pipeline(st, current_payload)
        should_show_existing_result = True

    if should_show_existing_result and st.session_state.get("pipeline_result"):
        _render_result(st, st.session_state["pipeline_result"])


def _init_state(st: Any) -> None:
    if st.session_state.get("demo_initialized"):
        return
    example = _load_example_payload()
    st.session_state["target_user"] = target_user_from_payload(example)
    st.session_state["date"] = example.get("date", "")
    st.session_state["ingredient_rows"] = _display_ingredient_rows(ingredient_rows_from_payload(example))
    st.session_state["condiment_rows"] = _display_condiment_rows(condiment_rows_from_payload(example))
    st.session_state["extra_item_rows"] = _display_extra_item_rows(extra_item_rows_from_payload(example))
    st.session_state["record_quality"] = example.get("record_quality") or {
        "has_ingredient_weights": True,
        "has_condiments": True,
        "has_snacks_and_drinks": True,
        "completeness": "complete",
    }
    st.session_state["demo_initialized"] = True


def _reset_state(st: Any) -> None:
    for key in [
        "demo_initialized",
        "target_user",
        "date",
        "ingredient_rows",
        "condiment_rows",
        "extra_item_rows",
        "record_quality",
        "pipeline_result",
    ]:
        st.session_state.pop(key, None)
    for key in ["ingredient_editor", "condiment_editor", "extra_editor"]:
        st.session_state.pop(key, None)
    _init_state(st)


def _load_example_payload() -> dict[str, Any]:
    return json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))


def _target_user_controls(st: Any, target_user: dict[str, Any]) -> dict[str, Any]:
    sex = _internal_from_label(target_user.get("sex"), SEX_LABELS) or "female"
    activity = _internal_from_label(target_user.get("activity_level"), ACTIVITY_LABELS) or "light"
    habit = _internal_from_label(target_user.get("habit_pattern"), HABIT_PATTERN_LABELS) or "chinese_home_meals"
    habit_options = _options_with_current(["chinese_home_meals", "unknown"], habit)
    return {
        "sex": st.selectbox(
            "性别",
            SEX_OPTIONS,
            index=SEX_OPTIONS.index(sex) if sex in SEX_OPTIONS else 0,
            format_func=_label_sex,
        ),
        "age": st.number_input("年龄", min_value=18, max_value=100, value=int(target_user.get("age") or 30)),
        "height_cm": st.number_input(
            "身高 cm",
            min_value=120.0,
            max_value=220.0,
            value=float(target_user.get("height_cm") or 165),
            step=1.0,
        ),
        "weight_kg": st.number_input(
            "体重 kg",
            min_value=30.0,
            max_value=200.0,
            value=float(target_user.get("weight_kg") or 60),
            step=0.5,
        ),
        "activity_level": st.selectbox(
            "活动水平",
            ACTIVITY_LEVELS,
            index=ACTIVITY_LEVELS.index(activity) if activity in ACTIVITY_LEVELS else 1,
            format_func=_label_activity_level,
        ),
        "liked_foods": parse_list_text(
            st.text_input("喜欢的食物", value=_list_text(target_user.get("liked_foods")))
        ),
        "disliked_foods": parse_list_text(
            st.text_input("不喜欢的食物", value=_list_text(target_user.get("disliked_foods")))
        ),
        "dietary_restrictions": parse_list_text(
            st.text_input("饮食限制", value=_list_text(target_user.get("dietary_restrictions")))
        ),
        "habit_pattern": st.selectbox(
            "饮食习惯模式",
            habit_options,
            index=habit_options.index(habit) if habit in habit_options else 0,
            format_func=_label_habit_pattern,
        ),
    }


def _editable_tables(st: Any) -> tuple[Any, Any, Any]:
    st.subheader("食材")
    ingredient_rows = st.data_editor(
        st.session_state["ingredient_rows"],
        key="ingredient_editor",
        num_rows="dynamic",
        hide_index=True,
        use_container_width=True,
        column_config={
            "meal_name": st.column_config.SelectboxColumn(
                "餐次", options=MEAL_DISPLAY_OPTIONS
            ),
            "meal_time": "时间",
            "dish_name": "菜品",
            "dish_type": "菜品类型",
            "ingredient_name": "食材",
            "amount_g": st.column_config.NumberColumn("重量 g", min_value=0.0, step=10.0),
            "edible": st.column_config.CheckboxColumn("可食"),
        },
    )

    st.subheader("调味品")
    condiment_rows = st.data_editor(
        st.session_state["condiment_rows"],
        key="condiment_editor",
        num_rows="dynamic",
        hide_index=True,
        use_container_width=True,
        column_config={
            "meal_name": st.column_config.SelectboxColumn(
                "餐次", options=MEAL_DISPLAY_OPTIONS
            ),
            "dish_name": "菜品",
            "condiment_name": "调味品",
            "amount_g": st.column_config.NumberColumn("用量 g", min_value=0.0, step=0.5),
        },
    )

    st.subheader("加餐和饮品")
    extra_rows = st.data_editor(
        st.session_state["extra_item_rows"],
        key="extra_editor",
        num_rows="dynamic",
        hide_index=True,
        use_container_width=True,
        column_config={
            "name": "名称",
            "amount_g": st.column_config.NumberColumn("重量 g", min_value=0.0, step=10.0),
            "meal_name": st.column_config.SelectboxColumn(
                "餐次", options=["加餐", "早餐", "午餐", "晚餐"]
            ),
            "meal_time": "时间",
            "item_type": "类型",
        },
    )
    return ingredient_rows, condiment_rows, extra_rows


def _run_pipeline(st: Any, payload: dict[str, Any]) -> None:
    with st.status("正在运行完整流程", expanded=True) as status:
        progress_bar = st.progress(0, text="准备开始")

        def on_progress(step_key: str, message: str) -> None:
            progress_bar.progress(PROGRESS_STEPS.get(step_key, 0), text=message)
            st.write(message)

        try:
            result = evaluate_full_pipeline(payload, progress_callback=on_progress)
        except Exception as exc:  # pragma: no cover - Streamlit displays the exception.
            status.update(label="计算失败", state="error")
            st.exception(exc)
            return

        st.session_state["pipeline_result"] = result
        progress_bar.progress(100, text="完整流程处理完成")
        status.update(label="计算完成", state="complete")


def _render_result(st: Any, result: dict[str, Any]) -> None:
    st.divider()
    st.header("评分结果")
    score_col, final_col, raw_col = st.columns(3)
    score_col.metric("总分", _format_number(result.get("total_score")))
    final_col.metric("最终等级", result.get("final_grade", "-"))
    raw_col.metric("原始等级", result.get("raw_grade", "-"))

    module_scores = result.get("module_scores") or {}
    nutrition_totals = result.get("daily_totals") or {}
    food_groups = nutrition_totals.get("food_group_amounts_g") or {}

    chart_col, food_col = st.columns(2)
    with chart_col:
        st.subheader("模块分")
        module_rows = _module_score_rows(module_scores)
        st.bar_chart(module_rows, x="模块", y="得分")
    with food_col:
        st.subheader("食物组重量")
        food_group_rows = _food_group_rows(food_groups)
        st.bar_chart(food_group_rows, x="食物组", y="重量 g")

    st.subheader("全天营养汇总")
    st.dataframe(_nutrition_rows(nutrition_totals), hide_index=True, use_container_width=True)

    st.subheader("食材匹配")
    st.dataframe(_resolved_item_rows(result.get("resolved_items") or []), hide_index=True, use_container_width=True)

    caps = result.get("grade_caps") or []
    st.subheader("等级封顶")
    if caps:
        for message in _grade_cap_messages(caps):
            st.warning(message)
        with st.expander("封顶规则详情"):
            st.dataframe(caps, hide_index=True, use_container_width=True)
    else:
        st.success("本次结果未触发等级封顶规则。")

    warnings = result.get("ai_warnings") or []
    with st.expander("AI 标注提示"):
        if warnings:
            for warning in warnings:
                st.write(warning)
        else:
            st.write("无 AI 标注提示。")

    with st.expander("完整结果 JSON"):
        st.json(result)
        st.download_button(
            "下载结果 JSON",
            data=json.dumps(result, ensure_ascii=False, indent=2),
            file_name="full_result.json",
            mime="application/json",
            key="download_full_result_json",
        )


def _nutrition_rows(daily_totals: dict[str, Any]) -> list[dict[str, Any]]:
    labels = {
        "energy_kcal": "能量 kcal",
        "protein_g": "蛋白质 g",
        "fat_g": "脂肪 g",
        "saturated_fat_g": "饱和脂肪 g",
        "carbohydrate_g": "碳水化合物 g",
        "fiber_g": "膳食纤维 g",
        "sodium_mg": "钠 mg",
        "cooking_oil_g": "烹调油 g",
        "added_sugar_g": "添加糖 g",
        "food_group_count": "有效食物组数",
    }
    return [
        {"指标": label, "数值": _format_number(daily_totals.get(key))}
        for key, label in labels.items()
    ]


def _display_ingredient_rows(rows: Any) -> list[dict[str, Any]]:
    output = []
    for row in _as_records(rows):
        output.append(
            {
                **row,
                "meal_name": _label_meal_name(row.get("meal_name")),
                "dish_type": _label_dish_type(row.get("dish_type")),
            }
        )
    return output


def _display_condiment_rows(rows: Any) -> list[dict[str, Any]]:
    output = []
    for row in _as_records(rows):
        output.append({**row, "meal_name": _label_meal_name(row.get("meal_name"))})
    return output


def _display_extra_item_rows(rows: Any) -> list[dict[str, Any]]:
    output = []
    for row in _as_records(rows):
        output.append(
            {
                **row,
                "meal_name": _label_meal_name(row.get("meal_name")),
                "item_type": _label_item_type(row.get("item_type")),
            }
        )
    return output


def _internalize_ingredient_rows(rows: Any) -> list[dict[str, Any]]:
    output = []
    for row in _as_records(rows):
        output.append(
            {
                **row,
                "meal_name": _internal_meal_name(row.get("meal_name")),
                "dish_type": _internal_dish_type(row.get("dish_type")),
            }
        )
    return output


def _internalize_condiment_rows(rows: Any) -> list[dict[str, Any]]:
    output = []
    for row in _as_records(rows):
        output.append({**row, "meal_name": _internal_meal_name(row.get("meal_name"))})
    return output


def _internalize_extra_item_rows(rows: Any) -> list[dict[str, Any]]:
    output = []
    for row in _as_records(rows):
        output.append(
            {
                **row,
                "meal_name": _internal_meal_name(row.get("meal_name")),
                "item_type": _internal_item_type(row.get("item_type")),
            }
        )
    return output


def _module_score_rows(module_scores: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"模块": _label_module_key(key), "得分": _to_chart_number(value)}
        for key, value in module_scores.items()
    ]


def _food_group_rows(food_groups: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [
        {"食物组": _label_food_group(key), "重量 g": _to_chart_number(value)}
        for key, value in food_groups.items()
    ]
    return sorted(rows, key=lambda row: row["重量 g"], reverse=True)


def _resolved_item_rows(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "食材": item.get("name") or "",
            "英文检索名（供系统查询）": item.get("search_name") or "",
            "食物组": _label_food_group(item.get("food_group")),
            "加工程度": _label_processing_level(item.get("processing_level")),
            "FatSecret 匹配词条": item.get("fatsecret_food_name") or "",
            "份量标准": item.get("serving_used") or "",
            "状态": _label_status(item.get("status")),
            "错误": item.get("error") or "",
        }
        for item in items
    ]


def _grade_cap_messages(caps: list[dict[str, Any]]) -> list[str]:
    return [_grade_cap_message(cap) for cap in caps]


def _grade_cap_message(cap: dict[str, Any]) -> str:
    trigger = str(cap.get("trigger") or "")
    cap_grade = cap.get("cap_grade") or "-"
    value = cap.get("value")
    if trigger in {"energy_ratio_outside_range", "energy_ratio_severe"}:
        return (
            f"本次最终等级被限制为 {cap_grade}，原因是全天能量摄入约为目标的 "
            f"{_format_ratio_percent(value)}，{GRADE_CAP_LABELS.get(trigger, trigger)}。"
        )
    if trigger in {
        "saturated_fat_energy_ratio_above_15_percent",
        "max_meal_energy_ratio_above_70_percent",
        "max_meal_energy_ratio_above_80_percent",
        "snack_energy_ratio_above_50_percent",
    }:
        return (
            f"本次最终等级被限制为 {cap_grade}，原因是"
            f"{GRADE_CAP_LABELS.get(trigger, trigger)}，当前约为 {_format_ratio_percent(value)}。"
        )
    if trigger in {
        "main_meal_energy_ratio_abnormal",
        "two_main_meals_energy_ratio_above_90_percent",
    }:
        return (
            f"本次最终等级被限制为 {cap_grade}，原因是"
            f"{GRADE_CAP_LABELS.get(trigger, trigger)}：{_format_meal_ratio_summary(value)}。"
        )
    label = GRADE_CAP_LABELS.get(trigger, trigger or "未知封顶规则")
    formatted_value = _format_cap_value(value)
    if formatted_value:
        return f"本次最终等级被限制为 {cap_grade}，原因是{label}，当前值为 {formatted_value}。"
    return f"本次最终等级被限制为 {cap_grade}，原因是{label}。"


def _label_module_key(key: Any) -> str:
    text = str(key or "")
    return MODULE_LABELS.get(text, text)


def _label_sex(value: Any) -> str:
    text = str(value or "")
    return SEX_LABELS.get(text, text)


def _label_activity_level(value: Any) -> str:
    text = str(value or "")
    return ACTIVITY_LABELS.get(text, text)


def _label_habit_pattern(value: Any) -> str:
    text = str(value or "")
    return HABIT_PATTERN_LABELS.get(text, text)


def _label_meal_name(value: Any) -> str:
    text = str(value or "")
    return MEAL_LABELS.get(text, text)


def _label_dish_type(value: Any) -> str:
    text = str(value or "")
    return DISH_TYPE_LABELS.get(text, text)


def _label_item_type(value: Any) -> str:
    text = str(value or "")
    return ITEM_TYPE_LABELS.get(text, text)


def _label_food_group(key: Any) -> str:
    text = str(key or "")
    return FOOD_GROUP_LABELS.get(text, text)


def _label_status(value: Any) -> str:
    text = str(value or "")
    return STATUS_LABELS.get(text, text)


def _label_processing_level(value: Any) -> str:
    text = str(value or "")
    return PROCESSING_LABELS.get(text, text)


def _list_text(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value or "")


def _as_records(table: Any) -> list[dict[str, Any]]:
    if table is None:
        return []
    if hasattr(table, "to_dict"):
        return table.to_dict("records")
    return [dict(row) for row in table]


def _internal_meal_name(value: Any) -> str:
    return _internal_from_label(value, MEAL_LABELS)


def _internal_dish_type(value: Any) -> str:
    return _internal_from_label(value, DISH_TYPE_LABELS)


def _internal_item_type(value: Any) -> str:
    return _internal_from_label(value, ITEM_TYPE_LABELS)


def _internal_from_label(value: Any, labels: dict[str, str]) -> str:
    text = str(value or "").strip()
    reverse = {label: key for key, label in labels.items()}
    return reverse.get(text, text)


def _options_with_current(options: list[str], current: str) -> list[str]:
    if current and current not in options:
        return [*options, current]
    return options


def _format_number(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"{value:.2f}"
    return "-"


def _to_chart_number(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return 0.0


def _format_ratio_percent(value: Any) -> str:
    try:
        return f"{float(value) * 100:.0f}%"
    except (TypeError, ValueError):
        return "未知比例"


def _format_cap_value(value: Any) -> str:
    if isinstance(value, dict):
        return ", ".join(
            f"{_label_display_key(key)}: {_format_cap_value(item)}"
            for key, item in value.items()
        )
    if isinstance(value, list):
        return ", ".join(_label_display_key(item) for item in value)
    if isinstance(value, (int, float)):
        return f"{value:.2f}"
    return str(value or "")


def _label_display_key(value: Any) -> str:
    text = str(value or "")
    for labels in (FOOD_GROUP_LABELS, MEAL_LABELS, COMPONENT_LABELS):
        if text in labels:
            return labels[text]
    return text


def _format_meal_ratio_summary(value: Any) -> str:
    if not isinstance(value, dict):
        return _format_cap_value(value)
    labels = {"breakfast": "早餐", "lunch": "午餐", "dinner": "晚餐", "snack": "加餐"}
    return ", ".join(
        f"{labels.get(str(meal), str(meal))} {_format_ratio_percent(ratio)}"
        for meal, ratio in value.items()
    )


if __name__ == "__main__":
    main()
