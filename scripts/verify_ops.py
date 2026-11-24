from __future__ import annotations

import json
import os

os.environ.setdefault("LLM_ENABLED", "false")
os.environ.setdefault("EMBEDDING_ENABLED", "false")

from agent.graph import build_graph  # noqa: E402
from agent.opportunity import rank_opportunities  # noqa: E402
from agent.ops_plan import build_ops_plan  # noqa: E402
from agent.services import build_services  # noqa: E402


def check_opportunities(store) -> dict:
    first = rank_opportunities(store)
    second = rank_opportunities(store)
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True), "not deterministic"
    items = first["items"]
    assert len(items) == 5, len(items)
    assert [item["rank"] for item in items] == [1, 2, 3, 4, 5], items
    scores = [float(item["score"]) for item in items]
    assert scores == sorted(scores, reverse=True), scores
    for item in items:
        assert 0 <= float(item["score"]) <= 100, item["score"]
        assert len(item["drivers"]) >= 3, item
        assert len(item["evidence"]) >= 1, item["sku_id"]
        assert item["components"]["pain"] >= 0, item
    return first


def check_plans(store) -> None:
    for sku in store.skus.values():
        plan = build_ops_plan(store, sku)
        assert plan["simulated"] is True, plan
        assert plan["adapter_mode"] == "mock", plan
        assert plan["adapter_sources"]["read_only"] is True, plan
        inventory = plan["inventory"]
        assert inventory["reorder_point"] >= 0, inventory
        assert inventory["reorder_qty"] >= 0, inventory
        price = plan["price_guardrail"]
        assert price["floor_price"] <= price["ceiling_price"], price
        assert plan["budget"]["proposed_daily_budget"] >= 0, plan["budget"]
        assert plan["assumptions"], plan
        assert any(item["simulated"] for item in plan["assumptions"]), plan


def check_graph(services) -> None:
    graph = build_graph(services)
    run_id = "verify-ops"
    config = {"configurable": {"thread_id": run_id}}
    initial = {
        "run_id": run_id,
        "thread_id": run_id,
        "sku_id": "SKU-003",
        "mode": "full_chain",
        "request": "verify ops plan",
        "approval": None,
        "metrics": {},
        "errors": [],
    }
    graph.invoke(initial, config)
    snapshot = graph.get_state(config)
    assert list(snapshot.next) == ["executor"], snapshot.next
    state = dict(snapshot.values or {})
    plan = state.get("ops_plan") or {}
    assert plan.get("sku_id") == "SKU-003", plan
    assert plan.get("simulated") is True, plan
    assert plan["roi"]["human_minutes_saved"] > 0, plan["roi"]
    graph.update_state(
        config,
        {"approval": {"decision": "approved", "actor": "verify-ops", "note": None}},
    )
    graph.invoke(None, config)
    snapshot = graph.get_state(config)
    state = dict(snapshot.values or {})
    logs = state.get("execution_log") or []
    assert len(logs) == 5, len(logs)
    assert all(item.get("status") == "dry_run_success" for item in logs), logs


def main() -> int:
    services = build_services()
    opportunities = check_opportunities(services.store)
    check_plans(services.store)
    check_graph(services)
    top = opportunities["items"][0]
    print(
        "OPS_VERIFY_OK "
        f"skus={len(opportunities['items'])} "
        f"top={top['sku_id']}:{top['score']} "
        f"drivers={len(top['drivers'])} evidence={len(top['evidence'])} "
        "execution=5_dry_run"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
