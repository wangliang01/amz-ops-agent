"""Deterministic inventory, budget, pricing and ROI plan for one SKU.

Inventory, unit cost, sales velocity and ad spend are simulated demo inputs
(the seed marks them as simulated). Review-driven demand is handled separately
in `agent/opportunity.py`. The point of this module is to show the decision
shape a seller ops agent would need, with every assumption visible.
"""
from __future__ import annotations

import math
from typing import Any

from core.store import SeedStore

LEAD_TIME_DAYS = 30
SAFETY_STOCK_DAYS = 14
CASE_PACK_UNITS = 50
MIN_MARGIN = 0.30
PRICE_CEILING_PCT = 0.08
HOURLY_RATE_USD = 30.0

NODE_MINUTES = {
    "insight": 10,
    "listing": 25,
    "compliance": 10,
    "creative": 15,
    "ads": 15,
    "ops": 10,
}


def _round_up_to(value: float, step: int) -> int:
    if value <= 0:
        return 0
    return int(math.ceil(value / step) * step)


def _inventory(store: SeedStore, sku: dict[str, Any]) -> dict[str, Any]:
    price = float(sku.get("price") or 0)
    rows = store.ads_for(str(sku["sku_id"]), days=30)
    sales = sum(float(row.get("sales") or 0) for row in rows)
    daily_units = sales / price / 30 if price and rows else 0.0
    on_hand = int(sku.get("stock") or 0)
    days_of_cover = on_hand / daily_units if daily_units else None
    reorder_point = _round_up_to(daily_units * (LEAD_TIME_DAYS + SAFETY_STOCK_DAYS), 1)
    target_days = LEAD_TIME_DAYS + SAFETY_STOCK_DAYS + 30
    reorder_qty = _round_up_to(max(0.0, daily_units * target_days - on_hand), CASE_PACK_UNITS)
    if days_of_cover is None:
        status = "no_sales_signal"
    elif days_of_cover <= LEAD_TIME_DAYS + SAFETY_STOCK_DAYS:
        status = "reorder_now"
    elif days_of_cover <= LEAD_TIME_DAYS + SAFETY_STOCK_DAYS + 14:
        status = "watch"
    else:
        status = "healthy"
    return {
        "on_hand": on_hand,
        "daily_units": round(daily_units, 2),
        "days_of_cover": round(days_of_cover, 1) if days_of_cover is not None else None,
        "lead_time_days": LEAD_TIME_DAYS,
        "safety_days": SAFETY_STOCK_DAYS,
        "reorder_point": reorder_point,
        "reorder_qty": reorder_qty,
        "status": status,
    }


def _budget(store: SeedStore, sku: dict[str, Any]) -> dict[str, Any]:
    rows = store.ads_for(str(sku["sku_id"]), days=30)
    spend = sum(float(row.get("spend") or 0) for row in rows)
    sales = sum(float(row.get("sales") or 0) for row in rows)
    daily_budget = spend / 30 if rows else 0.0
    acos = spend / sales if sales else 0.0
    target = float(sku.get("target_acos") or 0.30)
    if acos > target and acos > 0:
        factor = max(0.70, target / acos)
        action = "decrease"
        reason = f"ACOS {acos:.1%} 高于目标 {target:.0%}，先收紧预算再优化关键词。"
    elif acos and acos < target * 0.80:
        factor = 1.10
        action = "increase"
        reason = f"ACOS {acos:.1%} 低于目标 {target:.0%}，有放量空间。"
    else:
        factor = 1.0
        action = "hold"
        reason = f"ACOS {acos:.1%} 接近目标 {target:.0%}，维持预算。"
    return {
        "spend_30d": round(spend, 2),
        "sales_30d": round(sales, 2),
        "acos_30d": round(acos, 3),
        "target_acos": round(target, 3),
        "daily_budget": round(daily_budget, 2),
        "proposed_daily_budget": round(daily_budget * factor, 2),
        "action": action,
        "reason": reason,
    }


def _price(sku: dict[str, Any]) -> dict[str, Any]:
    price = float(sku.get("price") or 0)
    cost = float(sku.get("cost") or 0)
    floor = cost / (1 - MIN_MARGIN) if cost else 0.0
    ceiling = price * (1 + PRICE_CEILING_PCT)
    if price and price < floor:
        action = "raise_to_floor"
        recommended = floor
    else:
        action = "hold"
        recommended = price
    return {
        "current_price": round(price, 2),
        "unit_cost": round(cost, 2),
        "floor_price": round(floor, 2),
        "ceiling_price": round(ceiling, 2),
        "recommended_price": round(recommended, 2),
        "discount_headroom_pct": round(max(0.0, (price - floor) / price), 3) if price else 0.0,
        "action": action,
    }


def _roi(
    ads_report: dict[str, Any] | None,
    compliance_report: dict[str, Any] | None,
    metrics: dict[str, Any] | None,
) -> dict[str, Any]:
    node_times = (metrics or {}).get("node_times") or {}
    minutes = sum(
        value for node, value in NODE_MINUTES.items() if node in node_times
    )
    labor_value = minutes / 60 * HOURLY_RATE_USD
    llm_cost = float((metrics or {}).get("cost_usd") or 0.0)
    delta = ((ads_report or {}).get("backtest") or {}).get("delta") or {}
    return {
        "human_minutes_saved": minutes,
        "hourly_rate_usd": HOURLY_RATE_USD,
        "labor_value_usd": round(labor_value, 2),
        "llm_cost_usd": round(llm_cost, 6),
        "net_value_usd": round(labor_value - llm_cost, 2),
        "projected_acos_delta": delta.get("acos"),
        "compliance_fixes": int((compliance_report or {}).get("fixed_count") or 0),
        "assumptions": [
            "人工分钟数按节点固定估算，不是工时实测。",
            "时薪按 $30/h 演示假设。",
            "ACOS 变化来自广告回测的弹性假设，不是线上实测。",
        ],
    }


def build_ops_plan(
    store: SeedStore,
    sku: dict[str, Any],
    ads_report: dict[str, Any] | None = None,
    compliance_report: dict[str, Any] | None = None,
    metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    inventory = _inventory(store, sku)
    budget = _budget(store, sku)
    price = _price(sku)
    roi = _roi(ads_report, compliance_report, metrics)
    return {
        "sku_id": str(sku["sku_id"]),
        "simulated": True,
        "inventory": inventory,
        "budget": budget,
        "price_guardrail": price,
        "roi": roi,
        "assumptions": [
            {"item": "库存与日销量", "value": "来自模拟 stock 与 90 天广告销售", "simulated": True},
            {"item": "补货提前期", "value": f"{LEAD_TIME_DAYS} 天", "simulated": True},
            {"item": "安全库存", "value": f"{SAFETY_STOCK_DAYS} 天", "simulated": True},
            {"item": "最小毛利率", "value": f"{MIN_MARGIN:.0%}", "simulated": True},
            {"item": "广告日预算", "value": "30 天花费 / 30", "simulated": True},
            {"item": "标价", "value": "真实公开标价", "simulated": False},
            {"item": "单位成本", "value": "模拟", "simulated": True},
        ],
    }
