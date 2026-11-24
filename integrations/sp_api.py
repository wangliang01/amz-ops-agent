"""Read-only SP-API boundary.

The demo does not call Amazon. `MockSPAPIAdapter` reads the seed store and
returns SP-API-shaped data, so a real client can replace it without changing
nodes, API snapshots or the UI.

No write methods are defined here. Listing and inventory changes stay behind
the approval gate and the dry-run executor.
"""
from __future__ import annotations

import copy
from typing import Any, Protocol

from core.store import SeedStore


class SPAPIAdapter(Protocol):
    name: str

    def get_catalog_item(self, sku_id: str) -> dict[str, Any]: ...

    def get_inventory(self, sku_id: str) -> dict[str, Any]: ...

    def get_listing(self, sku_id: str) -> dict[str, Any]: ...


class MockSPAPIAdapter:
    """Reuse the public seed as a stand-in for SP-API catalog/inventory."""

    name = "mock_sp_api"

    def __init__(self, store: SeedStore):
        self.store = store

    def get_catalog_item(self, sku_id: str) -> dict[str, Any]:
        return copy.deepcopy(self.store.sku(sku_id))

    def get_inventory(self, sku_id: str) -> dict[str, Any]:
        sku = self.store.sku(sku_id)
        on_hand = int(sku.get("stock") or 0)
        return {
            "sku_id": str(sku_id),
            "on_hand": on_hand,
            "available": on_hand,
            "inbound": 0,
            "source": self.name,
        }

    def get_listing(self, sku_id: str) -> dict[str, Any]:
        sku = self.store.sku(sku_id)
        listing = copy.deepcopy(sku.get("current_listing") or {})
        listing["sku_id"] = str(sku_id)
        listing["source"] = self.name
        return listing
