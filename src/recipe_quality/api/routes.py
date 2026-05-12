from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from recipe_quality.aggregator import resolve_and_aggregate
from recipe_quality.engine import evaluate_daily_diet
from recipe_quality.fatsecret import FatSecretClient, FatSecretError, FatSecretResolver

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/foods/search")
def foods_search(q: str = Query(..., min_length=1), max_results: int = 10) -> dict[str, Any]:
    try:
        return FatSecretClient().search_foods(q, max_results=max_results)
    except FatSecretError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/nutrition/resolve")
def nutrition_resolve(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        resolver = FatSecretResolver(FatSecretClient())
        return resolve_and_aggregate(
            resolver,
            payload.get("items", []),
            payload.get("condiments", []),
        )
    except FatSecretError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/evaluate")
def evaluate(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        resolver = FatSecretResolver(FatSecretClient())
        resolved = resolve_and_aggregate(
            resolver,
            payload.get("items", []),
            payload.get("condiments", []),
        )
        enriched = {
            **payload,
            "items": resolved["items"],
            "daily_totals": resolved["daily_totals"],
        }
        return evaluate_daily_diet(enriched)
    except FatSecretError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

