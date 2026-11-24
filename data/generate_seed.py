"""Synthetic fallback seed generator for the amz-ops-agent demo.

The canonical seed is now built from the public Amazon Reviews 2023 dataset by
`data/fetch_real_seed.py`. This module is kept as a deterministic offline
fallback: it refuses to overwrite a real-data seed unless `--force-synthetic`
is passed explicitly.
"""
from __future__ import annotations

import csv
import json
import random
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "data" / "seed"
POLICIES = SEED / "policies"
TODAY = date(2026, 11, 23)
RNG = random.Random(42)

SKUS = [
    {
        "sku_id": "SKU-001",
        "asin": "B0DEMO001",
        "brand": "NordicHome",
        "title": "NordicHome Double-Wall Stainless Steel French Press, 34 oz Insulated Coffee Maker with 4-Level Filtration",
        "category": "Kitchen & Dining",
        "subcategory": "Coffee Makers",
        "marketplace": "US",
        "price": 32.99,
        "cost": 11.50,
        "stock": 180,
        "rating": 4.4,
        "review_count": 1280,
        "target_acos": 0.30,
        "current_bid": 0.85,
        "attributes": ["34 oz", "double-wall insulation", "4-level filtration", "18/10 stainless steel"],
        "benefits": [
            "keeps coffee hot for hours",
            "clean cup without grit",
            "brews four cups at once",
            "rust-resistant and dishwasher safe",
        ],
        "bullets": [
            "KEEPS COFFEE HOT LONGER: Double-wall vacuum insulation holds heat while the outer wall stays cool.",
            "CLEAN CUP, NO GRIT: Four-level filtration uses two stainless steel screens and a spring-loaded plunger.",
            "BREWS FOR A CROWD: 34 oz capacity makes four cups at once, ideal for sharing or a second round.",
            "BUILT TO LAST: 18/10 stainless steel resists rust and is dishwasher safe.",
            "SIMPLE FOUR-MINUTE BREW: Add coarse grounds, pour hot water, wait, and press.",
        ],
        "description": (
            "Brew a clean, full-bodied cup without paper filters. The double-wall body keeps coffee hot "
            "while the four-level filtration keeps grit out of the cup."
        ),
        "review_profile": "generic",
    },
    {
        "sku_id": "SKU-002",
        "asin": "B0DEMO002",
        "brand": "NordicHome",
        "title": "NordicHome Silicone Baking Mat Set, 3-Piece Non-Stick Oven Liner for Cookies, Pastry and Roasting",
        "category": "Kitchen & Dining",
        "subcategory": "Bakeware",
        "marketplace": "US",
        "price": 24.99,
        "cost": 7.80,
        "stock": 240,
        "rating": 4.5,
        "review_count": 960,
        "target_acos": 0.28,
        "current_bid": 0.70,
        "attributes": ["3-piece set", "food-grade silicone", "non-stick", "heat resistant to 450F"],
        "benefits": [
            "releases food without spray",
            "replaces parchment paper",
            "fits standard baking pans",
            "easy to clean",
        ],
        "bullets": [
            "NON-STICK WITHOUT SPRAY: Food-grade silicone releases cookies, pastry, and roasted vegetables cleanly.",
            "REUSABLE AND MONEY-SAVING: Replaces parchment paper and aluminum foil for everyday baking.",
            "FITS STANDARD PANS: 3-piece set fits half-sheet and quarter-sheet baking pans.",
            "EASY TO CLEAN: Wipe with warm soapy water or place in the dishwasher.",
            "HEAT RESISTANT: Safe for oven temperatures up to 450F.",
        ],
        "description": (
            "A reusable baking surface for cookies, vegetables, and everyday oven meals. "
            "The silicone mat releases food cleanly and cuts down on parchment paper."
        ),
        "review_profile": "generic",
    },
    {
        "sku_id": "SKU-003",
        "asin": "B0DEMO003",
        "brand": "NordicHome",
        "title": "NordicHome Portable Blender, 20 oz USB-C Rechargeable Personal Blender for Shakes, Smoothies and Travel",
        "category": "Kitchen & Dining",
        "subcategory": "Blenders",
        "marketplace": "US",
        "price": 29.99,
        "cost": 9.80,
        "stock": 95,
        "rating": 3.8,
        "review_count": 420,
        "target_acos": 0.28,
        "current_bid": 1.10,
        "attributes": ["20 oz", "USB-C rechargeable", "six blades", "leak-proof lid"],
        "benefits": [
            "blend on the go",
            "USB-C charging",
            "six-blade blending",
            "easy one-button operation",
        ],
        "bullets": [
            "BLEND ON THE GO: 20 oz cup doubles as a travel bottle for shakes, smoothies, and protein drinks.",
            "USB-C RECHARGEABLE: Charges from a laptop, power bank, or car adapter.",
            "SIX-BLADE BLENDING: Stainless steel blades handle fruit, protein powder, and ice.",
            "LEAK-PROOF LID: Silicone seal helps prevent spills in a gym bag or backpack.",
            "ONE-BUTTON OPERATION: Press to blend, twist to drink, rinse to clean.",
        ],
        "description": (
            "A cordless personal blender for shakes and smoothies on the go. "
            "The 20 oz cup doubles as a travel bottle and charges over USB-C."
        ),
        "review_profile": "blender",
    },
    {
        "sku_id": "SKU-004",
        "asin": "B0DEMO004",
        "brand": "NordicHome",
        "title": "NordicHome Bamboo Cutting Board Set, 3 Sizes with Juice Groove and Built-In Handles",
        "category": "Kitchen & Dining",
        "subcategory": "Cutting Boards",
        "marketplace": "US",
        "price": 27.99,
        "cost": 8.40,
        "stock": 150,
        "rating": 4.3,
        "review_count": 730,
        "target_acos": 0.26,
        "current_bid": 0.65,
        "attributes": ["3 sizes", "organic bamboo", "juice groove", "reversible"],
        "benefits": [
            "gentle on knife edges",
            "catches juice and runoff",
            "covers prep and serving",
            "reversible design",
        ],
        "bullets": [
            "ORGANIC BAMBOO: Dense, renewable bamboo is gentle on knife edges.",
            "JUICE GROOVE: Built-in groove catches runoff from roasts, fruit, and steaks.",
            "THREE SIZES: Small, medium, and large boards cover prep, carving, and serving.",
            "REVERSIBLE DESIGN: Use one side for meat and the other for vegetables.",
            "EASY CARE: Hand wash, dry upright, and oil occasionally to preserve the finish.",
        ],
        "description": (
            "A three-piece bamboo board set for prep, carving, and serving. "
            "The juice groove keeps counters clean and the reversible design separates food types."
        ),
        "review_profile": "generic",
    },
    {
        "sku_id": "SKU-005",
        "asin": "B0DEMO005",
        "brand": "NordicHome",
        "title": "NordicHome Reusable Storage Bags, 10-Pack BPA-Free Leakproof Food Bags for Snacks, Sandwiches and Travel",
        "category": "Kitchen & Dining",
        "subcategory": "Food Storage",
        "marketplace": "US",
        "price": 19.99,
        "cost": 5.20,
        "stock": 300,
        "rating": 4.2,
        "review_count": 540,
        "target_acos": 0.25,
        "current_bid": 0.55,
        "attributes": ["10-pack", "BPA-free", "leakproof", "freezer safe"],
        "benefits": [
            "replaces single-use bags",
            "food-safe material",
            "freezer and dishwasher safe",
            "ten-bag set",
        ],
        "bullets": [
            "REUSABLE AND LEAKPROOF: Replace single-use plastic bags for snacks, sandwiches, and travel.",
            "BPA-FREE MATERIAL: Food-safe construction for everyday food storage.",
            "FREEZER AND DISHWASHER SAFE: Store leftovers and clean up without fuss.",
            "TEN-BAG SET: Five snack bags and five sandwich bags cover lunch prep and travel.",
            "EASY TO SEAL: Zip closure keeps food fresh and prevents spills.",
        ],
        "description": (
            "A ten-piece reusable bag set for snacks, sandwiches, and travel. "
            "The leakproof zip closure and freezer-safe material replace single-use bags."
        ),
        "review_profile": "generic",
    },
]

