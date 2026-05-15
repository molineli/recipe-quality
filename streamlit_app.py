from __future__ import annotations

import html
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
from recipe_quality.targets import resolve_basic_nutrition_targets, resolve_daily_targets


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
    _inject_dashboard_css(st)
    _init_state(st)

    _render_header(st)

    with st.sidebar:
        st.header("目标用户")
        target_user = _target_user_controls(st, st.session_state["target_user"])
        date = st.text_input("日期", value=st.session_state.get("date", ""))
        if st.button("恢复示例输入"):
            _reset_state(st)
            st.rerun()

    should_show_existing_result = bool(st.session_state.get("pipeline_result"))

    input_tab, overview_tab, detail_tab, raw_tab = st.tabs(
        ["输入配置", "评分总览", "详细分析", "原始数据"]
    )
    with input_tab:
        _render_json_importer(st)
        ingredient_rows, condiment_rows, extra_rows = _editable_tables(st)

    current_payload = build_payload_from_demo_tables(
        target_user=target_user,
        ingredient_rows=_internalize_ingredient_rows(ingredient_rows),
        condiment_rows=_internalize_condiment_rows(condiment_rows),
        extra_item_rows=_internalize_extra_item_rows(extra_rows),
        date=date,
    )

    with input_tab:
        left, right = st.columns([1, 1])
        run_clicked = left.button("开始计算", type="primary", width="stretch")
        right.download_button(
            "下载当前输入 JSON",
            data=json.dumps(current_payload, ensure_ascii=False, indent=2),
            file_name="input_day.json",
            mime="application/json",
            key="download_current_input_json",
            width="stretch",
        )

    if run_clicked:
        _run_pipeline(st, current_payload)
        should_show_existing_result = True

    result = st.session_state.get("pipeline_result") if should_show_existing_result else None
    with overview_tab:
        _render_score_overview(st, result)
    with detail_tab:
        _render_detail_analysis(st, result, current_payload)
    with raw_tab:
        _render_raw_data(st, current_payload, result)


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


def _render_json_importer(st: Any) -> None:
    with st.expander("导入 AI 生成的食谱 JSON"):
        st.caption("请上传纯 JSON 文件。Markdown 代码块或说明文字不会被解析。")
        uploaded_file = st.file_uploader(
            "选择 JSON 文件",
            type=["json"],
            key="import_recipe_json_file",
        )
        if st.button("加载 JSON 到表格", key="load_recipe_json_to_tables"):
            if uploaded_file is None:
                st.error("请先选择一个 .json 文件。")
                return
            state, error = _recipe_payload_to_session_state(uploaded_file.getvalue())
            if error:
                st.error(error)
                return
            _apply_imported_recipe_state(st, state)
            st.success("JSON 已加载到表格。请检查后点击“开始计算”。")
            st.rerun()


def _recipe_payload_to_session_state(raw_data: bytes | str) -> tuple[dict[str, Any] | None, str | None]:
    try:
        text = raw_data.decode("utf-8") if isinstance(raw_data, bytes) else str(raw_data)
        payload = json.loads(text)
    except UnicodeDecodeError:
        return None, "JSON 文件必须使用 UTF-8 编码。"
    except json.JSONDecodeError as exc:
        return None, f"JSON 解析失败：{exc.msg}。请确认文件只包含纯 JSON。"
    if not isinstance(payload, dict):
        return None, "JSON 顶层必须是对象。"
    if not isinstance(payload.get("meals"), list):
        return None, "JSON 必须包含 meals 数组。"

    return {
        "target_user": target_user_from_payload(payload),
        "date": payload.get("date", ""),
        "ingredient_rows": _display_ingredient_rows(ingredient_rows_from_payload(payload)),
        "condiment_rows": _display_condiment_rows(condiment_rows_from_payload(payload)),
        "extra_item_rows": _display_extra_item_rows(extra_item_rows_from_payload(payload)),
        "record_quality": payload.get("record_quality") or {
            "has_ingredient_weights": True,
            "has_condiments": bool(condiment_rows_from_payload(payload)),
            "has_snacks_and_drinks": bool(extra_item_rows_from_payload(payload)),
            "completeness": "complete",
        },
    }, None


