from __future__ import annotations


def score_daily_intake_fit(
    daily_totals: dict,
    resolved_targets: dict | None = None,
) -> tuple[float, dict[str, float]]:
    """计算 D 全天摄入总量适配分数和明细。"""
    target_energy = float((resolved_targets or {}).get("energy_kcal", 2000))
    energy = float(daily_totals.get("energy_kcal") or 0)
    energy_score = score_energy_match(energy / target_energy if target_energy else 0)
    macro_score = score_macro_distribution(daily_totals)
    details = {
        "energy_match": round(energy_score, 2),
        "macro_distribution": round(macro_score, 2),
    }
    return round(sum(details.values()), 2), details


def score_energy_match(ratio: float) -> float:
    """根据实际能量与目标能量的比例计算 D1 能量匹配得分。"""
    distance = abs(ratio - 1)
    if distance <= 0.05:
        return 8.0
    if distance <= 0.10:
        return _interpolate(distance, 0.05, 0.10, 8, 6)
    if distance <= 0.20:
        return _interpolate(distance, 0.10, 0.20, 6, 3)
    if distance <= 0.30:
        return _interpolate(distance, 0.20, 0.30, 3, 1)
    return 0.0


def score_macro_distribution(daily_totals: dict) -> float:
    """根据三大营养素供能比计算 D2 供能结构得分。"""
    energy = daily_totals.get("energy_kcal") or 0
    if energy <= 0:
        return 0.0
    protein_ratio = (daily_totals.get("protein_g") or 0) * 4 / energy
    fat_ratio = (daily_totals.get("fat_g") or 0) * 9 / energy
    carb_ratio = (daily_totals.get("carbohydrate_g") or 0) * 4 / energy
    off_count = 0
    off_count += not (0.10 <= protein_ratio <= 0.20)
    off_count += not (0.20 <= fat_ratio <= 0.30)
    off_count += not (0.50 <= carb_ratio <= 0.65)
    if off_count == 0:
        return 4.0
    if off_count == 1:
        return 3.0
    if off_count == 2:
        return 2.0
    return 1.0


def _interpolate(value: float, x0: float, x1: float, y0: float, y1: float) -> float:
    """在两个区间端点之间做线性插值。"""
    return y0 + (value - x0) * (y1 - y0) / (x1 - x0)