# Deliberately non-compliant current listing for the demo star SKU.
SKU_BY_ID = {s["sku_id"]: s for s in SKUS}
SKU_BY_ID["SKU-003"]["current_listing"] = {
    "title": "NordicHome Best Seller Portable Blender, 20 oz USB-C Rechargeable Personal Blender",
    "bullets": [
        "BEST SELLER QUALITY: Our 100% leak-proof design is a customer favorite.",
        "BLEND ON THE GO: 20 oz cup doubles as a travel bottle for shakes and smoothies.",
        "USB-C RECHARGEABLE: Charges from a laptop, power bank, or car adapter.",
        "SIX-BLADE BLENDING: Stainless steel blades handle fruit, protein powder, and ice.",
        "ONE-BUTTON OPERATION: Press to blend, twist to drink, rinse to clean.",
    ],
    "description": (
        "The best seller portable blender for shakes and smoothies. "
        "Eco-friendly and 100% leak-proof for travel and the gym."
    ),
}
for sku in SKUS:
    sku.setdefault(
        "current_listing",
        {
            "title": sku["title"],
            "bullets": list(sku["bullets"]),
            "description": sku["description"],
        },
    )

KEYWORDS = {
    "SKU-001": [
        "french press",
        "stainless steel french press",
        "insulated coffee press",
        "coffee maker",
        "34 oz french press",
        "camping coffee press",
    ],
    "SKU-002": [
        "silicone baking mat",
        "baking mat set",
        "non stick oven liner",
        "cookie baking mat",
        "reusable baking sheet",
        "pastry mat",
    ],
    "SKU-003": [
        "portable blender",
        "personal blender",
        "usb blender",
        "blender for smoothies",
        "travel blender",
        "cordless blender",
    ],
    "SKU-004": [
        "bamboo cutting board",
        "cutting board set",
        "wood cutting board",
        "juice groove cutting board",
        "kitchen chopping board",
        "serving board",
    ],
    "SKU-005": [
        "reusable storage bags",
        "reusable food bags",
        "leakproof snack bags",
        "silicone food bags",
        "travel food bags",
        "freezer bags reusable",
    ],
}

