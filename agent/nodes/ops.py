from __future__ import annotations

import time
from typing import Any

from agent.nodes.common import update_metrics
from agent.ops_plan import build_ops_plan
from agent.services import Services


def make_ops_node(services: Services):
    def ops_node(state: dict[str, Any]) -> dict[str, Any]:
        started = time.perf_counter()
        plan = build_ops_plan(
            services.store,
            state["sku"],
            ads_report=state.get("ads_report"),
            compliance_report=state.get("compliance_report"),
            metrics=state.get("metrics"),
            adapters=services.adapters,
        )
        return {
            "ops_plan": plan,
            "metrics": update_metrics(state, "ops", started),
        }

    return ops_node
