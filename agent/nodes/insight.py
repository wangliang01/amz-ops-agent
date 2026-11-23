from __future__ import annotations

import time
from typing import Any

from agent.nodes.common import update_metrics
from agent.services import Services

PAIN_PATTERNS = {
    "leaks": ["leak", "leaking", "spill"],
    "battery life": ["battery", "charge", "charging", "dies"],
    "hard to clean": ["clean", "cleaning", "residue", "scrub"],
    "noise": ["loud", "noise", "wakes"],
    "blending power": ["ice", "chunk", "blend", "motor", "weak"],
    "durability": ["broke", "broken", "crack", "stopped working", "falling apart"],
    "size/fit": ["small", "size", "capacity", "fit"],
    "quality": ["cheap", "flimsy", "quality", "scratched"],
}

POSITIVE_PATTERNS = {
    "portability": ["portable", "travel", "gym", "bag"],
    "ease of use": ["easy", "simple", "quick", "one button"],
    "value": ["value", "price", "worth", "quality"],
    "performance": ["works", "great", "perfect", "good"],
}


def _haystack(review: dict[str, Any]) -> str:
    return f"{review.get('title', '')} {review.get('text', '')}".lower()


def rule_based_insights(reviews: list[dict[str, Any]]) -> dict[str, Any]:
    negatives = [r for r in reviews if int(r.get("rating", 5)) <= 3]
    positives = [r for r in reviews if int(r.get("rating", 5)) >= 4]

    pain_points = []
    for theme, keys in PAIN_PATTERNS.items():
        matches = [r for r in negatives if any(k in _haystack(r) for k in keys)]
        if matches:
            quotes: list[str] = []
            for match in matches:
                quote = f"{match.get('title', '')}: {match.get('text', '')}"
                if quote not in quotes:
                    quotes.append(quote)
                if len(quotes) == 2:
                    break
            pain_points.append(
                {
                    "theme": theme,
                    "frequency": len(matches),
                    "quotes": quotes,
                }
            )
    pain_points.sort(key=lambda item: -item["frequency"])

    positive_themes = []
    for theme, keys in POSITIVE_PATTERNS.items():
        mentions = sum(1 for r in positives if any(k in _haystack(r) for k in keys))
        if mentions:
            positive_themes.append({"theme": theme, "mentions": mentions})
    positive_themes.sort(key=lambda item: -item["mentions"])

    gaps = [
        f"Address '{item['theme']}' complaints with a clearer claim or design note."
        for item in pain_points[:3]
    ]
    top = pain_points[0]["theme"] if pain_points else "none"
    return {
        "summary": (
            f"{len(reviews)} reviews analyzed. Top complaint: {top}. "
            f"Negative share: {round(len(negatives) / len(reviews), 3) if reviews else 0}."
        ),
        "pain_points": pain_points[:5],
        "positive_themes": positive_themes[:4],
        "competitor_gaps": gaps,
        "review_count": len(reviews),
        "negative_share": round(len(negatives) / len(reviews), 3) if reviews else 0,
    }


def make_insight_node(services: Services):
    def insight_node(state: dict[str, Any]) -> dict[str, Any]:
        started = time.perf_counter()
        reviews = list(state.get("reviews") or [])
        fallback = rule_based_insights(reviews)
        sample = "\n".join(
            f"[{r['review_id']}] {r['rating']} stars - {r['title']}: {r['text']}"
            for r in reviews[:30]
        )
        data, usage = services.llm.json(
            system=(
                "You are an Amazon review analyst. Analyze the reviews and return JSON with "
                "summary (string), pain_points (list of {theme, frequency, quotes}), "
                "positive_themes (list of {theme, mentions}), and competitor_gaps "
                "(list of strings). Use only evidence from the reviews."
            ),
            user=f"SKU: {state.get('sku_id', '')}\nReviews:\n{sample}",
            fallback=fallback,
            model=services.cfg.cheap_model,
        )
        if not isinstance(data.get("pain_points"), list):
            data = fallback
        data.setdefault("review_count", len(reviews))
        return {
            "insights": data,
            "metrics": update_metrics(
                state, "insight", started, usage, services.cfg.cheap_model
            ),
        }

    return insight_node
