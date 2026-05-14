from recipe_quality.fatsecret.resolver import FatSecretResolver, choose_serving


class FakeClient:
    def __init__(self):
        self.last_query = None

    def search_foods(self, query, max_results=10):
        """模拟 FatSecret 搜索接口返回品牌和通用候选。"""
        self.last_query = query
        return {
            "foods": {
                "food": [
                    {"food_id": "2", "food_name": "Brand Rice", "food_type": "Brand", "brand_name": "X"},
                    {"food_id": "1", "food_name": "Rice", "food_type": "Generic"},
                ]
            }
        }

    def get_food(self, food_id):
        """模拟 FatSecret 食物详情接口返回多个 serving。"""
        assert food_id == "1"
        return {
            "food": {
                "food_id": "1",
                "food_name": "Rice",
                "servings": {
                    "serving": [
                        {
                            "serving_description": "1 cup",
                            "metric_serving_amount": "158",
                            "metric_serving_unit": "g",
                            "calories": "205",
                        },
                        {
                            "serving_description": "100 g",
                            "metric_serving_amount": "100",
                            "metric_serving_unit": "g",
                            "calories": "130",
                            "protein": "2.7",
                        },
                    ]
                },
            }
        }


def test_resolver_prefers_generic_candidate_and_100g_serving():
    """验证解析器优先选择 Generic 候选和 100g serving。"""
    resolver = FatSecretResolver(FakeClient())

    resolved = resolver.resolve_item({"name": "rice", "amount_g": 200})

    assert resolved.fatsecret_food_id == "1"
    assert resolved.serving_used == "100 g"
    assert resolved.nutrients.energy_kcal == 260
    assert resolved.match_confidence == "high"
    assert resolved.nutrition_estimation_status == "resolved"


def test_resolver_uses_search_name_for_fatsecret_query_and_keeps_original_name():
    client = FakeClient()
    resolver = FatSecretResolver(client)

    resolved = resolver.resolve_item({"name": "米饭", "search_name": "rice", "amount_g": 200})

    assert client.last_query == "rice"
    assert resolved.name == "米饭"
    assert resolved.search_name == "rice"
    assert resolved.fatsecret_food_name == "Rice"
    assert resolved.match_confidence == "high"


def test_choose_serving_returns_none_when_no_metric_serving():
    """验证没有可按克数换算的 serving 时返回 None。"""
    assert choose_serving([{"serving_description": "1 serving", "calories": "100"}]) is None