KEYWORD_BANK = {
    "SKU-001": [
        ("french press", 74000, 0.98),
        ("stainless steel french press", 18100, 0.95),
        ("insulated coffee press", 9900, 0.91),
        ("coffee maker", 165000, 0.72),
        ("34 oz french press", 2400, 0.88),
        ("camping coffee press", 5400, 0.84),
        ("double wall french press", 3600, 0.90),
        ("coffee press", 22200, 0.93),
        ("french press coffee maker", 12100, 0.96),
        ("travel french press", 2900, 0.82),
    ],
    "SKU-002": [
        ("silicone baking mat", 49500, 0.98),
        ("baking mat set", 8100, 0.93),
        ("non stick oven liner", 6600, 0.88),
        ("cookie baking mat", 4400, 0.90),
        ("reusable baking sheet", 3900, 0.86),
        ("pastry mat", 14800, 0.79),
        ("silicone mat for baking", 12100, 0.94),
        ("oven liner", 22200, 0.71),
        ("baking supplies", 90500, 0.63),
        ("half sheet baking mat", 2900, 0.89),
    ],
    "SKU-003": [
        ("portable blender", 110000, 0.98),
        ("personal blender", 74000, 0.95),
        ("usb blender", 18100, 0.92),
        ("blender for smoothies", 40500, 0.94),
        ("travel blender", 8100, 0.89),
        ("cordless blender", 5400, 0.87),
        ("portable blender for shakes", 9900, 0.96),
        ("small blender", 33100, 0.78),
        ("blender bottle", 22200, 0.70),
        ("smoothie blender", 27100, 0.91),
    ],
    "SKU-004": [
        ("bamboo cutting board", 60500, 0.98),
        ("cutting board set", 18100, 0.94),
        ("wood cutting board", 33100, 0.91),
        ("juice groove cutting board", 4400, 0.89),
        ("kitchen chopping board", 8100, 0.86),
        ("serving board", 12100, 0.74),
        ("bamboo chopping board", 9900, 0.95),
        ("large cutting board", 14800, 0.84),
        ("cutting boards for kitchen", 27100, 0.90),
        ("wooden cutting board set", 6600, 0.92),
    ],
    "SKU-005": [
        ("reusable storage bags", 40500, 0.98),
        ("reusable food bags", 22200, 0.95),
        ("leakproof snack bags", 5400, 0.90),
        ("silicone food bags", 18100, 0.88),
        ("travel food bags", 3600, 0.82),
        ("freezer bags reusable", 4400, 0.86),
        ("reusable sandwich bags", 9900, 0.94),
        ("eco friendly food storage", 8100, 0.79),
        ("lunch bags for kids", 14800, 0.68),
        ("food storage containers", 74000, 0.61),
    ],
}

