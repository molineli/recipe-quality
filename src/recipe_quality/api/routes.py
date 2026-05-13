from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from recipe_quality.aggregator import resolve_and_aggregate
from recipe_quality.engine import evaluate_daily_diet
from recipe_quality.fatsecret import FatSecretClient, FatSecretError, FatSecretResolver
from recipe_quality.normalizer import normalize_recipe_input

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    """返回 API 服务健康状态。"""
    return {"status": "ok"}


@router.get("/foods/search")
def foods_search(q: str = Query(..., min_length=1), max_results: int = 10) -> dict[str, Any]:
    """通过 FatSecret 搜索食物候选。"""
    try:
        return FatSecretClient().search_foods(q, max_results=max_results)
    except FatSecretError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/nutrition/resolve")
def nutrition_resolve(payload: dict[str, Any]) -> dict[str, Any]:
    """解析食物列表并汇总全天营养数据。"""
    try:
        resolver = FatSecretResolver(FatSecretClient())
        normalized = normalize_recipe_input(payload)
        return resolve_and_aggregate(
            resolver,
            normalized["ingredient_records"],
            normalized["condiments"],
            dish_records=normalized["dish_records"],
            record_quality=payload.get("record_quality"),
        )
    except FatSecretError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/evaluate")
def evaluate(payload: dict[str, Any]) -> dict[str, Any]:
    """解析营养数据后调用本地规则引擎完成评分。"""
    try:
        resolver = FatSecretResolver(FatSecretClient())
        normalized = normalize_recipe_input(payload)
        resolved = resolve_and_aggregate(
            resolver,
            normalized["ingredient_records"],
            normalized["condiments"],
            dish_records=normalized["dish_records"],
            record_quality=payload.get("record_quality"),
        )
        enriched = {
            **payload,
            "items": resolved["items"],
            "ingredient_records": resolved["ingredient_records"],
            "dish_records": resolved["dish_records"],
            "daily_totals": resolved["daily_totals"],
        }
        return evaluate_daily_diet(enriched)
    except FatSecretError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