def _apply_imported_recipe_state(st: Any, state: dict[str, Any] | None) -> None:
    if state is None:
        return
    for key, value in state.items():
        st.session_state[key] = value
    st.session_state.pop("pipeline_result", None)
    for key in ["ingredient_editor", "condiment_editor", "extra_editor"]:
        st.session_state.pop(key, None)


def _inject_dashboard_css(st: Any) -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background: linear-gradient(180deg, #f6f8fb 0%, #eef3f8 100%);
        }
        .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
            max-width: 1280px;
        }
        .rq-hero {
            background: #ffffff;
            border: 1px solid #e4e9f1;
            border-radius: 18px;
            padding: 24px 28px;
            box-shadow: 0 16px 40px rgba(31, 41, 55, 0.08);
            margin-bottom: 18px;
        }
        .rq-hero-eyebrow {
            color: #2563eb;
            font-size: 0.86rem;
            font-weight: 700;
            letter-spacing: 0.04em;
            margin-bottom: 6px;
        }
        .rq-hero-title {
            color: #111827;
            font-size: 2.1rem;
            font-weight: 800;
            line-height: 1.15;
            margin: 0;
        }
        .rq-hero-subtitle {
            color: #64748b;
            font-size: 1rem;
            margin-top: 8px;
        }
        .rq-card {
            background: #ffffff;
            border: 1px solid #e4e9f1;
            border-radius: 16px;
            padding: 18px 20px;
            box-shadow: 0 12px 30px rgba(15, 23, 42, 0.06);
            min-height: 126px;
        }
        .rq-card-label {
            color: #64748b;
            font-size: 0.9rem;
            font-weight: 700;
            margin-bottom: 10px;
        }
        .rq-card-value {
            color: #0f172a;
            font-size: 2.2rem;
            font-weight: 800;
            line-height: 1;
        }
        .rq-card-factor {
            color: #0f172a;
            font-size: 1.2rem;
            font-weight: 800;
            line-height: 1.35;
        }
        .rq-card-detail {
            color: #64748b;
            font-size: 0.9rem;
            margin-top: 10px;
        }
        .rq-score-card {
            border-top: 5px solid #2563eb;
        }
        .rq-grade-badge {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-width: 56px;
            height: 56px;
            padding: 0 18px;
            border-radius: 999px;
            color: #ffffff;
            font-size: 1.8rem;
            font-weight: 900;
            box-shadow: inset 0 -2px 0 rgba(0,0,0,0.12);
        }
        .rq-grade-a { background: #16a34a; }
        .rq-grade-b { background: #0891b2; }
        .rq-grade-c { background: #f59e0b; }
        .rq-grade-d { background: #ea580c; }
        .rq-grade-e { background: #dc2626; }
        .rq-warning-card {
            background: #fff7d6;
            border: 1px solid #f8d85e;
            border-left: 6px solid #f59e0b;
            border-radius: 16px;
            padding: 16px 18px;
            color: #713f12;
            font-weight: 650;
            margin: 14px 0 18px 0;
            box-shadow: 0 10px 28px rgba(245, 158, 11, 0.12);
        }
        .rq-success-card {
            background: #eafaf0;
            border: 1px solid #bbf7d0;
            border-left: 6px solid #16a34a;
            border-radius: 16px;
            padding: 16px 18px;
            color: #14532d;
            font-weight: 650;
            margin: 14px 0 18px 0;
        }
        .rq-muted {
            color: #64748b;
            font-size: 0.92rem;
        }
        .rq-empty-state {
            background: #ffffff;
            border: 1px dashed #cbd5e1;
            border-radius: 16px;
            padding: 32px;
            color: #64748b;
            text-align: center;
        }
        .rq-nutrition-card {
            background: #ffffff;
            border: 1px solid #e4e9f1;
            border-radius: 16px;
            padding: 16px 18px;
            box-shadow: 0 10px 26px rgba(15, 23, 42, 0.06);
            min-height: 150px;
        }
        .rq-nutrition-label {
            color: #64748b;
            font-size: 0.86rem;
            font-weight: 700;
            margin-bottom: 8px;
        }
        .rq-nutrition-value {
            color: #0f172a;
            font-size: 1.75rem;
            font-weight: 850;
            line-height: 1.1;
            margin-bottom: 10px;
        }
        .rq-status {
            display: inline-flex;
            border-radius: 999px;
            padding: 3px 10px;
            font-size: 0.78rem;
            font-weight: 800;
            margin-bottom: 10px;
        }
        .rq-status-good { background: #dcfce7; color: #166534; }
        .rq-status-low { background: #dbeafe; color: #1d4ed8; }
        .rq-status-high { background: #ffedd5; color: #c2410c; }
        .rq-status-risk { background: #fee2e2; color: #b91c1c; }
        .rq-nutrition-note {
            color: #64748b;
            font-size: 0.86rem;
            line-height: 1.45;
        }
        .rq-progress-card {
            background: #ffffff;
            border: 1px solid #e4e9f1;
            border-radius: 14px;
            padding: 13px 15px;
            margin-bottom: 10px;
            box-shadow: 0 8px 18px rgba(15, 23, 42, 0.045);
        }
        .rq-progress-header {
            display: flex;
            justify-content: space-between;
            gap: 12px;
            align-items: baseline;
            margin-bottom: 8px;
        }
        .rq-progress-name {
            color: #0f172a;
            font-weight: 800;
        }
        .rq-progress-meta {
            color: #64748b;
            font-size: 0.86rem;
        }
        .rq-progress-track {
            width: 100%;
            height: 10px;
            background: #e5e7eb;
            border-radius: 999px;
            overflow: hidden;
        }
        .rq-progress-fill {
            height: 10px;
            border-radius: 999px;
        }
        .rq-progress-good { background: #16a34a; }
        .rq-progress-low { background: #2563eb; }
        .rq-progress-high { background: #f59e0b; }
        .rq-progress-risk { background: #dc2626; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_header(st: Any) -> None:
    st.markdown(
        """
        <div class="rq-hero">
            <div class="rq-hero-eyebrow">RECIPE QUALITY DASHBOARD</div>
            <h1 class="rq-hero-title">食谱质量评分演示工具</h1>
            <div class="rq-hero-subtitle">AI 标注、FatSecret 营养查询与本地规则评分的一体化演示面板</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


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
        width="stretch",
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
        width="stretch",
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
        width="stretch",
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
        except RuntimeError as exc:
            status.update(label="计算失败", state="error")
            st.error(f"计算过程中遇到外部服务请求问题：{exc}")
            st.info("请稍后重试；如果只有部分食材查询失败，系统会保留可解析食材并在明细中标记未解析项。")
            return
        except Exception as exc:  # pragma: no cover - Streamlit displays the exception.
            status.update(label="计算失败", state="error")
            st.exception(exc)
            return

        st.session_state["pipeline_result"] = result
        progress_bar.progress(100, text="完整流程处理完成")
        status.update(label="计算完成", state="complete")


def _render_result(st: Any, result: dict[str, Any]) -> None:
    _render_score_overview(st, result)
    _render_detail_analysis(st, result)


def _render_score_overview(st: Any, result: dict[str, Any] | None) -> None:
    st.subheader("评分总览")
    if not result:
        _render_empty_state(st, "请先在“输入配置”中点击开始计算，完成后这里会展示综合评分和等级信息。")
        return

    caps = result.get("grade_caps") or []
    score_col, final_col, raw_col, factor_col = st.columns([1.1, 1, 1, 1.5])
    final_grade = str(result.get("final_grade") or "-")
    raw_grade = str(result.get("raw_grade") or "-")
    primary_factor = _primary_limiting_factor(caps)

    with score_col:
        _metric_card(st, "综合评分", _format_number(result.get("total_score")), "100 分制综合饮食质量评分", "rq-score-card")
    with final_col:
        _grade_card(st, "最终等级", final_grade, "应用封顶规则后的等级")
    with raw_col:
        _grade_card(st, "原始等级", raw_grade, "仅按总分换算的等级")
    with factor_col:
        _factor_card(st, primary_factor, "优先显示最影响最终等级的因素")

    if caps:
        for message in _grade_cap_messages(caps):
            _warning_card(st, message)
    else:
        st.markdown(
            '<div class="rq-success-card">本次结果未触发等级封顶规则。</div>',
            unsafe_allow_html=True,
        )


def _render_detail_analysis(
    st: Any,
    result: dict[str, Any] | None,
    current_payload: dict[str, Any] | None = None,
) -> None:
    st.subheader("详细分析")
    if not result:
        _render_empty_state(st, "完成计算后，这里会显示模块得分、食物组分布、营养汇总和食材匹配。")
        return
    module_scores = result.get("module_scores") or {}
    nutrition_totals = result.get("daily_totals") or {}
    food_groups = nutrition_totals.get("food_group_amounts_g") or {}

    chart_col, food_col, meal_col = st.columns(3)
    with chart_col:
        st.subheader("模块分")
        module_rows = _module_score_rows(module_scores)
        _plotly_bar_chart(st, module_rows, label_key="模块", value_key="得分", color="#2563eb")
    with food_col:
        st.subheader("食物组重量")
        food_group_rows = _food_group_rows(food_groups)
        _plotly_bar_chart(st, food_group_rows, label_key="食物组", value_key="重量 g", color="#16a34a")
    with meal_col:
        st.subheader("三餐能量占比")
        meal_energy_rows = _meal_energy_rows(nutrition_totals.get("ingredient_records") or [])
        _plotly_pie_chart(st, meal_energy_rows, label_key="餐次", value_key="能量 kcal")

    _render_nutrition_summary(st, nutrition_totals, (current_payload or {}).get("target_user"))

    st.subheader("食材匹配")
    st.dataframe(_resolved_item_rows(result.get("resolved_items") or []), hide_index=True, width="stretch")

    caps = result.get("grade_caps") or []
    st.subheader("等级封顶")
    if caps:
        for message in _grade_cap_messages(caps):
            _warning_card(st, message)
        with st.expander("封顶规则详情"):
            st.dataframe(caps, hide_index=True, width="stretch")
    else:
        st.markdown(
            '<div class="rq-success-card">本次结果未触发等级封顶规则。</div>',
            unsafe_allow_html=True,
        )

    warnings = result.get("ai_warnings") or []
    with st.expander("AI 标注提示"):
        if warnings:
            for warning in warnings:
                st.write(warning)
        else:
            st.write("无 AI 标注提示。")


def _render_raw_data(st: Any, current_payload: dict[str, Any], result: dict[str, Any] | None) -> None:
    st.subheader("原始数据")
    st.caption("这里展示的是系统内部 JSON，餐次和活动水平会保留英文代码，便于规则计算。")
    st.json(current_payload)
    if result:
        with st.expander("完整结果 JSON"):
            st.json(result)
            st.download_button(
                "下载结果 JSON",
                data=json.dumps(result, ensure_ascii=False, indent=2),
                file_name="full_result.json",
                mime="application/json",
                key="download_full_result_json",
            )


def _metric_card(st: Any, label: str, value: str, detail: str, extra_class: str = "") -> None:
    st.markdown(
        f"""
        <div class="rq-card {extra_class}">
            <div class="rq-card-label">{_html_escape(label)}</div>
            <div class="rq-card-value">{_html_escape(value)}</div>
            <div class="rq-card-detail">{_html_escape(detail)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _grade_card(st: Any, label: str, grade: str, detail: str) -> None:
    st.markdown(
        f"""
        <div class="rq-card">
            <div class="rq-card-label">{_html_escape(label)}</div>
            <span class="rq-grade-badge {_grade_badge_class(grade)}">{_html_escape(grade)}</span>
            <div class="rq-card-detail">{_html_escape(detail)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _factor_card(st: Any, value: str, detail: str) -> None:
    st.markdown(
        f"""
        <div class="rq-card">
            <div class="rq-card-label">主要限制因素</div>
            <div class="rq-card-factor">{_html_escape(value)}</div>
            <div class="rq-card-detail">{_html_escape(detail)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _warning_card(st: Any, message: str) -> None:
    st.markdown(
        f'<div class="rq-warning-card">{_html_escape(message)}</div>',
        unsafe_allow_html=True,
    )


def _render_empty_state(st: Any, message: str) -> None:
    st.markdown(
        f'<div class="rq-empty-state">{_html_escape(message)}</div>',
        unsafe_allow_html=True,
    )


def _plotly_bar_chart(
    st: Any,
    rows: list[dict[str, Any]],
    *,
    label_key: str,
    value_key: str,
    color: str,
) -> None:
    if not rows:
        _render_empty_state(st, "暂无可展示的数据。")
        return
    try:
        import plotly.graph_objects as go
    except ModuleNotFoundError:
        st.error("缺少 Plotly 依赖，请运行：python -m pip install -e \".[demo]\"")
        return
    figure = go.Figure(
        data=[
            go.Bar(
                x=[row[value_key] for row in rows],
                y=[row[label_key] for row in rows],
                orientation="h",
                marker={"color": color, "line": {"color": "rgba(15,23,42,0.12)", "width": 1}},
                text=[row[value_key] for row in rows],
                textposition="auto",
                hovertemplate="%{y}<br>%{x}<extra></extra>",
            )
        ]
    )
    figure.update_layout(
        height=330,
        margin={"l": 16, "r": 16, "t": 18, "b": 24},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "Microsoft YaHei, Arial, sans-serif", "color": "#334155"},
        xaxis={"showgrid": True, "gridcolor": "#e5e7eb", "zeroline": False},
        yaxis={"autorange": "reversed", "showgrid": False},
    )
    st.plotly_chart(figure, width="stretch", config={"displayModeBar": False})


def _plotly_pie_chart(
    st: Any,
    rows: list[dict[str, Any]],
    *,
    label_key: str,
    value_key: str,
) -> None:
    if not rows:
        _render_empty_state(st, "暂无可展示的数据。")
        return
    try:
        import plotly.graph_objects as go
    except ModuleNotFoundError:
        st.error("缺少 Plotly 依赖，请运行：python -m pip install -e \".[demo]\"")
        return
    figure = go.Figure(
        data=[
            go.Pie(
                labels=[row[label_key] for row in rows],
                values=[row[value_key] for row in rows],
                hole=0.36,
                marker={
                    "colors": ["#2563eb", "#16a34a", "#f59e0b"],
                    "line": {"color": "#ffffff", "width": 2},
                },
                textinfo="label+percent",
                hovertemplate="%{label}<br>%{value:.2f} kcal<br>%{percent}<extra></extra>",
            )
        ]
    )
    figure.update_layout(
        height=330,
        margin={"l": 16, "r": 16, "t": 18, "b": 24},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "Microsoft YaHei, Arial, sans-serif", "color": "#334155"},
        showlegend=False,
    )
    st.plotly_chart(figure, width="stretch", config={"displayModeBar": False})


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


def _render_nutrition_summary(
    st: Any,
    daily_totals: dict[str, Any],
    target_user: dict[str, Any] | None = None,
) -> None:
    st.subheader("全天营养汇总")
    targets = _nutrition_display_targets(target_user)
    core_rows = _core_nutrition_cards(daily_totals, targets)
    columns = st.columns(4)
    for column, row in zip(columns, core_rows):
        with column:
            _nutrition_card(st, row)

    st.markdown('<div class="rq-muted">关键指标进度</div>', unsafe_allow_html=True)
    for row in _nutrition_progress_rows(daily_totals, targets):
        _nutrition_progress_bar(st, row)

    with st.expander("查看完整营养明细"):
        st.dataframe(_nutrition_rows(daily_totals), hide_index=True, width="stretch")


def _nutrition_card(st: Any, row: dict[str, Any]) -> None:
    st.markdown(
        f"""
        <div class="rq-nutrition-card">
            <div class="rq-nutrition-label">{_html_escape(row["label"])}</div>
            <div class="rq-nutrition-value">{_html_escape(row["value_text"])}</div>
            <div class="rq-status rq-status-{_html_escape(row["status_class"])}">{_html_escape(row["status"])}</div>
            <div class="rq-nutrition-note">{_html_escape(row["note"])}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _nutrition_progress_bar(st: Any, row: dict[str, Any]) -> None:
    width = max(0.0, min(float(row["percent"]), 100.0))
    st.markdown(
        f"""
        <div class="rq-progress-card">
            <div class="rq-progress-header">
                <span class="rq-progress-name">{_html_escape(row["label"])}</span>
                <span class="rq-progress-meta">{_html_escape(row["actual_text"])} / {_html_escape(row["target_text"])} · {_html_escape(row["percent_text"])}</span>
            </div>
            <div class="rq-progress-track">
                <div class="rq-progress-fill rq-progress-{_html_escape(row["status_class"])}" style="width: {width:.1f}%"></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _nutrition_display_targets(target_user: dict[str, Any] | None = None) -> dict[str, float]:
    resolved_targets = resolve_daily_targets(target_user)
    basic_targets = resolve_basic_nutrition_targets(resolved_targets, target_user)
    energy = float(resolved_targets.get("energy_kcal") or 2000.0)
    return {
        "energy_kcal": energy,
        "protein_g": float(basic_targets.get("protein_g") or energy * 0.15 / 4),
        "fiber_g": float(basic_targets.get("fiber_g") or 25.0),
        "sodium_mg": float(resolved_targets.get("sodium_mg_limit") or 2000.0),
        "added_sugar_g": float(resolved_targets.get("added_sugar_g_limit") or 25.0),
    }


def _core_nutrition_cards(
    daily_totals: dict[str, Any],
    targets: dict[str, float],
) -> list[dict[str, Any]]:
    energy = _to_float(daily_totals.get("energy_kcal"))
    protein = _to_float(daily_totals.get("protein_g"))
    fat = _to_float(daily_totals.get("fat_g"))
    carbohydrate = _to_float(daily_totals.get("carbohydrate_g"))
    return [
        _core_nutrition_card(
            label="能量",
            value=energy,
            unit="kcal",
            status=_ratio_status(energy, targets["energy_kcal"], low=0.8, good_low=0.9, good_high=1.1, high=1.2),
            note=f"目标约 {_format_target(targets['energy_kcal'], 'kcal')}，用于判断全天摄入是否匹配。",
        ),
        _core_nutrition_card(
            label="蛋白质",
            value=protein,
            unit="g",
            status=_ratio_status(protein, targets["protein_g"], low=0.8, good_low=0.9, good_high=1.5, high=2.0),
            note=f"目标约 {_format_target(targets['protein_g'], 'g')}，关注是否满足基础需要。",
        ),
        _core_nutrition_card(
            label="脂肪",
            value=fat,
            unit="g",
            status=_macro_ratio_status(fat, energy, kcal_per_g=9, low=0.15, good_low=0.20, good_high=0.30, high=0.35),
            note="参考脂肪供能比 20%–30%，用于判断结构是否均衡。",
        ),
        _core_nutrition_card(
            label="碳水化合物",
            value=carbohydrate,
            unit="g",
            status=_macro_ratio_status(carbohydrate, energy, kcal_per_g=4, low=0.40, good_low=0.50, good_high=0.65, high=0.75),
            note="参考碳水供能比 50%–65%，用于判断主食和整体能量结构。",
        ),
    ]


def _core_nutrition_card(
    *,
    label: str,
    value: float,
    unit: str,
    status: tuple[str, str],
    note: str,
) -> dict[str, Any]:
    return {
        "label": label,
        "value": value,
        "unit": unit,
        "value_text": _format_nutrition_value(value, unit),
        "status": status[0],
        "status_class": status[1],
        "note": note,
    }


def _nutrition_progress_rows(
    daily_totals: dict[str, Any],
    targets: dict[str, float],
) -> list[dict[str, Any]]:
    specs = [
        ("能量", "energy_kcal", "kcal", targets["energy_kcal"], "target"),
        ("蛋白质", "protein_g", "g", targets["protein_g"], "target"),
        ("膳食纤维", "fiber_g", "g", targets["fiber_g"], "minimum"),
        ("钠", "sodium_mg", "mg", targets["sodium_mg"], "limit"),
        ("添加糖", "added_sugar_g", "g", targets["added_sugar_g"], "limit"),
    ]
    return [
        _nutrition_progress_row(
            label=label,
            actual=_to_float(daily_totals.get(key)),
            target=target,
            unit=unit,
            mode=mode,
        )
        for label, key, unit, target, mode in specs
    ]


def _nutrition_progress_row(
    *,
    label: str,
    actual: float,
    target: float,
    unit: str,
    mode: str,
) -> dict[str, Any]:
    percent = actual / target * 100 if target else 0.0
    status = _progress_status(percent, mode)
    return {
        "label": label,
        "actual": actual,
        "target": target,
        "percent": round(percent, 1),
        "percent_text": f"{percent:.0f}%",
        "actual_text": _format_nutrition_value(actual, unit),
        "target_text": _format_target(target, unit),
        "status": status[0],
        "status_class": status[1],
    }


def _ratio_status(
    actual: float,
    target: float,
    *,
    low: float,
    good_low: float,
    good_high: float,
    high: float,
) -> tuple[str, str]:
    if target <= 0:
        return "良好", "good"
    ratio = actual / target
    if ratio < low:
        return "风险", "risk"
    if ratio < good_low:
        return "偏低", "low"
    if ratio <= good_high:
        return "良好", "good"
    if ratio <= high:
        return "偏高", "high"
    return "风险", "risk"


def _macro_ratio_status(
    grams: float,
    energy_kcal: float,
    *,
    kcal_per_g: float,
    low: float,
    good_low: float,
    good_high: float,
    high: float,
) -> tuple[str, str]:
    if energy_kcal <= 0:
        return "风险", "risk"
    ratio = grams * kcal_per_g / energy_kcal
    if ratio < low:
        return "风险", "risk"
    if ratio < good_low:
        return "偏低", "low"
    if ratio <= good_high:
        return "良好", "good"
    if ratio <= high:
        return "偏高", "high"
    return "风险", "risk"


def _progress_status(percent: float, mode: str) -> tuple[str, str]:
    if mode == "limit":
        if percent <= 100:
            return "良好", "good"
        if percent <= 130:
            return "偏高", "high"
        return "风险", "risk"
    if mode == "minimum":
        if percent >= 100:
            return "良好", "good"
        if percent >= 80:
            return "偏低", "low"
        return "风险", "risk"
    if 90 <= percent <= 110:
        return "良好", "good"
    if 80 <= percent < 90:
        return "偏低", "low"
    if 110 < percent <= 120:
        return "偏高", "high"
    return "风险", "risk"


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


def _meal_energy_rows(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    meal_order = ("breakfast", "lunch", "dinner")
    meal_energy = {meal: 0.0 for meal in meal_order}
    for item in items:
        meal_name = str(item.get("meal_name") or "")
        if meal_name not in meal_energy:
            continue
        energy = _item_energy_kcal(item)
        if energy is None or energy <= 0:
            continue
        meal_energy[meal_name] += energy
    rows = []
    for meal in meal_order:
        energy = meal_energy[meal]
        if energy > 0:
            rows.append({"餐次": _label_meal_name(meal), "能量 kcal": _to_chart_number(energy)})
    return rows


def _item_energy_kcal(item: dict[str, Any]) -> float | None:
    nutrients = item.get("nutrients") or {}
    if isinstance(nutrients, dict):
        energy = _to_optional_float(nutrients.get("energy_kcal"))
        if energy is not None:
            return energy
    return _to_optional_float(item.get("energy_kcal"))


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


def _primary_limiting_factor(caps: list[dict[str, Any]]) -> str:
    if not caps:
        return "未触发等级封顶"
    trigger = str(caps[0].get("trigger") or "")
    return GRADE_CAP_LABELS.get(trigger, trigger or "未知限制因素")


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


def _grade_badge_class(grade: Any) -> str:
    text = str(grade or "").strip().lower()
    if text in {"a", "b", "c", "d", "e"}:
        return f"rq-grade-{text}"
    return "rq-grade-c"


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


def _html_escape(value: Any) -> str:
    return html.escape(str(value or ""))


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


def _to_float(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _format_nutrition_value(value: Any, unit: str) -> str:
    number = _to_float(value)
    if unit == "kcal":
        return f"{number:.0f} {unit}"
    if unit == "mg":
        return f"{number:.0f} {unit}"
    return f"{number:.1f} {unit}"


def _format_target(value: Any, unit: str) -> str:
    return _format_nutrition_value(value, unit)


def _to_chart_number(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return 0.0


def _to_optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


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