GENERIC_POSITIVE = [
    ("Works great", "Exactly what I needed. Good quality and easy to use."),
    ("Solid value", "Feels sturdy and does the job. Would buy again."),
    ("Better than expected", "Arrived quickly and works exactly as described."),
    ("Happy with this purchase", "Simple to use and easy to clean."),
    ("Good everyday item", "I use it several times a week and it has held up well."),
    ("Nice design", "Looks good on the counter and feels well made."),
    ("Does what it says", "No complaints so far. Good price for the quality."),
    ("Recommended", "Bought one for myself and one as a gift. Both work well."),
    ("Great gift", "Gave this to a friend and they loved it."),
    ("Five stars", "Good product, good packaging, no issues."),
]

GENERIC_NEGATIVE = [
    ("Disappointed", "Stopped working after a few weeks. Not worth the price."),
    ("Not as described", "The size is smaller than expected and the quality feels cheap."),
    ("Would not buy again", "Started falling apart after light use."),
    ("Poor quality", "The material feels flimsy and the finish scratched easily."),
    ("Arrived damaged", "Packaging was fine but the item had a crack."),
    ("Hard to use", "The instructions are unclear and it takes forever to set up."),
    ("Not durable", "Broke after two weeks of normal use."),
    ("Mixed feelings", "Works okay but feels overpriced for what it is."),
    ("Returned it", "Did not match the photos and felt low quality."),
    ("Save your money", "Mine stopped working almost immediately."),
]

GENERIC_NEUTRAL = [
    ("It's okay", "Does the job but nothing special."),
    ("Average", "Decent for the price, but I expected better."),
    ("Mixed", "Some things I like, some I don't."),
    ("Fine for now", "Works as expected so far. Will update if anything changes."),
    ("Not bad", "Good enough for occasional use."),
]

BLENDER_NEGATIVE = [
    ("Leaks everywhere", "The lid leaks if you fill it past the line. Ruined my gym bag."),
    ("Battery dies fast", "Battery dies after three or four blends. Not enough for a full day."),
    ("Can't crush ice", "It leaves big chunks of ice and frozen fruit. The motor is too weak."),
    ("Very loud", "Much louder than expected. Wakes up the whole house."),
    ("Hard to clean", "Residue gets stuck around the blades and the cup is hard to scrub."),
    ("Stopped charging", "Stopped charging after three weeks. Very disappointed."),
    ("Weak motor", "Blends protein powder fine but struggles with anything frozen."),
    ("Leak-proof? No", "The seal does not fit well and it leaks when I shake it."),
    ("Not worth it", "I wanted to like it, but the battery and blending power are both poor."),
    ("Cheap plastic", "The cup feels cheap and the lid cracked after a month."),
]

BLENDER_POSITIVE = [
    ("Perfect for the gym", "Fits in my bag and makes a quick shake after workouts."),
    ("Great for travel", "USB-C charging is convenient and it is easy to pack."),
    ("Good for smoothies", "Works well for soft fruit and protein shakes."),
    ("Easy to use", "One button, quick blend, and easy to rinse."),
    ("Nice size", "The 20 oz cup is just right for one serving."),
]

ADS_BASE = {
    "SKU-001": {"impressions": 9000, "ctr": 0.0045, "cvr": 0.12, "cpc": 0.75},
    "SKU-002": {"impressions": 7000, "ctr": 0.0040, "cvr": 0.10, "cpc": 0.65},
    "SKU-003": {"impressions": 14000, "ctr": 0.0028, "cvr": 0.045, "cpc": 0.95},
    "SKU-004": {"impressions": 6000, "ctr": 0.0042, "cvr": 0.11, "cpc": 0.60},
    "SKU-005": {"impressions": 8000, "ctr": 0.0038, "cvr": 0.09, "cpc": 0.55},
}

