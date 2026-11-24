from __future__ import annotations

import copy
import json
import os

os.environ.setdefault("LLM_ENABLED", "false")
os.environ.setdefault("EMBEDDING_ENABLED", "false")

from agent.creative import (  # noqa: E402
    build_creative_brief,
    get_provider,
    review_creative,
)
from agent.graph import build_graph  # noqa: E402
from agent.nodes.insight import rule_based_insights  # noqa: E402
from agent.services import build_services  # noqa: E402


def check_brief(services) -> tuple[dict, list[dict], dict]:
    sku = services.store.sku("SKU-003")
    reviews = services.store.reviews_for("SKU-003")
    insights = rule_based_insights(reviews)
    first = build_creative_brief(
        sku, insights, {"title": "draft"}, reviews, services.store.compliance_rules
    )
    second = build_creative_brief(
        sku, insights, {"title": "draft"}, reviews, services.store.compliance_rules
    )
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True), (
        "brief not deterministic"
    )

    assets = first["assets"]
    assert [item["slot"] for item in assets] == [
        "hero",
        "lifestyle",
        "detail",
        "comparison",
        "aplus",
    ], assets
    hero = assets[0]
    assert hero["overlay_text"] is None, hero
    assert all(item["evidence"] for item in assets), assets
    assert all(item["must_show"] for item in assets), assets

    provider = get_provider("mock")
    generated = provider.generate(first, sku)
    assert provider.name == "mock", provider.name
    assert all(item["provider"] == "mock" for item in generated), generated
    assert all(item["rendered"] is False for item in generated), generated
    assert all(item["asset_url"] is None for item in generated), generated

    review = review_creative(
        generated, first, services.store.compliance_rules, provider.name
    )
    assert review["passed"] is True, review
    assert review["score"] == 100.0, review["score"]
    assert review["block_count"] == 0, review
    assert len(review["dimensions"]) == 5, review["dimensions"]
    assert any(
        item["severity"] == "info" and "像素级" in item["message"]
        for item in review["findings"]
    ), review["findings"]
    return first, generated, review


def check_negative_control(
    services, brief: dict, assets: list[dict], baseline: float
) -> None:
    broken = copy.deepcopy(assets)
    broken[1]["overlay_text"] = "Best Seller #1"
    review = review_creative(
        broken, brief, services.store.compliance_rules, "mock"
    )
    assert review["passed"] is False, review
    assert review["block_count"] >= 1, review
    assert review["score"] < baseline, (review["score"], baseline)
    assert any(item["dimension"] == "policy" for item in review["findings"]), review


def check_all_skus(services) -> None:
    provider = get_provider("mock")
    for sku in services.store.skus.values():
        reviews = services.store.reviews_for(sku["sku_id"])
        brief = build_creative_brief(
            sku,
            rule_based_insights(reviews),
            {},
            reviews,
            services.store.compliance_rules,
        )
        assets = provider.generate(brief, sku)
        review = review_creative(
            assets, brief, services.store.compliance_rules, provider.name
        )
        assert len(assets) == 5, (sku["sku_id"], assets)
        assert review["passed"] is True, (sku["sku_id"], review)
        assert all(item["evidence"] for item in assets), sku["sku_id"]


def invoke(services, mode: str, run_id: str):
    graph = build_graph(services)
    config = {"configurable": {"thread_id": run_id}}
    graph.invoke(
        {
            "run_id": run_id,
            "thread_id": run_id,
            "sku_id": "SKU-003",
            "mode": mode,
            "request": "verify creative",
            "approval": None,
            "metrics": {},
            "errors": [],
        },
        config,
    )
    snapshot = graph.get_state(config)
    return graph, config, snapshot


def check_graph(services) -> None:
    graph, config, snapshot = invoke(services, "full_chain", "verify-creative-full")
    assert list(snapshot.next) == ["executor"], snapshot.next
    state = dict(snapshot.values or {})
    assert state["creative_brief"]["assets"], state.get("creative_brief")
    assert len(state["creative_assets"]) == 5, state.get("creative_assets")
    assert state["creative_review"]["passed"] is True, state.get("creative_review")
    assert "creative" in (state.get("metrics") or {}).get("node_times", {}), state["metrics"]
    graph.update_state(
        config,
        {"approval": {"decision": "approved", "actor": "verify-creative", "note": None}},
    )
    graph.invoke(None, config)
    state = dict(graph.get_state(config).values or {})
    logs = state.get("execution_log") or []
    assert len(logs) == 5, len(logs)
    assert all(item.get("status") == "dry_run_success" for item in logs), logs

    for mode in ("listing_only", "ads_only"):
        _, _, snapshot = invoke(services, mode, f"verify-creative-{mode}")
        assert list(snapshot.next) == ["executor"], (mode, snapshot.next)
        state = dict(snapshot.values or {})
        assert not state.get("creative_review"), (mode, state.get("creative_review"))
        assert "creative" not in (state.get("metrics") or {}).get("node_times", {}), (
            mode,
            state.get("metrics"),
        )


def main() -> int:
    services = build_services()
    brief, assets, review = check_brief(services)
    check_all_skus(services)
    check_negative_control(services, brief, assets, float(review["score"]))
    check_graph(services)
    print(
        "CREATIVE_VERIFY_OK "
        f"slots={len(assets)} score={review['score']} provider={review['provider']} "
        "negative_control=blocked execution=5_dry_run"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
