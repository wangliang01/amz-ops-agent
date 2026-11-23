from __future__ import annotations

import time
from typing import Any

from core.llm import Usage, estimate_cost


def update_metrics(
    state: dict[str, Any],
    node: str,
    started: float,
    usage: Usage | None = None,
    model: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    metrics = dict(state.get("metrics") or {})
    node_times = dict(metrics.get("node_times") or {})
    node_times[node] = round(time.perf_counter() - started, 2)
    metrics["node_times"] = node_times

    tokens = dict(metrics.get("tokens") or {"prompt": 0, "completion": 0, "total": 0})
    if usage is not None:
        tokens["prompt"] = int(tokens.get("prompt", 0)) + usage.prompt_tokens
        tokens["completion"] = int(tokens.get("completion", 0)) + usage.completion_tokens
        tokens["total"] = int(tokens.get("total", 0)) + usage.total_tokens
        metrics["llm_calls"] = int(metrics.get("llm_calls", 0)) + usage.calls
        metrics["cost_usd"] = round(
            float(metrics.get("cost_usd", 0.0)) + estimate_cost(usage, model or ""),
            6,
        )
    metrics["tokens"] = tokens
    metrics.update(extra)
    return metrics


def truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."
