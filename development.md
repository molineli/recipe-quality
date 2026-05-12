# Development Guide

本文档说明当前项目结构、每个文件的作用，以及文件之间的数据流关系。

## 项目目标

本项目实现 RQS-P 全天饮食质量评分体系的工程骨架。当前版本重点完成：

- 通过 FatSecret API 查询食物营养数据；
- 将 FatSecret serving 数据换算为用户实际摄入克数；
- 汇总全天营养指标；
- 提供初始评分入口和 API/CLI 调用方式；
- 保留完整 RQS-P 规则层的扩展位置。

核心原则是：**AI 或外部 API 只负责数据解析与营养查询，评分由本地规则引擎计算。**

## 顶层结构

```text
recipe_quality/
├── .env
├── .env.example
├── .gitignore
├── README.md
├── development.md
├── feedback.md
├── pyproject.toml
├── rules.md
├── 评价规则.md
├── 评价规则.pdf
├── configs/
├── examples/
├── scripts/
├── src/
└── tests/
```

### 顶层文件

| 文件 | 作用 |
| --- | --- |
| `.env` | 本地环境变量文件，用于保存 FatSecret 凭证；不提交 Git。 |
| `.env.example` | 环境变量模板，说明需要配置哪些 FatSecret 参数。 |
| `.gitignore` | Git 忽略规则，排除 `.env`、缓存、PDF 等文件。 |
| `README.md` | 项目简介和评分规则概览。 |
| `development.md` | 当前文件，说明项目结构和开发关系。 |
| `feedback.md` | 对评分规则的设计反馈和落地建议。 |
| `pyproject.toml` | Python 项目元数据、依赖、测试配置。 |
| `rules.md` | 评分规则文档。 |
| `评价规则.md` | 当前主要中文规则文档，后续实现规则层时应优先参考。 |
| `评价规则.pdf` | 规则 PDF 文件，已在 `.gitignore` 中忽略。 |

## 配置目录

```text
configs/
├── cooking_methods.yaml
├── food_groups.yaml
├── grade_caps.yaml
└── scoring.yaml
```

| 文件 | 作用 |
| --- | --- |
| `configs/scoring.yaml` | 保存 A/B/C/D/E 模块权重。 |
| `configs/food_groups.yaml` | 保存食物组和目标摄入量配置。 |
| `configs/cooking_methods.yaml` | 保存烹调方式代码和基础分。 |
| `configs/grade_caps.yaml` | 保存等级封顶相关阈值。 |

当前代码中部分规则还写在 Python 默认值里，后续应逐步改为读取这些配置文件，减少硬编码。

## 示例目录

```text
examples/
├── input_day.json
└── resolved_day.json
```

| 文件 | 作用 |
| --- | --- |
| `examples/input_day.json` | 示例输入，包含全天食物项、重量、餐次、调味品和目标值。 |
| `examples/resolved_day.json` | 解析后结果示例占位，用于展示 `items` 和 `daily_totals` 的目标结构。 |

`input_day.json` 可直接用于：

```bash
python scripts/calculate_initial_totals.py examples/input_day.json
```

## 脚本目录

```text
scripts/
├── calculate_initial_totals.py
├── fatsecret_get_food.py
└── fatsecret_search.py
```

| 文件 | 作用 |
| --- | --- |
| `scripts/fatsecret_search.py` | 命令行搜索 FatSecret 食物。 |
| `scripts/fatsecret_get_food.py` | 根据 FatSecret `food_id` 查询食物详情和 serving。 |
| `scripts/calculate_initial_totals.py` | 读取全天饮食 JSON，查询 FatSecret，汇总营养，并调用评分入口。 |

脚本与核心代码的关系：

```text
scripts/*
  → recipe_quality.fatsecret.client.FatSecretClient
  → recipe_quality.fatsecret.resolver.FatSecretResolver
  → recipe_quality.aggregator.resolve_and_aggregate
  → recipe_quality.engine.evaluate_daily_diet
```

## 源码目录

```text
src/
└── recipe_quality/
    ├── __init__.py
    ├── aggregator.py
    ├── engine.py
    ├── models.py
    ├── api/
    ├── fatsecret/
    ├── scoring/
    └── utils/
```

### 核心文件

