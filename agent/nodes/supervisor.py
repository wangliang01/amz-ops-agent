from __future__ import annotations

import time
from typing import Any

from agent.nodes.common import update_metrics
from agent.services import Services

VALID_MODES = {"full_chain", "listing_only", "ads_only"}


def make_supervisor_node(services: Services):
    def supervisor_node(state: dict[str, Any]) -> dict[str, Any]:
        started = time.perf_counter()
        sku_id = str(state.get("sku_id", "")).strip()
        mode = str(state.get("mode", "full_chain")).strip() or "full_chain"
        errors = list(state.get("errors") or [])

        try:
            sku = services.adapters.sp_api.get_catalog_item(sku_id)
        except KeyError as exc:
            errors.append(str(exc))
            return {
                "errors": errors,
                "metrics": update_metrics(state, "supervisor", started),
            }

        usage = None
        model = None
        if mode == "auto":
            fallback = {"mode": "full_chain", "reason": "default"}
            data, usage = services.llm.json(
                system=(
                    "You route an Amazon operations request to one of three modes: "
                    "full_chain (insight + listing + compliance + ads), "
                    "listing_only (insight + listing + compliance), "
                    "ads_only (ads diagnosis). Return JSON: "
                    '{"mode": "full_chain|listing_only|ads_only", "reason": "..."}'
                ),
                user=f"Request: {state.get('request', '')}\nSKU: {sku_id}",
                fallback=fallback,
                model=services.cfg.cheap_model,
            )
            model = services.cfg.cheap_model
            chosen = data.get("mode")
            mode = chosen if chosen in VALID_MODES else "full_chain"

        if mode not in VALID_MODES:
            errors.append(f"invalid mode: {mode}")
            mode = "full_chain"

        return {
            "sku": sku,
            "mode": mode,
            "reviews": services.store.reviews_for(sku_id),
            "keywords": services.store.keywords_for(sku_id),
            "errors": errors,
            "metrics": update_metrics(state, "supervisor", started, usage, model),
        }

    return supervisor_node
