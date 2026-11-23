from __future__ import annotations

import time
from typing import Any

from agent.nodes.common import update_metrics
from agent.services import Services


def fallback_listing(sku: dict[str, Any], keywords: list[dict[str, Any]]) -> dict[str, Any]:
    title = sku["title"]
    if len(title) > 200:
        title = title[:197].rstrip() + "..."
    return {
        "title": title,
        "bullets": list(sku["bullets"])[:5],
        "description": sku["description"],
        "backend_keywords": [item["keyword"] for item in keywords[:8]],
        "rationale": "Rule-based fallback using the current listing and keyword bank.",
        "citations": [],
    }


def normalize_listing(
    data: dict[str, Any],
    sku: dict[str, Any],
    docs: list[dict[str, Any]],
) -> dict[str, Any]:
    title = str(data.get("title") or sku["title"]).strip()
    if len(title) > 200:
        title = title[:197].rstrip() + "..."

    raw_bullets = data.get("bullets") or sku["bullets"]
    if isinstance(raw_bullets, str):
        raw_bullets = [raw_bullets]
    bullets = [str(item).strip() for item in raw_bullets if str(item).strip()][:5]
    while len(bullets) < 5:
        bullets.append(sku["bullets"][len(bullets) % len(sku["bullets"])])

    description = str(data.get("description") or sku["description"]).strip()

    raw_backend = data.get("backend_keywords") or []
    if isinstance(raw_backend, str):
        raw_backend = [item.strip() for item in raw_backend.split(",")]
    backend = [str(item).strip() for item in raw_backend if str(item).strip()][:10]

    citations = data.get("citations") or []
    if isinstance(citations, str):
        citations = [citations]
    valid_ids = {doc["doc_id"] for doc in docs}
    citations = [item for item in citations if item in valid_ids]
    if not citations and docs:
        citations = [docs[0]["doc_id"]]

    return {
        "title": title,
        "bullets": bullets,
        "description": description,
        "backend_keywords": backend,
        "rationale": str(
            data.get("rationale")
            or "Generated from retrieved high-converting listings and policy evidence."
        ),
        "citations": citations,
    }


def make_listing_node(services: Services):
    def listing_node(state: dict[str, Any]) -> dict[str, Any]:
        started = time.perf_counter()
        sku = state["sku"]
        keywords = state.get("keywords") or []
        insights = state.get("insights") or {}

        query = f"{sku['title']} {sku['subcategory']} high converting listing"
        history_docs = services.retriever.search(
            query,
            top_k=4,
            doc_types=["historical_listing"],
            metadata_filter={"subcategory": sku["subcategory"]},
        )
        if not history_docs:
            history_docs = services.retriever.search(
                query, top_k=4, doc_types=["historical_listing"]
            )
        policy_docs = services.retriever.search(
            query, top_k=2, doc_types=["policy"]
        )
        docs = history_docs + policy_docs
        doc_block = "\n\n".join(
            f"[{doc['doc_id']}] {doc['title']}\n{doc['snippet']}" for doc in docs
        )
        keyword_block = ", ".join(item["keyword"] for item in keywords[:10])
        pain_block = ", ".join(
            item.get("theme", "") for item in insights.get("pain_points", [])[:3]
        )
        fallback = fallback_listing(sku, keywords)

        data, usage = services.llm.json(
            system=(
                "You are an Amazon listing copywriter. Write compliant US marketplace copy. "
                "Rules: title <= 200 characters; exactly 5 bullets; no prohibited claims "
                "(best seller, #1, Amazon's Choice, FDA approved, guaranteed, 100%, "
                "eco-friendly, non-toxic, BPA free, lifetime warranty, made in USA, "
                "free shipping, limited time); no URLs, emails, phone numbers, or emojis. "
                "Return JSON with title, bullets (list of 5 strings), description, "
                "backend_keywords (list), rationale, and citations (list of doc_id values used)."
            ),
            user=(
                f"SKU: {sku['sku_id']} | {sku['subcategory']} | {sku['marketplace']}\n"
                f"Current title: {sku['title']}\n"
                f"Attributes: {', '.join(sku['attributes'])}\n"
                f"Top keywords: {keyword_block}\n"
                f"Review pain points to address: {pain_block}\n\n"
                f"Retrieved evidence:\n{doc_block}\n\n"
                "Write the new listing. Cite evidence with doc_id values."
            ),
            fallback=fallback,
        )
        listing = normalize_listing(data, sku, docs)
        return {
            "draft_listing": listing,
            "retrieved_docs": docs,
            "metrics": update_metrics(
                state, "listing", started, usage, services.cfg.chat_model
            ),
        }

    return listing_node
