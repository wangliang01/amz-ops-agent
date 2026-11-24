"""Adapter assembly for the demo.

`ADAPTER_MODE=mock` is the only registered mode. Real SP-API / Ads API clients
can be added here later; they must implement the read-only Protocols.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.store import SeedStore
from integrations.ads_api import AdsAPIAdapter, MockAdsAPIAdapter
from integrations.sp_api import MockSPAPIAdapter, SPAPIAdapter

SP_CAPABILITIES = ["get_catalog_item", "get_inventory", "get_listing"]
ADS_CAPABILITIES = ["get_daily_metrics", "get_keyword_performance"]


@dataclass(frozen=True)
class Adapters:
    mode: str
    sp_api: SPAPIAdapter
    ads: AdsAPIAdapter

    def describe(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "read_only": True,
            "sp_api": {
                "provider": self.sp_api.name,
                "capabilities": SP_CAPABILITIES,
            },
            "ads_api": {
                "provider": self.ads.name,
                "capabilities": ADS_CAPABILITIES,
            },
        }


def build_adapters(store: SeedStore, mode: str | None = None) -> Adapters:
    selected = (mode or "mock").strip().lower() or "mock"
    if selected != "mock":
        raise ValueError(
            f"unknown adapter mode: {selected}; available modes: mock"
        )
    return Adapters(
        mode="mock",
        sp_api=MockSPAPIAdapter(store),
        ads=MockAdsAPIAdapter(store),
    )
