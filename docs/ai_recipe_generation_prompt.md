# AI 食谱 JSON 生成提示词

将下面提示词复制给任意 AI，并把同一个 `target_user` 粘贴进去，即可让不同 AI 生成可被本项目读取和评分的全天食谱 JSON。

```text
你是一名营养食谱生成助手。请根据下面 target_user，为该用户生成一份全天饮食记录 JSON

要求：
1. 只输出 JSON，不要输出 Markdown，不要解释。
2. JSON 必须能被 Python json.loads 直接解析。
3. 使用中文食材名和中文菜品名。
4. 不要输出 search_name、food_group、processing_level、cooking_method 等中途标注字段。
5. 每个食材必须包含 name、amount_g、edible。
6. 调味品必须写入 condiments，并标明 amount_g。
7. 餐次 meal_name 只能使用 breakfast、lunch、dinner。
8. 加餐或水果放入 extra_items，meal_name 使用 snack。
9. 重量单位统一为克。
10. 目标是生成一份普通健康成年人可执行的全天饮食，不要极端节食或极端高热量。


target_user: {
    "sex": "female",
    "age": 30,
    "height_cm": 165,
    "weight_kg": 58,
    "activity_level": "light",
    "liked_foods": ["鸡蛋", "番茄", "土豆"],
    "disliked_foods": [],
    "dietary_restrictions": [],
    "habit_pattern": "chinese_home_meals"
  },

请严格输出以下结构：

{
  "evaluation_scope": "whole_day",
  "target_population": "healthy_adult",
  "date": "2026-05-12",
  "target_user": {
    "sex": "female",
    "age": 30,
    "height_cm": 165,
    "weight_kg": 58,
    "activity_level": "light",
    "liked_foods": ["鸡蛋", "番茄", "土豆"],
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
          "dish_name": "菜品名",
          "dish_type": "simple_foods",
          "ingredients": [
            {"name": "食材名", "amount_g": 100, "edible": true}
          ],
          "condiments": []
        }
      ]
    }
  ],
  "extra_items": [
    {
      "name": "水果或加餐",
      "amount_g": 150,
      "meal_name": "snack",
      "item_type": "fruit"
    }
  ],
  "record_quality": {
    "has_ingredient_weights": true,
    "has_condiments": true,
    "has_snacks_and_drinks": true,
    "completeness": "complete"
  }
}
```

使用建议：

- 对比不同 AI 时，保持 `target_user` 完全一致。
- 保存每个 AI 的输出为独立 `.json` 文件。
- 在 Streamlit 页面“输入配置”中上传 JSON 文件，再点击“加载 JSON 到表格”后运行评分。
