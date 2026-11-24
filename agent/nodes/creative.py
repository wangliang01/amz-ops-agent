from __future__ import annotations

import time
from typing import Any

from agent.creative import (
    build_creative_brief,
    get_provider,
    review_creative,
)
from agent.nodes.common import update_metrics
from agent.services import Services


def make_creative_node(services: Services):
    def creative_node(state: dict[str, Any]) -> dict[str, Any]:
        started = time.perf_counter()
        sku = state["sku"]
        brief = build_creative_brief(
            sku,
            state.get("insights") or {},
            state.get("draft_listing") or {},
            state.get("reviews") or [],
            services.store.compliance_rules,
        )
        provider = get_provider(services.cfg.creative_provider)
        assets = provider.generate(brief, sku)
        review = review_creative(
            assets,
            brief,
            services.store.compliance_rules,
            provider_name=provider.name,
        )
        return {
            "creative_brief": brief,
            "creative_assets": assets,
            "creative_review": review,
            "metrics": update_metrics(
                state,
                "creative",
                started,
                creative_provider=provider.name,
                creative_score=review["score"],
            ),
        }

    return creative_node