COMPLIANCE_RULES = [
    {
        "rule_id": "C-001",
        "category": "prohibited_claim",
        "check_type": "regex",
        "pattern": r"\bbest\s*seller\b",
        "severity": "block",
        "description": "Amazon prohibits 'best seller' claims unless the product has the badge.",
        "suggestion": "Remove the claim or reference the actual badge and category.",
    },
    {
        "rule_id": "C-002",
        "category": "prohibited_claim",
        "check_type": "regex",
        "pattern": r"(#\s*1\b|\bnumber\s+one\b)",
        "severity": "block",
        "description": "Ranking claims such as '#1' or 'number one' require substantiation.",
        "suggestion": "Remove the ranking claim and describe the product benefit instead.",
    },
    {
        "rule_id": "C-003",
        "category": "prohibited_claim",
        "check_type": "regex",
        "pattern": r"\bamazon'?s?\s+choice\b",
        "severity": "block",
        "description": "Amazon's Choice is a badge and cannot be used as ad copy.",
        "suggestion": "Remove the badge reference.",
    },
    {
        "rule_id": "C-004",
        "category": "medical_claim",
        "check_type": "regex",
        "pattern": r"\bfda\s+approved\b",
        "severity": "block",
        "description": "FDA approval claims require documentation and are restricted.",
        "suggestion": "Remove the claim unless you can provide the relevant clearance.",
    },
    {
        "rule_id": "C-005",
        "category": "medical_claim",
        "check_type": "regex",
        "pattern": (
            r"\b(cures?|treats?|prevents?)\s+"
            r"(cancer|disease|illness|infection|acne|pain|arthritis|diabetes|"
            r"anxiety|insomnia|condition|symptoms?)\b"
        ),
        "severity": "block",
        "description": "Medical treatment claims are not allowed for general products.",
        "suggestion": "Describe the product function, not a medical outcome.",
    },
    {
        "rule_id": "C-006",
        "category": "guarantee",
        "check_type": "regex",
        "pattern": r"\bguaranteed?\b",
        "severity": "warn",
        "description": "Guarantee claims must be clearly disclosed and supportable.",
        "suggestion": "Replace with a specific, supportable statement.",
    },
    {
        "rule_id": "C-007",
        "category": "guarantee",
        "check_type": "regex",
        "pattern": r"\b100\s*%",
        "severity": "warn",
        "description": "Absolute claims such as '100%' are difficult to substantiate.",
        "suggestion": "Use a measured claim or remove the percentage.",
    },
    {
        "rule_id": "C-008",
        "category": "certification",
        "check_type": "regex",
        "pattern": r"\beco[-\s]?friendly\b",
        "severity": "warn",
        "description": "Environmental claims require supporting documentation.",
        "suggestion": "Remove the claim or link it to a specific certification.",
    },
    {
        "rule_id": "C-009",
        "category": "certification",
        "check_type": "regex",
        "pattern": r"\bnon[-\s]?toxic\b",
        "severity": "warn",
        "description": "Safety claims require test evidence.",
        "suggestion": "Replace with a material fact, such as 'food-grade silicone'.",
    },
    {
        "rule_id": "C-010",
        "category": "certification",
        "check_type": "regex",
        "pattern": r"\bbpa[-\s]?free\b",
        "severity": "warn",
        "description": "BPA-free claims should be supported by test documentation.",
        "suggestion": "Keep the claim only if you have current test evidence.",
    },
    {
        "rule_id": "C-011",
        "category": "guarantee",
        "check_type": "regex",
        "pattern": r"\blifetime\s+warranty\b",
        "severity": "warn",
        "description": "Lifetime warranty terms must be disclosed and supportable.",
        "suggestion": "State the actual warranty period and terms.",
    },
    {
        "rule_id": "C-012",
        "category": "origin",
        "check_type": "regex",
        "pattern": r"\bmade\s+in\s+the?\s*usa\b",
        "severity": "warn",
        "description": "Country-of-origin claims require documentation.",
        "suggestion": "Remove the claim unless the product qualifies.",
    },
    {
        "rule_id": "C-013",
        "category": "promotion",
        "check_type": "regex",
        "pattern": r"\bfree\s+shipping\b",
        "severity": "warn",
        "description": "Shipping promises must match the actual offer.",
        "suggestion": "Remove the promise or confirm it is active.",
    },
    {
        "rule_id": "C-014",
        "category": "promotion",
        "check_type": "regex",
        "pattern": r"\blimited\s+time\b",
        "severity": "warn",
        "description": "Urgency claims must be truthful and time-bound.",
        "suggestion": "Remove the urgency language or add a real end date.",
    },
    {
        "rule_id": "C-015",
        "category": "medical_claim",
        "check_type": "regex",
        "pattern": r"\bdoctor\s+recommended\b",
        "severity": "warn",
        "description": "Endorsement claims require evidence and permission.",
        "suggestion": "Remove the endorsement claim.",
    },
    {
        "rule_id": "C-016",
        "category": "medical_claim",
        "check_type": "regex",
        "pattern": r"\bmedical\s+grade\b",
        "severity": "warn",
        "description": "Medical-grade claims require a defined standard.",
        "suggestion": "Use a specific material or test standard instead.",
    },
    {
        "rule_id": "C-017",
        "category": "format",
        "check_type": "max_length",
        "field": "title",
        "value": 200,
        "severity": "block",
        "description": "Titles must be 200 characters or fewer.",
        "suggestion": "Shorten the title and keep the most important attributes.",
    },
    {
        "rule_id": "C-018",
        "category": "format",
        "check_type": "max_items",
        "field": "bullets",
        "value": 5,
        "severity": "block",
        "description": "Listings support up to five bullet points.",
        "suggestion": "Merge or remove extra bullets.",
    },
    {
        "rule_id": "C-019",
        "category": "format",
        "check_type": "all_caps_field",
        "severity": "warn",
        "description": "Entire fields in all caps reduce readability and can be rejected.",
        "suggestion": "Use sentence case or short headline casing.",
    },
    {
        "rule_id": "C-020",
        "category": "format",
        "check_type": "url_or_contact",
        "severity": "block",
        "description": "Listings cannot contain external URLs or seller contact information.",
        "suggestion": "Remove links, email addresses, and phone numbers.",
    },
    {
        "rule_id": "C-021",
        "category": "format",
        "check_type": "emoji",
        "severity": "warn",
        "description": "Emojis are not recommended in listing copy.",
        "suggestion": "Remove emojis and use plain text.",
    },
]

