from __future__ import annotations

import time
from typing import Any

import pandas as pd

from agent.nodes.common import update_metrics
from agent.services import Services


def _aggregate(df: pd.DataFrame, price: float) -> dict[str, Any]:
    if df.empty:
        return {
            "spend": 0.0,
            "sales": 0.0,
            "clicks": 0,
            "impressions": 0,
            "orders": 0.0,
            "acos": 0.0,
            "ctr": 0.0,
            "cvr": 0.0,
        }
    spend = float(df["spend"].sum())
    sales = float(df["sales"].sum())
    clicks = int(df["clicks"].sum())
    impressions = int(df["impressions"].sum())
    orders = sales / price if price else 0.0
    return {
        "spend": round(spend, 2),
        "sales": round(sales, 2),
        "clicks": clicks,
        "impressions": impressions,
        "orders": round(orders, 2),
        "acos": round(spend / sales, 3) if sales else 0.0,
        "ctr": round(clicks / impressions, 5) if impressions else 0.0,
        "cvr": round(orders / clicks, 4) if clicks else 0.0,
    }


def _fallback_recommendations(
    keywords: list[dict[str, Any]], target: float
) -> list[dict[str, Any]]:
    recommendations = []
    for kw in keywords:
        acos = float(kw.get("acos_30d") or 0)
        current_bid = float(kw["bid"])
        if acos > target * 1.2:
            recommendations.append(
                {
                    "keyword": kw["keyword"],
                    "action": "decrease_bid",
                    "current_bid": current_bid,
                    "proposed_bid": round(current_bid * 0.85, 2),
                    "current_acos": acos,
                    "reason": f"ACOS {acos:.0%} is above target {target:.0%}.",
                }
            )
        elif acos < target * 0.7 and float(kw.get("sales_30d") or 0) > 0:
            recommendations.append(
                {
                    "keyword": kw["keyword"],
                    "action": "increase_bid",
                    "current_bid": current_bid,
                    "proposed_bid": round(current_bid * 1.05, 2),
                    "current_acos": acos,
                    "reason": f"ACOS {acos:.0%} is below target {target:.0%}; room to scale.",
                }
            )
    recommendations.sort(key=lambda item: -item["current_acos"])
    return recommendations[:5]


