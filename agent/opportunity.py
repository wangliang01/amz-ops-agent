"""Deterministic product-opportunity ranking for the demo portfolio.

Real inputs: product rating, review count, review text and dates, price, and
the public historical listings. Simulated inputs: unit cost (used for the
margin component) and any competition proxy derived from the small historical
sample. Every item marks which components are simulated.

The ranking is a transparent weighted score, not a model prediction. It stays
deterministic so the demo and the verification script can assert on it.
"""
from __future__ import annotations

import math
from typing import Any

from core.store import SeedStore

WEIGHTS = {
    "demand": 0.30,
    "rating": 0.20,
    "pain": 0.25,
    "competition": 0.15,
    "margin": 0.10,
}

PAIN_TERMS = (
    "broke",
    "broken",
    "cheap",
    "flimsy",
    "irritat",
    "rash",
    "burn",
    "waste",
    "didn't work",
    "doesn't work",
    "did not work",
    "no difference",
    "no results",
    "smell",
    "peel",
    "fall off",
    "slip",
    "small",
    "fit",
    "weak",
    "damaged",
    "expensive",
    "not worth",
    "useless",
)

SIMULATED_COMPONENTS = ("margin",)


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _has_pain(review: dict[str, Any]) -> bool:
    text = f"{review.get('title', '')} {review.get('text', '')}".lower()
    return any(term in text for term in PAIN_TERMS)


def _evidence(reviews: list[dict[str, Any]]) -> list[dict[str, Any]]:
    negatives = [
        review for review in reviews if int(review.get("rating") or 5) <= 2
    ]
    pool = [review for review in negatives if _has_pain(review)] or negatives
    pool.sort(
        key=lambda review: (
            int(review.get("rating") or 5),
            -len(str(review.get("text") or "")),
            str(review.get("review_id") or ""),
        )
    )
    out = []
    for review in pool[:2]:
        out.append(
            {
                "review_id": review.get("review_id"),
                "rating": review.get("rating"),
                "date": review.get("date"),
                "quote": str(review.get("text") or "")[:180].strip(),
            }
        )
    return out


def _pain_share(reviews: list[dict[str, Any]]) -> float:
    if not reviews:
        return 0.0
    negatives = sum(1 for review in reviews if int(review.get("rating") or 5) <= 2)
    with_pain = sum(1 for review in reviews if _has_pain(review))
    return _clamp((0.6 * negatives + 0.4 * with_pain) / len(reviews))


def rank_opportunities(store: SeedStore) -> dict[str, Any]:
    skus = list(store.skus.values())
    historical = store.historical_listings
    competition_reviews: dict[str, int] = {}
    for listing in historical:
        subcategory = str(listing.get("subcategory") or "")
        competition_reviews[subcategory] = competition_reviews.get(subcategory, 0) + int(
            listing.get("review_count") or 0
        )

    max_reviews = max((int(sku.get("review_count") or 0) for sku in skus), default=1)
    max_competition = max(competition_reviews.values(), default=0)
    max_margin = max(
        (
            (float(sku.get("price") or 0) - float(sku.get("cost") or 0))
            / float(sku.get("price") or 1)
            for sku in skus
        ),
        default=1.0,
    )

    items: list[dict[str, Any]] = []
    for sku in skus:
        sku_id = str(sku["sku_id"])
        reviews = store.reviews_for(sku_id)
        price = float(sku.get("price") or 0)
        cost = float(sku.get("cost") or 0)
        margin = (price - cost) / price if price else 0.0
        competition = competition_reviews.get(str(sku.get("subcategory") or ""), 0)

        components = {
            "demand": _clamp(
                math.log1p(int(sku.get("review_count") or 0)) / math.log1p(max_reviews)
            ),
            "rating": _clamp(float(sku.get("rating") or 0) / 5.0),
            "pain": _pain_share(reviews),
            "competition": _clamp(
                1.0
                - math.log1p(competition) / math.log1p(max_competition)
                if max_competition
                else 1.0
            ),
            "margin": _clamp(margin / max(max_margin, 1e-9)),
        }
        score = round(
            100.0
            * sum(WEIGHTS[name] * value for name, value in components.items()),
            1,
        )
        drivers = [
            {
                "name": name,
                "weight": WEIGHTS[name],
                "value": round(components[name], 3),
                "contribution": round(WEIGHTS[name] * components[name] * 100, 1),
            }
            for name in WEIGHTS
        ]
        drivers.sort(key=lambda item: -item["contribution"])
        items.append(
            {
                "sku_id": sku_id,
                "title": sku.get("title"),
                "subcategory": sku.get("subcategory"),
                "price": price,
                "rating": sku.get("rating"),
                "review_count": sku.get("review_count"),
                "score": score,
                "components": {name: round(value, 3) for name, value in components.items()},
                "drivers": drivers,
                "evidence": _evidence(reviews),
                "simulated_components": list(SIMULATED_COMPONENTS),
            }
        )

    items.sort(key=lambda item: (-item["score"], item["sku_id"]))
    for rank, item in enumerate(items, start=1):
        item["rank"] = rank

    return {
        "weights": WEIGHTS,
        "source": {
            "products": len(skus),
            "reviews": sum(len(store.reviews_for(str(sku["sku_id"]))) for sku in skus),
            "historical_listings": len(historical),
            "real_inputs": [
                "rating",
                "review_count",
                "review_text",
                "price",
                "subcategory",
                "historical_listing_review_count",
            ],
            "simulated_inputs": ["cost"],
        },
        "items": items,
    }