POLICY_FILES = {
    "listing_quality.md": """# Listing Quality Policy (Demo Summary)

## Titles
Titles should be clear, specific, and under 200 characters. Include the brand, product type, key attribute, and size or quantity. Avoid promotional language and repeated keywords.

## Bullet Points
Use up to five bullets. Lead with a benefit, then support it with a concrete detail. Avoid all-caps sentences and keyword stuffing.

## Descriptions
Describe the product and its use. Do not include seller contact information, external URLs, or competitor brand names.

## Keyword Stuffing
Use keywords naturally. Do not repeat the same phrase across the title, bullets, and description.
""",
    "prohibited_claims.md": """# Prohibited Claims (Demo Summary)

## Superlatives
Do not claim "best seller", "#1", "top rated", or "Amazon's Choice" unless the product has the corresponding badge and the claim is accurate.

## Medical and Health Claims
Do not claim that a product cures, treats, or prevents a disease. Avoid "FDA approved" unless you can provide the relevant clearance.

## Guarantees
Avoid "100%", "guaranteed", "lifetime warranty", and "money back guarantee" unless the terms are clearly disclosed and supportable.

## Certifications
Claims such as "organic", "BPA free", "non-toxic", "eco-friendly", and "made in USA" require supporting documentation.
""",
    "advertising_policy.md": """# Advertising Policy (Demo Summary)

## Claims
Ad copy must match the product detail page. Do not advertise a price, discount, or feature that is not available on the landing page.

## Prohibited Content
Do not use competitor trademarks in ad copy. Do not make unsubstantiated health, safety, or environmental claims.

## Landing Page Consistency
The advertised product, size, and quantity must match the detail page. Mismatches can lead to ad disapproval.
""",
    "brand_guidelines.md": """# NordicHome Brand Guidelines (Demo)

## Voice
Practical, warm, and specific. Prefer concrete benefits over hype.

## Preferred Terms
Use "NordicHome" as the brand name. Use sentence case for descriptions. Keep bullet headlines short.

## Avoid
Avoid "best seller", "100%", "guaranteed", and medical claims. Do not mention competitor brands.
""",
    "image_video.md": """# Image and Video Guidance (Demo Summary)

## Main Image
Use a pure white background, show the product clearly, and avoid text overlays.

## Lifestyle Images
Show the product in use. Keep props relevant and avoid misleading scale.

## Video
Keep the product and packaging consistent with the listing. Do not use third-party trademarks.
""",
}


def write_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_jsonl(path: Path, rows) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def make_reviews(sku: dict) -> list[dict]:
    if sku["review_profile"] == "blender":
        pos_pool = BLENDER_POSITIVE + GENERIC_POSITIVE[:4]
        neg_pool = BLENDER_NEGATIVE + GENERIC_NEGATIVE[:4]
        neg_count, pos_count, neu_count = 16, 10, 4
    else:
        pos_pool = GENERIC_POSITIVE
        neg_pool = GENERIC_NEGATIVE
        neg_count, pos_count, neu_count = 6, 20, 4

    plan = [("negative", neg_count), ("positive", pos_count), ("neutral", neu_count)]
    reviews: list[dict] = []
    idx = 1
    for label, count in plan:
        for _ in range(count):
            if label == "negative":
                title, text = RNG.choice(neg_pool)
                rating = RNG.choice([1, 1, 2, 2, 3])
            elif label == "positive":
                title, text = RNG.choice(pos_pool)
                rating = RNG.choice([4, 5, 5])
            else:
                title, text = RNG.choice(GENERIC_NEUTRAL)
                rating = 3
            d = TODAY - timedelta(days=RNG.randint(1, 180))
            reviews.append(
                {
                    "review_id": f"RV-{sku['sku_id']}-{idx:02d}",
                    "sku_id": sku["sku_id"],
                    "rating": rating,
                    "title": title,
                    "text": text,
                    "date": d.isoformat(),
                    "verified_purchase": RNG.random() > 0.15,
                }
            )
            idx += 1
    RNG.shuffle(reviews)
    return reviews


