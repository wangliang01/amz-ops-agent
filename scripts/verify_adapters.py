from __future__ import annotations

import os

os.environ.setdefault("LLM_ENABLED", "false")
os.environ.setdefault("EMBEDDING_ENABLED", "false")

from agent.graph import build_graph  # noqa: E402
from agent.ops_plan import build_ops_plan  # noqa: E402
from agent.services import build_services  # noqa: E402
from integrations import Adapters, build_adapters  # noqa: E402


def check_mock(services) -> None:
    adapters = services.adapters
    description = adapters.describe()
    assert description["mode"] == "mock", description
    assert description["read_only"] is True, description
    assert description["sp_api"]["provider"] == "mock_sp_api", description
    assert description["ads_api"]["provider"] == "mock_ads_api", description
    assert "get_inventory" in description["sp_api"]["capabilities"], description
    assert "get_daily_metrics" in description["ads_api"]["capabilities"], description
    assert adapters.mode == "mock", adapters

    sku_id = "SKU-003"
    catalog = adapters.sp_api.get_catalog_item(sku_id)
    assert catalog == services.store.sku(sku_id), catalog

    inventory = adapters.sp_api.get_inventory(sku_id)
    assert inventory["source"] == "mock_sp_api", inventory
    assert inventory["on_hand"] == 95, inventory
    assert inventory["available"] == 95, inventory
    assert inventory["inbound"] == 0, inventory

    listing = adapters.sp_api.get_listing(sku_id)
    assert listing["sku_id"] == sku_id, listing
    assert listing["title"] == services.store.sku(sku_id)["current_listing"]["title"], (
        listing
    )

    rows = adapters.ads.get_daily_metrics(sku_id, days=90)
    assert len(rows) == 90, len(rows)
    first_spend = rows[0]["spend"]
    rows[0]["spend"] = -1.0
    again = adapters.ads.get_daily_metrics(sku_id, days=90)
    assert again[0]["spend"] == first_spend, "adapter must not expose mutable seed rows"

    keywords = adapters.ads.get_keyword_performance(sku_id)
    assert len(keywords) == len(services.store.ad_keywords_for(sku_id)), len(keywords)

    for call in (
        lambda: adapters.sp_api.get_catalog_item("SKU-404"),
        lambda: adapters.sp_api.get_inventory("SKU-404"),
        lambda: adapters.sp_api.get_listing("SKU-404"),
        lambda: adapters.ads.get_daily_metrics("SKU-404"),
        lambda: adapters.ads.get_keyword_performance("SKU-404"),
    ):
        try:
            call()
        except KeyError:
            pass
        else:
            raise AssertionError("unknown SKU must raise KeyError")

    try:
        build_adapters(services.store, "real")
    except ValueError:
        pass
    else:
        raise AssertionError("unknown adapter mode must fail loudly")


class FakeSPAPI:
    name = "fake_sp_api"

    def __init__(self, store):
        self.store = store

    def get_catalog_item(self, sku_id):
        return self.store.sku(sku_id)

    def get_inventory(self, sku_id):
        return {
            "sku_id": sku_id,
            "on_hand": 500,
            "available": 500,
            "inbound": 25,
            "source": self.name,
        }

    def get_listing(self, sku_id):
        return {"sku_id": sku_id, "source": self.name}


class FakeAdsAPI:
    name = "fake_ads_api"

    def __init__(self, store):
        self.store = store
        self.calls: list[tuple[str, int]] = []

    def get_daily_metrics(self, sku_id, days=90):
        self.calls.append((sku_id, days))
        return [
            {
                "spend": 10.0,
                "sales": 100.0,
                "clicks": 10,
                "impressions": 1000,
            }
            for _ in range(30)
        ]

    def get_keyword_performance(self, sku_id):
        self.calls.append((sku_id, 0))
        return []


def check_swap(services) -> None:
    fake_sp = FakeSPAPI(services.store)
    fake_ads = FakeAdsAPI(services.store)
    fake = Adapters(mode="fake", sp_api=fake_sp, ads=fake_ads)
    sku = services.store.sku("SKU-003")
    plan = build_ops_plan(services.store, sku, adapters=fake)
    assert plan["adapter_mode"] == "fake", plan["adapter_mode"]
    assert plan["inventory"]["on_hand"] == 500, plan["inventory"]
    assert plan["inventory"]["inbound"] == 25, plan["inventory"]
    assert plan["budget"]["spend_30d"] == 300.0, plan["budget"]
    assert plan["budget"]["sales_30d"] == 3000.0, plan["budget"]
    assert fake_ads.calls, "fake ads adapter was not used"


def check_graph(services) -> None:
    graph = build_graph(services)
    run_id = "verify-adapters"
    config = {"configurable": {"thread_id": run_id}}
    graph.invoke(
        {
            "run_id": run_id,
            "thread_id": run_id,
            "sku_id": "SKU-003",
            "mode": "full_chain",
            "request": "verify adapters",
            "approval": None,
            "metrics": {},
            "errors": [],
        },
        config,
    )
    snapshot = graph.get_state(config)
    assert list(snapshot.next) == ["executor"], snapshot.next
    state = dict(snapshot.values or {})
    assert (state.get("ads_report") or {}).get("source") == "mock_ads_api", (
        state.get("ads_report")
    )
    plan = state.get("ops_plan") or {}
    assert plan.get("adapter_mode") == "mock", plan
    assert plan["inventory"]["source"] == "mock_sp_api", plan["inventory"]
    assert plan["adapter_sources"]["read_only"] is True, plan["adapter_sources"]
    graph.update_state(
        config,
        {"approval": {"decision": "approved", "actor": "verify-adapters", "note": None}},
    )
    graph.invoke(None, config)
    state = dict(graph.get_state(config).values or {})
    logs = state.get("execution_log") or []
    assert len(logs) == 5, len(logs)
    assert all(item.get("status") == "dry_run_success" for item in logs), logs


def main() -> int:
    services = build_services()
    check_mock(services)
    check_swap(services)
    check_graph(services)
    print(
        "ADAPTERS_VERIFY_OK "
        "sp=mock_sp_api ads=mock_ads_api read_only=yes "
        "inventory=95 daily_rows=90 fake_swap=ok execution=5_dry_run"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
