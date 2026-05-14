# Recipe Quality

Recipe Quality 是一个面向全天饮食记录的规则化评分工具。它把用户输入的食谱和食材重量，经过 AI 结构化标注、FatSecret 营养查询、全天营养汇总和本地规则引擎计算，输出可解释的饮食质量分数与等级。

当前项目重点不是让 AI 直接打分，而是让 AI 补充规则计算所需的结构化标签；最终分数由本地规则函数计算。

## 当前能力

- 支持 `evaluation_scope = whole_day` 的全天饮食评分。
- 支持普通成年健康人群的默认目标，也可根据 `target_user` 的性别、年龄、身高、体重和活动水平估算能量目标。
- 使用 Qwen/OpenAI-compatible Chat Completions 做 AI 标注：
  - 菜品烹调方式 `cooking_method`
  - 食材食物组 `food_group`
  - 食材加工程度 `processing_level`
  - FatSecret 美国库检索名 `search_name`
  - 喜好匹配、饮食习惯匹配、可执行性因素
- 使用 FatSecret 美国数据库查询营养数据，并按实际摄入克数换算。
- 按 A/B/C/D/E 模块计算 100 分制总分，并应用最高等级封顶规则。

## 评分模块

| 模块 | 分值 | 当前实现 |
| --- | ---: | --- |
| A. 基础营养质量 | 40 | 食物组覆盖、蛋白质、膳食纤维、关键微量营养素 |
| B. 限制性成分控制 | 25 | 钠、烹调油、添加糖、饱和脂肪 |
| C. 烹调与加工 | 15 | 烹调方式、食材加工程度 |
| D. 全天摄入总量适配 | 12 | 能量匹配、三大营养素供能结构 |
| E. 个性化与可执行性 | 8 | 喜好食材、饮食习惯、执行难度 |

等级规则：

```text
90–100: A
80–89:  B
70–79:  C
60–69:  D
<60:    E
```

封顶规则会限制最终等级，例如能量明显偏离、钠/油/糖严重超标、食物结构严重缺失、可食部重量或餐次能量分布异常、数据质量不足等。

## 项目结构

```text
src/recipe_quality/
├── ai_annotation.py                 # AI 标注 schema、调用与合并
├── normalizer.py                    # 输入标准化为食材/菜品/调味品记录
├── aggregator.py                    # 营养与食物组聚合
├── engine.py                        # 总评分入口
├── targets.py                       # 每日目标估算
├── fatsecret/
│   ├── client.py                    # FatSecret OAuth 与 API 客户端
│   ├── resolver.py                  # 食材搜索、候选排序、serving 选择
│   ├── mapper.py                    # FatSecret serving 到内部营养字段映射
│   └── schemas.py                   # FatSecret 响应结构适配
└── scoring/
    ├── basic_nutrition.py
    ├── limiting_components.py
    ├── cooking_processing_safety.py
    ├── daily_intake_fit.py
    ├── personalization.py
    └── grade.py
```

重要配置：

```text
configs/food_groups.yaml
configs/cooking_methods.yaml
configs/processing_levels.yaml
configs/scoring.yaml
configs/grade_caps.yaml
```

## 环境变量

项目会读取 `.env`。最少需要：

```env
FATSECRET_CLIENT_ID=your_client_id
FATSECRET_CLIENT_SECRET=your_client_secret
FATSECRET_SCOPE=basic
FATSECRET_REGION=US
FATSECRET_LANGUAGE=en

OPENAI_API_KEY=your_api_key
OPENAI_MODEL=qwen-plus
OPENAI_API_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
OPENAI_TIMEOUT_SECONDS=120
```

说明：

- FatSecret 当前按美国库使用，因此 AI 会为中文食材补充英文 `search_name`。
- `OPENAI_TIMEOUT_SECONDS` 用于避免 AI 标注请求在网络较慢时过早超时。
- `.env` 不应提交到 Git。

## 输入格式

示例见：

```text
examples/input_day.json
```

推荐输入保持接近用户原始记录，只提供基础事实：

- 餐次 `meal_name`
- 菜品名 `dish_name`
- 食材名 `name`
- 食材重量 `amount_g`
- 调味品及用量
- 用户基础信息与偏好

不要在原始输入中预填这些中途字段：

```text
search_name
food_group
cooking_method
processing_level
classification_source
classification_confidence
```

这些字段应由 AI 标注阶段补充。

## 完整流程验证

在项目根目录运行：

```powershell
.\.venv\Scripts\python.exe scripts\full_pipeline_eval.py examples\input_day.json
```

输出内容包括：

- AI 标注 warnings
- 每个食材的 `search_name`、`food_group`、`processing_level`
- FatSecret 匹配食物、serving、营养解析状态
- 全天营养汇总
- 总分、原始等级、最终等级
- 模块分
- 触发的封顶规则

保存结果：

```powershell
.\.venv\Scripts\python.exe scripts\full_pipeline_eval.py examples\input_day.json > full_result.json
```

## 常用脚本

```powershell
# 完整 AI + FatSecret + 评分流程
.\.venv\Scripts\python.exe scripts\full_pipeline_eval.py examples\input_day.json

# 仅 FatSecret 搜索
.\.venv\Scripts\python.exe scripts\fatsecret_search.py rice 10

# 按 FatSecret food_id 查询详情
.\.venv\Scripts\python.exe scripts\fatsecret_get_food.py <food_id>

# FatSecret 营养查询冒烟测试
.\.venv\Scripts\python.exe scripts\smoke_fatsecret_nutrition.py
```

`scripts/calculate_initial_totals.py` 是较早的营养汇总脚本，不会自动执行 AI 标注；如果输入缺少 `search_name`、`food_group` 等字段，优先使用 `full_pipeline_eval.py`。

## 运行测试

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

当前测试覆盖：

- AI 标注 schema 与合并
- FatSecret 响应解析、候选排序、100g serving 优先
- 输入标准化
- 全天营养聚合
- A/B/C/D/E 评分模块
- 等级封顶规则
- API 关键路径

## 设计原则

- AI 只负责结构化标注和辅助解释，不直接决定分数。
- 评分规则保持本地、透明、可测试、可调整。
- 不确定的数据应保留 warning 或低置信度标记。
- FatSecret 匹配保留原始中文 `name`，同时使用英文 `search_name` 查询美国库。
- 100g/100ml serving 优先用于营养换算；没有标准 serving 时才回退到其他可按 g/ml 换算的 serving。