def make_historical_listings(sku: dict) -> list[dict]:
    variants = [
        {"prefix": "", "conversion": 0.16, "rating": 4.6, "reviews": 2100},
        {"prefix": "Upgraded ", "conversion": 0.11, "rating": 4.3, "reviews": 860},
        {"prefix": "Pro ", "conversion": 0.07, "rating": 4.0, "reviews": 240},
        {"prefix": "Compact ", "conversion": 0.13, "rating": 4.5, "reviews": 1450},
    ]
    rows = []
    for i, variant in enumerate(variants, start=1):
        title = f"{variant['prefix']}{sku['title']}" if variant["prefix"] else sku["title"]
        if len(title) > 200:
            title = title[:197].rstrip() + "..."
        bullets = list(sku["bullets"])
        if variant["prefix"]:
            bullets[0] = f"{variant['prefix'].strip().upper()} DESIGN: {bullets[0].split(':', 1)[-1].strip()}"
        keywords = KEYWORDS[sku["sku_id"]]
        content = (
            f"Historical listing for {sku['sku_id']} ({sku['subcategory']}, {sku['marketplace']}).\n"
            f"Title: {title}\n"
            "Bullets:\n"
            + "\n".join(f"- {b}" for b in bullets)
            + f"\nDescription: {sku['description']}\n"
            + f"Backend keywords: {', '.join(keywords)}\n"
            + f"Performance: conversion_rate={variant['conversion']:.3f}, "
            + f"rating={variant['rating']}, reviews={variant['reviews']}."
        )
        rows.append(
            {
                "doc_id": f"HL-{sku['sku_id']}-{i:02d}",
                "sku_id": sku["sku_id"],
                "title": title,
                "bullets": bullets,
                "description": sku["description"],
                "keywords": keywords,
                "category": sku["category"],
                "subcategory": sku["subcategory"],
                "marketplace": sku["marketplace"],
                "conversion_rate": variant["conversion"],
                "rating": variant["rating"],
                "review_count": variant["reviews"],
                "content": content,
            }
        )
    return rows


def make_ads_daily(sku: dict) -> list[dict]:
    base = ADS_BASE[sku["sku_id"]]
    rows = []
    for i in range(90):
        d = TODAY - timedelta(days=89 - i)
        weekend = 1.08 if d.weekday() >= 5 else 1.0
        trend = (
            1.0 + 0.25 * (i / 89) + (0.20 if i >= 60 else 0.0)
            if sku["sku_id"] == "SKU-003"
            else 1.0
        )
        impressions = int(base["impressions"] * weekend * RNG.uniform(0.85, 1.15))
        clicks = max(1, int(impressions * base["ctr"] * RNG.uniform(0.85, 1.15)))
        cpc = base["cpc"] * RNG.uniform(0.90, 1.10)
        spend = round(clicks * cpc * trend, 2)
        cvr = base["cvr"] * RNG.uniform(0.90, 1.10)
        sales = round(clicks * cvr * sku["price"], 2)
        rows.append(
            {
                "sku_id": sku["sku_id"],
                "date": d.isoformat(),
                "impressions": impressions,
                "clicks": clicks,
                "spend": spend,
                "sales": sales,
            }
        )
    return rows


def make_ad_keywords(sku: dict) -> list[dict]:
    rows = []
    for keyword in KEYWORDS[sku["sku_id"]]:
        if sku["sku_id"] == "SKU-003":
            bid = round(RNG.uniform(0.85, 1.25), 2)
            impressions = RNG.randint(28000, 62000)
            ctr = RNG.uniform(0.0022, 0.0036)
            cvr = RNG.uniform(0.030, 0.055)
        else:
            bid = round(RNG.uniform(0.45, 0.95), 2)
            impressions = RNG.randint(12000, 38000)
            ctr = RNG.uniform(0.0035, 0.0055)
            cvr = RNG.uniform(0.08, 0.14)
        clicks = max(1, int(impressions * ctr))
        cpc = bid * 0.85
        spend = round(clicks * cpc, 2)
        sales = round(clicks * cvr * sku["price"], 2)
        rows.append(
            {
                "sku_id": sku["sku_id"],
                "keyword": keyword,
                "match_type": RNG.choice(["exact", "phrase", "broad"]),
                "bid": bid,
                "impressions_30d": impressions,
                "clicks_30d": clicks,
                "spend_30d": spend,
                "sales_30d": sales,
                "acos_30d": round(spend / sales, 3) if sales else 0.0,
            }
        )
    return rows