| 文件 | 作用 |
| --- | --- |
| `src/recipe_quality/__init__.py` | 包入口，定义版本号。 |
| `src/recipe_quality/models.py` | 定义内部数据结构，如 `Nutrients`、`ResolvedFoodItem`。 |
| `src/recipe_quality/aggregator.py` | 汇总全天营养数据，处理调味品中的盐、油、糖。 |
| `src/recipe_quality/engine.py` | 评分总入口，组织 A/B/C/D/E 模块计算、总分、等级和封顶规则。 |

### 数据模型关系

`models.py` 是多个模块共享的基础：

```text
FatSecret mapper
  → Nutrients

FatSecret resolver
  → ResolvedFoodItem

Aggregator
  → list[ResolvedFoodItem]
  → daily_totals

Engine
  → daily_totals
  → evaluation result
```

## API 模块

```text
src/recipe_quality/api/
├── __init__.py
├── app.py
└── routes.py
```

| 文件 | 作用 |
| --- | --- |
| `api/__init__.py` | API 子包标识文件。 |
| `api/app.py` | 创建 FastAPI 应用，并挂载路由。 |
| `api/routes.py` | 定义 HTTP 接口：健康检查、食物搜索、营养解析、评分。 |

当前接口：

| 接口 | 作用 |
| --- | --- |
| `GET /health` | 健康检查。 |
| `GET /foods/search?q=米饭` | 调用 FatSecret 搜索食物。 |
| `POST /nutrition/resolve` | 将食物列表解析为营养数据并汇总。 |
| `POST /evaluate` | 先解析营养，再调用本地规则引擎评分。 |

API 调用关系：

```text
api/app.py
  → api/routes.py
    → FatSecretClient
    → FatSecretResolver
    → resolve_and_aggregate
    → evaluate_daily_diet
```

## FatSecret 模块

```text
src/recipe_quality/fatsecret/
├── __init__.py
├── client.py
├── mapper.py
├── resolver.py
└── schemas.py
```

| 文件 | 作用 |
| --- | --- |
| `fatsecret/__init__.py` | 导出 FatSecret 相关公开类。 |
| `fatsecret/client.py` | FatSecret API 客户端，负责 OAuth2 token、搜索、详情查询和错误处理。 |
| `fatsecret/schemas.py` | 适配 FatSecret 返回结构，将单对象或数组统一成 list。 |
| `fatsecret/mapper.py` | 将 FatSecret serving 字段映射成本项目内部营养字段，并按克数换算。 |
| `fatsecret/resolver.py` | 食物解析器：搜索候选、排序、选择 serving、返回 `ResolvedFoodItem`。 |

FatSecret 数据流：

```text
用户食物项
  → FatSecretResolver.resolve_item
  → FatSecretClient.search_foods
  → schemas.extract_foods
  → resolver.rank_candidates
  → FatSecretClient.get_food
  → schemas.extract_servings
  → resolver.choose_serving
  → mapper.scale_serving_to_amount
  → ResolvedFoodItem
```

### 关键设计

- `client.py` 只负责 HTTP 和认证，不做业务判断。
- `schemas.py` 只解决 FatSecret 返回结构不稳定的问题。
- `mapper.py` 只做字段映射和单位换算。
- `resolver.py` 做候选排序和 serving 选择。

这样可以分别测试网络层、映射层和匹配策略。

## 评分模块

```text
src/recipe_quality/scoring/
├── __init__.py
├── basic_nutrition.py
├── cooking_processing_safety.py
├── daily_intake_fit.py
├── grade.py
├── limiting_components.py
└── personalization.py
```

| 文件 | 作用 |
| --- | --- |
| `scoring/__init__.py` | 评分子包标识文件。 |
| `scoring/basic_nutrition.py` | A 基础营养质量；当前实现蛋白质、纤维、微量营养素初版，食物组覆盖仍待补齐。 |
| `scoring/limiting_components.py` | B 限制性成分控制；实现钠、烹调油、添加糖、饱和脂肪评分。 |
| `scoring/cooking_processing_safety.py` | C 烹调、加工与食品安全；当前为扩展骨架。 |
| `scoring/daily_intake_fit.py` | D 全天摄入总量适配；实现能量匹配和三大营养素供能结构评分。 |
| `scoring/personalization.py` | E 个性化与可执行性；当前为扩展骨架。 |
| `scoring/grade.py` | 总分转等级、等级封顶规则。 |

