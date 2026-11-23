"""Compact end-to-end smoke test for the demo pipeline."""
from __future__ import annotations

import json
import time
import uuid

from agent.graph import build_graph
from agent.services import build_services
from core import db


def main() -> None:
    db.init_db()
    services = build_services()
    graph = build_graph(services)

    run_id = f"smoke-{uuid.uuid4().hex[:6]}"
    config = {"configurable": {"thread_id": run_id}}
    graph.invoke(
        {
            "run_id": run_id,
            "thread_id": run_id,
            "sku_id": "SKU-003",
            "mode": "full_chain",
            "request": "Smoke test",
            "approval": None,
            "metrics": {"started_at": time.time()},
            "errors": [],
        },
        config,
    )
    state = dict(graph.get_state(config).values)

    if graph.get_state(config).next:
        graph.update_state(config, {"approval": {"decision": "approved", "actor": "smoke"}})
        graph.invoke(None, config)
        state = dict(graph.get_state(config).values)

    insights = state.get("insights") or {}
    listing = state.get("draft_listing") or {}
    compliance = state.get("compliance_report") or {}
    ads = state.get("ads_report") or {}
    metrics = state.get("metrics") or {}
    docs = state.get("retrieved_docs") or []

    summary = {
        "run_id": run_id,
        "errors": state.get("errors"),
        "insight": {
            "top_pain": [item["theme"] for item in insights.get("pain_points", [])[:3]],
            "negative_share": insights.get("negative_share"),
        },
        "listing": {
            "title_len": len(listing.get("title", "")),
            "bullets": len(listing.get("bullets", [])),
            "citations": listing.get("citations"),
        },
        "compliance": {
            "passed": compliance.get("passed"),
            "score": compliance.get("score"),
            "draft_issues": len(compliance.get("draft_issues", [])),
            "current_issues": len(compliance.get("current_listing_issues", [])),
            "fixed_count": compliance.get("fixed_count"),
        },
        "ads": {
            "last30_acos": (ads.get("last_30d") or {}).get("acos"),
            "anomalies": [item["type"] for item in ads.get("anomalies", [])],
            "recommendations": len(ads.get("recommendations", [])),
            "backtest_baseline": (ads.get("backtest") or {}).get("baseline"),
            "backtest_projected": (ads.get("backtest") or {}).get("projected"),
        },
        "execution_actions": len(state.get("execution_log") or []),
        "retrieved_docs": [doc.get("doc_id") for doc in docs],
        "metrics": {
            "pipeline_sec": metrics.get("pipeline_sec"),
            "wall_clock_sec": metrics.get("wall_clock_sec"),
            "approval_wait_sec": metrics.get("approval_wait_sec"),
            "tokens": metrics.get("tokens"),
            "cost_usd": metrics.get("cost_usd"),
            "llm_calls": metrics.get("llm_calls"),
        },
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