def align_ad_keywords(
    ad_keywords: list[dict], ads_daily: list[dict]
) -> list[dict]:
    """Scale keyword-level 30d metrics so they add up to the daily totals."""
    daily_by_sku: dict[str, list[dict]] = {}
    for row in ads_daily:
        daily_by_sku.setdefault(row["sku_id"], []).append(row)

    keywords_by_sku: dict[str, list[dict]] = {}
    for row in ad_keywords:
        keywords_by_sku.setdefault(row["sku_id"], []).append(row)

    for sku_id, keywords in keywords_by_sku.items():
        last30 = daily_by_sku[sku_id][-30:]
        targets = {
            "spend": sum(float(row["spend"]) for row in last30),
            "sales": sum(float(row["sales"]) for row in last30),
            "clicks": sum(int(row["clicks"]) for row in last30),
            "impressions": sum(int(row["impressions"]) for row in last30),
        }
        for metric in ("spend", "sales", "clicks", "impressions"):
            current = sum(float(row[f"{metric}_30d"]) for row in keywords)
            factor = targets[metric] / current if current else 1.0
            for row in keywords:
                value = float(row[f"{metric}_30d"]) * factor
                row[f"{metric}_30d"] = (
                    int(round(value)) if metric in {"clicks", "impressions"} else round(value, 2)
                )
        for row in keywords:
            row["acos_30d"] = (
                round(row["spend_30d"] / row["sales_30d"], 3)
                if row["sales_30d"]
                else 0.0
            )
    return ad_keywords


def main() -> int:
    if (SEED / ".real_data").exists() and "--force-synthetic" not in sys.argv:
        print(
            "data/seed was built from real public data (see data/seed/PROVENANCE.md).\n"
            "Refusing to overwrite it with synthetic data. Run data/fetch_real_seed.py "
            "to rebuild, or pass --force-synthetic to replace it on purpose."
        )
        return 2
    SEED.mkdir(parents=True, exist_ok=True)
    POLICIES.mkdir(parents=True, exist_ok=True)

    write_json(SEED / "skus.json", SKUS)
    write_json(
        SEED / "keyword_bank.json",
        [
            {
                "sku_id": sku["sku_id"],
                "keywords": [
                    {"keyword": kw, "search_volume": vol, "relevance": rel}
                    for kw, vol, rel in KEYWORD_BANK[sku["sku_id"]]
                ],
            }
            for sku in SKUS
        ],
    )
    write_json(SEED / "compliance_rules.json", COMPLIANCE_RULES)

    all_listings: list[dict] = []
    all_reviews: list[dict] = []
    all_ads_daily: list[dict] = []
    all_ad_keywords: list[dict] = []
    for sku in SKUS:
        all_listings.extend(make_historical_listings(sku))
        all_reviews.extend(make_reviews(sku))
        all_ads_daily.extend(make_ads_daily(sku))
        all_ad_keywords.extend(make_ad_keywords(sku))

    all_ad_keywords = align_ad_keywords(all_ad_keywords, all_ads_daily)

    write_jsonl(SEED / "historical_listings.jsonl", all_listings)
    write_jsonl(SEED / "reviews.jsonl", all_reviews)
    write_json(SEED / "ads_keywords.json", all_ad_keywords)

    with (SEED / "ads_daily.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["sku_id", "date", "impressions", "clicks", "spend", "sales"],
        )
        writer.writeheader()
        writer.writerows(all_ads_daily)

    for name, content in POLICY_FILES.items():
        (POLICIES / name).write_text(content.strip() + "\n", encoding="utf-8")

    print(f"Wrote seed data to {SEED}")
    print(f"  SKUs: {len(SKUS)}")
    print(f"  historical listings: {len(all_listings)}")
    print(f"  reviews: {len(all_reviews)}")
    print(f"  ads daily rows: {len(all_ads_daily)}")
    print(f"  ad keywords: {len(all_ad_keywords)}")
    print(f"  compliance rules: {len(COMPLIANCE_RULES)}")
    print(f"  policies: {len(POLICY_FILES)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
