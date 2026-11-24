"""Read-only Amazon Ads API boundary.

`MockAdsAPIAdapter` serves the simulated 90-day daily rows and keyword
performance from the seed. A real Ads API client implements the same Protocol;
the Ads node and Ops plan do not need to change.

Only reads are defined. Bid changes are still proposals that require approval
and are written as dry-run audit rows by the executor.
"""
from __future__ import annotations

import copy
from typing import Any, Protocol

from core.store import SeedStore


class AdsAPIAdapter(Protocol):
    name: str

    def get_daily_metrics(self, sku_id: str, days: int = 90) -> list[dict[str, Any]]: ...

    def get_keyword_performance(self, sku_id: str) -> list[dict[str, Any]]: ...


class MockAdsAPIAdapter:
    """Reuse the simulated ad seed as a stand-in for the Ads API."""

    name = "mock_ads_api"

    def __init__(self, store: SeedStore):
        self.store = store

    def get_daily_metrics(
        self, sku_id: str, days: int = 90
    ) -> list[dict[str, Any]]:
        self.store.sku(sku_id)
        return copy.deepcopy(self.store.ads_for(sku_id, days=days))

    def get_keyword_performance(self, sku_id: str) -> list[dict[str, Any]]:
        self.store.sku(sku_id)
        return copy.deepcopy(self.store.ad_keywords_for(sku_id))
