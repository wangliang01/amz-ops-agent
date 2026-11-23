from __future__ import annotations

from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    run_id: str
    thread_id: str
    sku_id: str
    mode: str
    request: str

    sku: dict[str, Any]
    reviews: list[dict[str, Any]]
    keywords: list[dict[str, Any]]

    insights: dict[str, Any]
    retrieved_docs: list[dict[str, Any]]
    draft_listing: dict[str, Any]
    compliance_report: dict[str, Any]
    ads_report: dict[str, Any]

    proposals: list[dict[str, Any]]
    approval: dict[str, Any] | None
    execution_log: list[dict[str, Any]]

    metrics: dict[str, Any]
    errors: list[str]