评分调用关系：

```text
engine.evaluate_daily_diet
  → score_basic_nutrition
  → score_limiting_components
  → score_cooking_processing_safety
  → score_daily_intake_fit
  → score_personalization
  → score_to_grade
  → evaluate_grade_caps
  → apply_grade_caps
```

## 工具模块

```text
src/recipe_quality/utils/
├── __init__.py
├── math.py
└── units.py
```

| 文件 | 作用 |
| --- | --- |
| `utils/__init__.py` | 工具子包标识文件。 |
| `utils/math.py` | 通用数学函数，如线性限量评分。 |
| `utils/units.py` | 单位换算，目前包含食盐克数转钠毫克。 |

## 测试目录

```text
tests/
├── test_aggregator.py
├── test_engine.py
├── test_fatsecret_mapper.py
└── test_fatsecret_resolver.py
```

| 文件 | 作用 |
| --- | --- |
| `tests/test_fatsecret_mapper.py` | 测试 FatSecret 字段映射和 serving 克数换算。 |
| `tests/test_fatsecret_resolver.py` | 使用 fake client 测试候选排序、serving 选择和解析结果。 |
| `tests/test_aggregator.py` | 测试全天营养汇总和调味品换算。 |
| `tests/test_engine.py` | 测试评分入口和等级封顶规则。 |

测试设计原则：

- 不依赖真实 FatSecret 网络；
- 不消耗 API 额度；
- 用 fake client/mock 数据验证核心逻辑。

## 主要数据流

### 1. API 评分流程

```text
POST /evaluate
  → routes.evaluate
  → FatSecretClient
  → FatSecretResolver.resolve_items
  → resolve_and_aggregate
  → aggregate_daily_totals
  → evaluate_daily_diet
  → JSON response
```

### 2. CLI 初始计算流程

```text
python scripts/calculate_initial_totals.py examples/input_day.json
  → 读取 input_day.json
  → FatSecretResolver
  → resolve_and_aggregate
  → evaluate_daily_diet
  → 打印 resolved + evaluation JSON
```

### 3. 营养字段转换流程

```text
FatSecret serving
  calories       → energy_kcal
  protein        → protein_g
  fat            → fat_g
  saturated_fat  → saturated_fat_g
  carbohydrate   → carbohydrate_g
  fiber          → fiber_g
  sodium         → sodium_mg
  potassium      → potassium_mg
  calcium        → calcium_mg
  iron           → iron_mg
  vitamin_c      → vitamin_c_mg
  added_sugars   → added_sugar_g
```

### 4. 调味品处理流程

调味品不会全部交给 FatSecret。当前本地处理：

```text
食盐 amount_g
  → sodium_mg = amount_g × 393.4

烹调油 amount_g
  → cooking_oil_g

糖 amount_g
  → added_sugar_g
```

## 当前实现边界

已实现：

- FatSecret OAuth2 客户端；
- 食物搜索和详情查询；
- serving 选择和克数换算；
- FatSecret 营养字段映射；
- 全天营养汇总；
- 初始 B/D 模块评分；
- 部分 A 模块营养素评分；
- 等级封顶基础规则；
- API 和 CLI 入口。

待补齐：

- A1 食物组覆盖评分；
- C 烹调、加工与食品安全完整评分；
- E 个性化与可执行性完整评分；
- 从 `configs/*.yaml` 统一读取规则配置；
- FatSecret 查询结果缓存；
- 中文食物名匹配失败时的翻译或人工确认流程；
- 更完整的数据质量封顶和解释输出。

## 本地运行

安装依赖：

```bash
python -m pip install -e .[dev]
```

配置 `.env`：

```env
FATSECRET_CLIENT_ID=your_client_id
FATSECRET_CLIENT_SECRET=your_client_secret
FATSECRET_SCOPE=basic
FATSECRET_REGION=CN
FATSECRET_LANGUAGE=zh
```

搜索食物：

```bash
python scripts/fatsecret_search.py "米饭"
```

查询食物详情：

```bash
python scripts/fatsecret_get_food.py 12345
```

计算示例全天饮食：

```bash
python scripts/calculate_initial_totals.py examples/input_day.json
```

启动 API：

```bash
uvicorn recipe_quality.api.app:app --reload
```

运行测试：

```bash
python -m pytest
```

