from __future__ import annotations

import json
from collections import defaultdict
from typing import Any

import pandas as pd

from core.config import Settings, settings as default_settings


class SeedStore:
    """Read-only access to the seed dataset (real public reviews + simulated ads)."""

    def __init__(self, cfg: Settings = default_settings):
        self.cfg = cfg
        seed = cfg.data_dir

        self.skus = {
            item["sku_id"]: item
            for item in json.loads((seed / "skus.json").read_text(encoding="utf-8"))
        }

        self.reviews: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for line in (seed / "reviews.jsonl").read_text(encoding="utf-8").splitlines():
            if line.strip():
                item = json.loads(line)
                self.reviews[item["sku_id"]].append(item)

        self.keyword_bank = {
            item["sku_id"]: item["keywords"]
            for item in json.loads((seed / "keyword_bank.json").read_text(encoding="utf-8"))
        }
        self.compliance_rules = json.loads(
            (seed / "compliance_rules.json").read_text(encoding="utf-8")
        )
        self.ads_keywords = json.loads(
            (seed / "ads_keywords.json").read_text(encoding="utf-8")
        )
        self.ads_daily = pd.read_csv(seed / "ads_daily.csv")
        self.historical_listings: list[dict[str, Any]] = [
            json.loads(line)
            for line in (seed / "historical_listings.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        ]

    def sku(self, sku_id: str) -> dict[str, Any]:
        if sku_id not in self.skus:
            raise KeyError(f"unknown sku: {sku_id}")
        return self.skus[sku_id]

    def reviews_for(self, sku_id: str) -> list[dict[str, Any]]:
        return list(self.reviews.get(sku_id, []))

    def keywords_for(self, sku_id: str) -> list[dict[str, Any]]:
        return list(self.keyword_bank.get(sku_id, []))

    def ads_for(self, sku_id: str, days: int = 90) -> list[dict[str, Any]]:
        df = self.ads_daily[self.ads_daily["sku_id"] == sku_id].tail(days)
        return df.to_dict(orient="records")

    def ad_keywords_for(self, sku_id: str) -> list[dict[str, Any]]:
        return [row for row in self.ads_keywords if row["sku_id"] == sku_id]