def _normalize_recommendations(
    raw: Any,
    keywords: list[dict[str, Any]],
    fallback: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_keyword = {item["keyword"]: item for item in keywords}
    if not isinstance(raw, list) or not raw:
        return fallback

    out = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        keyword = str(item.get("keyword") or "").strip()
        if keyword not in by_keyword:
            continue
        current_bid = float(by_keyword[keyword]["bid"])
        try:
            proposed = float(item.get("proposed_bid", current_bid))
        except (TypeError, ValueError):
            proposed = current_bid
        proposed = max(
            round(current_bid * 0.75, 2),
            min(round(current_bid * 1.10, 2), round(proposed, 2)),
        )
        out.append(
            {
                "keyword": keyword,
                "action": str(
                    item.get("action")
                    or ("decrease_bid" if proposed < current_bid else "increase_bid")
                ),
                "current_bid": current_bid,
                "proposed_bid": proposed,
                "current_acos": float(by_keyword[keyword].get("acos_30d") or 0),
                "reason": str(item.get("reason") or "Adjust bid toward the target ACOS."),
            }
        )
    return out[:5] or fallback


def _backtest(
    keywords: list[dict[str, Any]], recommendations: list[dict[str, Any]]
) -> dict[str, Any]:
    rec_by_keyword = {item["keyword"]: item for item in recommendations}
    baseline = {"spend": 0.0, "sales": 0.0}
    projected = {"spend": 0.0, "sales": 0.0}

    for kw in keywords:
        clicks = float(kw["clicks_30d"])
        spend = float(kw["spend_30d"])
        sales = float(kw["sales_30d"])
        baseline["spend"] += spend
        baseline["sales"] += sales

        current_bid = float(kw["bid"])
        rec = rec_by_keyword.get(kw["keyword"])
        new_bid = float(rec["proposed_bid"]) if rec else current_bid
        delta = (new_bid - current_bid) / current_bid if current_bid else 0.0
        click_factor = max(0.2, 1 + 0.6 * delta)
        cpc_factor = max(0.2, 1 + 0.5 * delta)

        new_clicks = clicks * click_factor
        new_spend = new_clicks * (spend / clicks if clicks else 0.0) * cpc_factor
        new_sales = sales * click_factor
        projected["spend"] += new_spend
        projected["sales"] += new_sales

    baseline_acos = baseline["spend"] / baseline["sales"] if baseline["sales"] else 0.0
    projected_acos = projected["spend"] / projected["sales"] if projected["sales"] else 0.0
    return {
        "assumption": (
            "Clicks scale with bid at 0.6 elasticity; CPC scales at 0.5; "
            "CVR and AOV held constant."
        ),
        "baseline": {
            "spend": round(baseline["spend"], 2),
            "sales": round(baseline["sales"], 2),
            "acos": round(baseline_acos, 3),
        },
        "projected": {
            "spend": round(projected["spend"], 2),
            "sales": round(projected["sales"], 2),
            "acos": round(projected_acos, 3),
        },
        "delta": {
            "spend": round(projected["spend"] - baseline["spend"], 2),
            "sales": round(projected["sales"] - baseline["sales"], 2),
            "acos": round(projected_acos - baseline_acos, 3),
        },
    }


def make_ads_node(services: Services):
    def ads_node(state: dict[str, Any]) -> dict[str, Any]:
        started = time.perf_counter()
        sku = state["sku"]
        price = float(sku["price"])
        rows = services.adapters.ads.get_daily_metrics(sku["sku_id"], days=90)
        df = pd.DataFrame(rows)

        last30 = _aggregate(df.tail(30), price)
        prev30 = _aggregate(df.iloc[-60:-30], price)
        keywords = services.adapters.ads.get_keyword_performance(sku["sku_id"])
        target = float(sku.get("target_acos") or services.cfg.target_acos)

        anomalies = []
        if last30["acos"] > target:
            anomalies.append(
                {
                    "type": "high_acos",
                    "severity": "high",
                    "detail": f"ACOS {last30['acos']:.2%} is above target {target:.0%}.",
                }
            )
        spend_delta = (
            (last30["spend"] - prev30["spend"]) / prev30["spend"]
            if prev30["spend"]
            else 0.0
        )
        sales_delta = (
            (last30["sales"] - prev30["sales"]) / prev30["sales"]
            if prev30["sales"]
            else 0.0
        )
        if spend_delta > 0.15 and sales_delta < 0.05:
            anomalies.append(
                {
                    "type": "wasted_spend",
                    "severity": "high",
                    "detail": f"Spend +{spend_delta:.1%} while sales +{sales_delta:.1%}.",
                }
            )
        if last30["ctr"] < 0.0035:
            anomalies.append(
                {
                    "type": "low_ctr",
                    "severity": "medium",
                    "detail": f"CTR {last30['ctr']:.2%} is below the 0.35% demo benchmark.",
                }
            )
        if last30["cvr"] < 0.06:
            anomalies.append(
                {
                    "type": "low_cvr",
                    "severity": "medium",
                    "detail": f"CVR {last30['cvr']:.2%} is below the 6% demo benchmark.",
                }
            )

        fallback_recs = _fallback_recommendations(keywords, target)
        keyword_block = "\n".join(
            f"- {kw['keyword']} ({kw['match_type']}): bid ${kw['bid']:.2f}, "
            f"ACOS {kw['acos_30d']:.2%}, spend ${kw['spend_30d']:.2f}, "
            f"sales ${kw['sales_30d']:.2f}"
            for kw in keywords
        )
        fallback = {
            "diagnosis": (
                "Rule-based diagnosis: high ACOS keywords are driving spend "
                "without matching sales."
            ),
            "recommendations": fallback_recs,
        }

        data, usage = services.llm.json(
            system=(
                "You are an Amazon PPC analyst. Diagnose the ad performance and return "
                "JSON with diagnosis (string) and recommendations (list of "
                "{keyword, action, current_bid, proposed_bid, reason}). Use only the "
                "provided data. Keep proposed bids within -25% to +10% of the current bid."
            ),
            user=(
                f"SKU: {sku['sku_id']} | price ${price:.2f} | target ACOS {target:.0%}\n"
                f"Last 30 days: {last30}\nPrevious 30 days: {prev30}\n"
                f"Anomalies: {anomalies}\nKeywords:\n{keyword_block}"
            ),
            fallback=fallback,
            model=services.cfg.chat_model,
        )

        recommendations = _normalize_recommendations(
            data.get("recommendations"), keywords, fallback_recs
        )
        backtest = _backtest(keywords, recommendations)
        report = {
            "sku_id": sku["sku_id"],
            "source": services.adapters.ads.name,
            "target_acos": target,
            "last_30d": last30,
            "previous_30d": prev30,
            "spend_delta": round(spend_delta, 3),
            "sales_delta": round(sales_delta, 3),
            "anomalies": anomalies,
            "diagnosis": data.get("diagnosis") or fallback["diagnosis"],
            "recommendations": recommendations,
            "backtest": backtest,
        }
        proposals = [
            {
                "action": "adjust_bid",
                "sku_id": sku["sku_id"],
                "keyword": rec["keyword"],
                "current_bid": rec["current_bid"],
                "proposed_bid": rec["proposed_bid"],
                "reason": rec["reason"],
            }
            for rec in recommendations
        ]
        return {
            "ads_report": report,
            "proposals": proposals,
            "metrics": update_metrics(
                state, "ads", started, usage, services.cfg.chat_model
            ),
        }

    return ads_node
