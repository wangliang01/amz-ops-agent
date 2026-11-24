"""Build the demo seed from real public Amazon data.

Source: McAuley Lab, "Amazon Reviews 2023" (All Beauty category).
Product metadata, listing copy, ratings and review text are real public data,
with brand names replaced by neutral codes for the five featured SKUs.
Ads metrics, stock, cost, bids, keyword volumes and conversion rates are
simulated because they are private seller data; see data/seed/PROVENANCE.md.

Regenerate with:
    .\\.venv\\Scripts\\python.exe data\\fetch_real_seed.py
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import random
import re
import sys
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "data" / "seed"
CACHE = ROOT / "data" / "cache"
TODAY = date(2026, 11, 23)

DATASET = "McAuley-Lab/Amazon-Reviews-2023"
DATASET_URL = f"https://huggingface.co/datasets/{DATASET}"
META_URL = f"{DATASET_URL}/resolve/main/raw/meta_categories/meta_All_Beauty.jsonl"
REVIEW_URL = f"{DATASET_URL}/resolve/main/raw/review_categories/All_Beauty.jsonl"
META_SHA256 = "1cfbdf6d2ccf9c3ac52a4508b15f31f8f340508a245b65c3e3b5f461e06e97ef"
REVIEW_SHA256 = "36ca7c48440a8247b2dca0174d095238422b506a8a80c114dca722b7715f1c94"

# The five featured products are pinned by parent ASIN so regeneration is stable.
PRODUCTS = [
    {
        "sku_id": "SKU-001",
        "asin": "B019GBG0IE",
        "brand": "Brand A",
        "subcategory": "Hair Tools",
        "stock": 180,
        "target_acos": 0.30,
        "current_bid": 0.85,
        "attributes": ["Silicone", "Collapsible", "For curly hair", "Fits most hair dryers", "Black"],
        "extra_bullet": "Flexible silicone construction fits most hair dryer attachments.",
    },
    {
        "sku_id": "SKU-002",
        "asin": "B07D1B499B",
        "brand": "Brand B",
        "subcategory": "Nail Tools",
        "stock": 240,
        "target_acos": 0.28,
        "current_bid": 1.05,
        "attributes": ["110V US plug", "6 sanding bits", "3,000-20,000 RPM", "1.5 m cord", "Pink"],
    },
    {
        "sku_id": "SKU-003",
        "asin": "B074CQC2NG",
        "brand": "Brand C",
        "subcategory": "Skin Care Tools",
        "stock": 95,
        "target_acos": 0.28,
        "current_bid": 1.10,
        "attributes": ["12 lifts per kit", "Breathable tape", "For neck and jaw", "Adult"],
        "extra_bullet": "Breathable adhesive strips are shaped for the neck and jaw.",
    },
    {
        "sku_id": "SKU-004",
        "asin": "B00692OA2M",
        "brand": "Brand D",
        "subcategory": "Hair Removal",
        "stock": 150,
        "target_acos": 0.26,
        "current_bid": 0.75,
        "attributes": ["Cordless", "Adjustable T-blade", "3 trimming guides", "3 oz", "Black"],
        "extra_bullet": "Includes three trimming guides, a cleaning brush, and blade oil.",
    },
    {
        "sku_id": "SKU-005",
        "asin": "B0BMWQQR9W",
        "brand": "Brand E",
        "subcategory": "Nail Care",
        "stock": 300,
        "target_acos": 0.25,
        "current_bid": 0.55,
        "attributes": ["0.55 fl oz", "Ceramide treatment", "Clear finish", "Base and top coat"],
    },
]

HISTORICAL = {
    "Hair Tools": ["B00UCMO2U0", "B0797GW888", "B08MF3W9DZ", "B08K2RNJBJ"],
    "Nail Tools": ["B096LJB5RW", "B07D8SYBWD", "B089D1GLZM", "B007Y54ABE"],
    "Skin Care Tools": ["B095BQKYP3", "B0899QNWYJ", "B08SLFYG6K", "B0933HJVBG"],
    "Hair Removal": ["B07W867GKX", "B076C718PZ", "B00AX3YNPC", "B075KDK4D2"],
    "Nail Care": ["B07FYGVPV7", "B01M99C81L", "B07BKX1WZN", "B001AX81PM"],
}

KEYWORDS = {
    "SKU-001": [
        "hair diffuser",
        "collapsible diffuser",
        "curly hair diffuser",
        "travel hair dryer attachment",
        "silicone diffuser",
        "diffuser for curly hair",
    ],
    "SKU-002": [
        "nail drill",
        "nail art drill",
        "electric nail file",
        "manicure drill kit",
        "acrylic nail drill",
        "pedicure drill",
    ],
    "SKU-003": [
        "neck lift tape",
        "face lift tape",
        "instant neck lift",
        "jaw lift strips",
        "neck wrinkle tape",
        "invisible face tape",
    ],
    "SKU-004": [
        "hair trimmer",
        "cordless hair trimmer",
        "precision trimmer",
        "barber trimmer",
        "beard trimmer",
        "hair clipper",
    ],
    "SKU-005": [
        "nail strengthener",
        "nail thickener",
        "ridge filler",
        "nail growth treatment",
        "ceramide nail treatment",
        "clear nail base coat",
    ],
}

KEYWORD_BANK = {
    "SKU-001": [
        ("hair diffuser", 74000, 0.98),
        ("collapsible diffuser", 9900, 0.94),
        ("curly hair diffuser", 18100, 0.96),
        ("travel hair dryer attachment", 5400, 0.84),
        ("silicone diffuser", 3600, 0.88),
        ("diffuser for curly hair", 12100, 0.95),
        ("hair dryer diffuser", 33100, 0.92),
        ("portable diffuser", 2900, 0.82),
        ("diffuser attachment", 14800, 0.90),
        ("curl diffuser", 4400, 0.86),
    ],
    "SKU-002": [
        ("nail drill", 110000, 0.98),
        ("nail art drill", 18100, 0.95),
        ("electric nail file", 40500, 0.96),
        ("manicure drill kit", 8100, 0.92),
        ("acrylic nail drill", 9900, 0.94),
        ("pedicure drill", 5400, 0.88),
        ("nail drill machine", 27100, 0.97),
        ("professional nail drill", 12100, 0.93),
        ("nail buffer drill", 4400, 0.85),
        ("nail file kit", 22200, 0.78),
    ],
    "SKU-003": [
        ("neck lift tape", 40500, 0.98),
        ("face lift tape", 33100, 0.96),
        ("instant neck lift", 8100, 0.95),
        ("jaw lift strips", 5400, 0.92),
        ("neck wrinkle tape", 4400, 0.90),
        ("invisible face tape", 14800, 0.93),
        ("neck lift strips", 6600, 0.94),
        ("face tape for wrinkles", 9900, 0.91),
        ("neck tape", 12100, 0.88),
        ("facial lift tape", 3600, 0.89),
    ],
    "SKU-004": [
        ("hair trimmer", 90500, 0.98),
        ("cordless hair trimmer", 18100, 0.95),
        ("precision trimmer", 12100, 0.94),
        ("barber trimmer", 8100, 0.92),
        ("beard trimmer", 74000, 0.90),
        ("hair clipper", 60500, 0.86),
        ("trimmer for men", 40500, 0.88),
        ("professional hair trimmer", 6600, 0.93),
        ("cordless trimmer", 9900, 0.91),
        ("hair cutting machine", 14800, 0.84),
    ],
    "SKU-005": [
        ("nail strengthener", 49500, 0.98),
        ("nail thickener", 8100, 0.95),
        ("ridge filler", 12100, 0.92),
        ("nail growth treatment", 18100, 0.94),
        ("ceramide nail treatment", 2400, 0.96),
        ("clear nail base coat", 6600, 0.88),
        ("nail hardening polish", 9900, 0.93),
        ("nail repair treatment", 14800, 0.91),
        ("base coat nail polish", 22200, 0.82),
        ("nail protein treatment", 4400, 0.87),
    ],
}

ADS_BASE = {
    "SKU-001": {"impressions": 9000, "ctr": 0.0045, "cvr": 0.12, "cpc": 0.75},
    "SKU-002": {"impressions": 14000, "ctr": 0.0028, "cvr": 0.045, "cpc": 0.95},
    "SKU-003": {"impressions": 12000, "ctr": 0.0026, "cvr": 0.040, "cpc": 1.05},
    "SKU-004": {"impressions": 7000, "ctr": 0.0040, "cvr": 0.10, "cpc": 0.65},
    "SKU-005": {"impressions": 8000, "ctr": 0.0038, "cvr": 0.09, "cpc": 0.55},
}

PROHIBITED_PATTERNS = [
    r"\bbest\s*seller\b",
    r"(#\s*1\b|\bnumber\s+one\b)",
    r"\bamazon'?s?\s+choice\b",
    r"\bfda\s+approved\b",
    (
        r"\b(cures?|treats?|prevents?)\s+"
        r"(cancer|disease|illness|infection|acne|pain|arthritis|diabetes|"
        r"anxiety|insomnia|condition|symptoms?)\b"
    ),
    r"\bguaranteed?\b",
    r"\b100\s*%",
    r"\beco[-\s]?friendly\b",
    r"\bnon[-\s]?toxic\b",
    r"\bbpa[-\s]?free\b",
    r"\blifetime\s+warranty\b",
    r"\bmade\s+in\s+(?:the\s+)?usa\b",
    r"\bfree\s+shipping\b",
    r"\blimited\s+time\b",
    r"\bdoctor\s+recommended\b",
    r"\bmedical\s+grade\b",
]
PROHIBITED_RE = re.compile("|".join(f"(?:{p})" for p in PROHIBITED_PATTERNS), re.I)
CONTACT_RE = re.compile(
    r"(https?://|www\.|[\w.+-]+@[\w-]+\.[\w.]+|\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b)",
    re.I,
)
GENERIC_HEADING_RE = re.compile(
    r"^(product description|product high lights|product highlights|safety rules|"
    r"about this item|manufacturer contact information)$",
    re.I,
)
PHRASE_STRIP = [
    (re.compile(r"\bmedical[- ]grade,?\s*", re.I), ""),
    (re.compile(r"\bmade\s+in\s+(?:the\s+)?usa\b", re.I), ""),
    (re.compile(r"\b100\s*%\s*", re.I), ""),
]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _download(url: str, path: Path, sha256: str) -> None:
    if path.exists():
        digest = _sha256(path)
        if digest == sha256:
            print(f"cache hit {path.name} sha256={digest[:12]}…")
            return
        print(f"cache mismatch for {path.name}; re-downloading")
    path.parent.mkdir(parents=True, exist_ok=True)
    print(f"downloading {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "amz-ops-agent-demo/1.0"})
    with urllib.request.urlopen(req, timeout=120) as response, path.open("wb") as fh:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            fh.write(chunk)
    digest = _sha256(path)
    if digest != sha256:
        raise RuntimeError(f"sha256 mismatch for {path.name}: {digest} != {sha256}")


def _load_meta(asins: set[str]) -> dict[str, dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    with (CACHE / "meta_All_Beauty.jsonl").open(encoding="utf-8") as fh:
        for line in fh:
            if not any(asin in line for asin in asins):
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            asin = item.get("parent_asin")
            if asin in asins:
                found[asin] = item
    missing = asins - found.keys()
    if missing:
        raise RuntimeError(f"ASINs missing from metadata: {sorted(missing)}")
    return found


def _load_reviews(asins: set[str]) -> dict[str, list[dict[str, Any]]]:
    found: dict[str, list[dict[str, Any]]] = {asin: [] for asin in asins}
    with (CACHE / "reviews_All_Beauty.jsonl").open(encoding="utf-8") as fh:
        for line in fh:
            if not any(asin in line for asin in asins):
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            asin = item.get("parent_asin")
            if asin in found:
                found[asin].append(item)
    return found


def _as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return []
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
    return []


def _details(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _strip_html(text: str) -> str:
    text = html.unescape(re.sub(r"<[^>]+>", " ", text or ""))
    return re.sub(r"\s+", " ", text).strip()


def _sentence_case(text: str) -> str:
    letters = [char for char in text if char.isalpha()]
    if len(letters) >= 12 and all(char.isupper() for char in letters):
        return text[0] + text[1:].lower()
    # Normalize shouty prefixes such as "NAIL STRENGTHENER:" or "3 DAY RESULTS:".
    match = re.match(r"^([A-Z0-9][A-Z0-9 &'/-]{2,}?)(:\s*|\s+-\s+)", text)
    if match and sum(char.isalpha() for char in match.group(1)) >= 3:
        prefix = match.group(1)
        normalized = prefix[0] + prefix[1:].lower()
        return normalized + text[len(prefix):]
    return text


def clean_text(text: str) -> str:
    text = _strip_html(text)
    # Do not let abbreviations such as "Co." end a sentence.
    text = re.sub(r"\b(Co|Inc|Ltd|Corp|U\.S|U\.S\.A)\.(?=\s)", r"\1", text)
    for pattern, replacement in PHRASE_STRIP:
        text = pattern.sub(replacement, text)
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
    kept = [
        part
        for part in sentences
        if not PROHIBITED_RE.search(part)
        and not CONTACT_RE.search(part)
        and not GENERIC_HEADING_RE.match(part)
    ]
    return _sentence_case(" ".join(kept).strip())


def clean_title(title: str) -> str:
    title = _strip_html(title)
    if not PROHIBITED_RE.search(title):
        return title
    parts = [part.strip() for part in re.split(r",\s*|\s+with\s+|\s+-\s+", title) if part.strip()]
    kept = [part for part in parts if not PROHIBITED_RE.search(part)]
    return " ".join(kept) if kept else PROHIBITED_RE.sub("", title).strip(" ,-")


def anonymize(text: str, store: str, brand: str) -> str:
    if not store:
        return text
    variants = {store, store.rstrip("."), store.replace("The ", ""), store.replace("The ", "").rstrip(".")}
    for variant in sorted((item for item in variants if item), key=len, reverse=True):
        text = re.sub(re.escape(variant), brand, text, flags=re.I)
    return text


def trim(text: str, limit: int = 700) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    cut = text[:limit]
    end = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
    return cut[: end + 1].strip() if end > 80 else cut.rstrip() + "…"


def description_paragraphs(meta: dict[str, Any]) -> list[str]:
    paragraphs = []
    for item in _as_list(meta.get("description")):
        text = _strip_html(item)
        text = re.sub(
            r"^(Product Description|Product high lights|Product highlights|Safety rules|About this item)[:\s]*",
            "",
            text,
            flags=re.I,
        ).strip()
        if text and not GENERIC_HEADING_RE.match(text):
            paragraphs.append(text)
    return paragraphs


def fill_bullets(clean_features: list[str], description: str, count: int = 5) -> list[str]:
    bullets = [item for item in clean_features if item][:count]
    if len(bullets) < count:
        sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", description) if len(part.strip()) >= 25]
        sentences.sort(key=lambda item: (not (30 <= len(item) <= 180), len(item)))
        for sentence in sentences:
            if len(bullets) >= count:
                break
            if sentence not in bullets and not PROHIBITED_RE.search(sentence):
                bullets.append(trim(sentence, 180))
    while len(bullets) < count:
        bullets.append("See the product details for full specifications.")
    return bullets[:count]


def make_attributes(meta: dict[str, Any], features: list[str]) -> list[str]:
    details = _details(meta.get("details"))
    preferred = [
        "Color",
        "Material",
        "Hair Type",
        "Item Form",
        "Skin Type",
        "Unit Count",
        "Power Source",
        "Included Components",
        "Product Benefits",
        "Scent",
        "Liquid Volume",
        "Age Range (Description)",
    ]
    values: list[str] = []
    for key in preferred:
        value = str(details.get(key) or "").strip()
        if value and value.lower() not in {"no", "none", "not applicable"}:
            values.append(value[:60])
        if len(values) >= 4:
            break
    for feature in features:
        if len(values) >= 5:
            break
        snippet = trim(feature, 60)
        if snippet and snippet not in values:
            values.append(snippet)
    return values[:5]


def shorten(text: str, limit: int = 60) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    cut = text[:limit]
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return cut.rstrip(" ,;:-")


def make_benefits(features: list[str]) -> list[str]:
    benefits: list[str] = []
    for feature in features:
        text = feature.rstrip(" .!")
        if not text:
            continue
        headline = text.split(":", 1)[0] if ":" in text else text
        headline = shorten(headline, 72)
        if not headline:
            continue
        headline = headline[0].lower() + headline[1:] if headline[0].isupper() else headline
        benefits.append(headline)
        if len(benefits) == 4:
            break
    return benefits


def make_reviews(sku: dict[str, Any], raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for item in raw:
        try:
            rating = int(round(float(item.get("rating") or 0)))
            stamp = int(item.get("timestamp") or 0)
        except (TypeError, ValueError):
            continue
        if rating < 1 or stamp <= 0:
            continue
        when = datetime.fromtimestamp(stamp / 1000, tz=timezone.utc).date()
        if when.year < 2000 or when.year > 2023:
            continue
        text = trim(_strip_html(str(item.get("text") or "")), 700)
        title = trim(_strip_html(str(item.get("title") or "")), 160)
        if not text and not title:
            continue
        rows.append(
            {
                "rating": rating,
                "title": title,
                "text": text,
                "date": when.isoformat(),
                "verified_purchase": bool(item.get("verified_purchase")),
                "helpful": int(item.get("helpful_vote") or 0),
            }
        )
    rows.sort(key=lambda item: (-item["helpful"], item["date"]), reverse=False)
    rows = rows[:50]
    random.Random(sku["sku_id"]).shuffle(rows)
    reviews = []
    for index, row in enumerate(rows, start=1):
        reviews.append(
            {
                "review_id": f"RV-{sku['sku_id']}-{index:02d}",
                "sku_id": sku["sku_id"],
                "rating": row["rating"],
                "title": row["title"],
                "text": row["text"],
                "date": row["date"],
                "verified_purchase": row["verified_purchase"],
            }
        )
    return reviews


def make_sku(meta: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    store = str(meta.get("store") or "")
    brand = spec["brand"]
    real_title = anonymize(_strip_html(str(meta.get("title") or "")), store, brand)
    features = [
        anonymize(_strip_html(item), store, brand)
        for item in _as_list(meta.get("features"))
    ]
    paragraphs = [anonymize(item, store, brand) for item in description_paragraphs(meta)]
    real_description = trim(" ".join(paragraphs), 900)

    clean_features = [clean_text(item) for item in features]
    clean_features = [item for item in clean_features if len(item) >= 15]
    if spec.get("extra_bullet"):
        clean_features.append(spec["extra_bullet"])
    clean_description = trim(" ".join(clean_text(item) for item in paragraphs), 700)
    clean_bullets = fill_bullets(clean_features, clean_description)

    current_bullets = [trim(item, 240) for item in features][:5]
    if len(current_bullets) < 5:
        extra = [trim(item, 200) for item in paragraphs if len(item) >= 30]
        current_bullets += [item for item in extra if item not in current_bullets][: 5 - len(current_bullets)]
    current_bullets += ["See the product details for full specifications."] * (
        5 - len(current_bullets)
    )

    try:
        price = round(float(meta.get("price") or 0), 2)
    except (TypeError, ValueError):
        price = 0.0
    if price <= 0:
        price = 19.99

    return {
        "sku_id": spec["sku_id"],
        "asin": spec["asin"],
        "brand": brand,
        "title": clean_title(real_title),
        "category": "Beauty & Personal Care",
        "subcategory": spec["subcategory"],
        "marketplace": "US",
        "price": price,
        "cost": round(price * 0.4, 2),
        "stock": spec["stock"],
        "rating": float(meta.get("average_rating") or 0),
        "review_count": int(meta.get("rating_number") or 0),
        "target_acos": spec["target_acos"],
        "current_bid": spec["current_bid"],
        "attributes": spec.get("attributes") or make_attributes(meta, clean_features),
        "benefits": make_benefits(clean_features),
        "bullets": clean_bullets,
        "description": clean_description,
        "current_listing": {
            "title": real_title,
            "bullets": current_bullets,
            "description": real_description,
        },
        "data_origin": {
            "dataset": "Amazon Reviews 2023",
            "parent_asin": spec["asin"],
            "note": "Real public product metadata; brand anonymized. Draft copy sanitized for prohibited claims.",
        },
    }


def title_keywords(title: str, subcategory: str, limit: int = 6) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z-]{3,}", title.lower())
    stop = {
        "with",
        "pack",
        "count",
        "fluid",
        "ounce",
        "inch",
        "from",
        "your",
        "this",
        "that",
        "for",
        "and",
        "the",
        "plus",
        "size",
        "color",
        "set",
    }
    picked: list[str] = []
    for word in words:
        if word in stop or word in picked:
            continue
        picked.append(word)
        if len(picked) == limit - 1:
            break
    return picked + [subcategory.lower()]


def make_historical(
    sku_id: str, subcategory: str, meta: dict[str, Any], index: int
) -> dict[str, Any]:
    title = _strip_html(str(meta.get("title") or ""))
    features = [_strip_html(item) for item in _as_list(meta.get("features"))]
    paragraphs = description_paragraphs(meta)
    description = trim(" ".join(paragraphs), 600)
    bullets = [trim(item, 240) for item in features][:5]
    if len(bullets) < 5:
        bullets += [trim(item, 200) for item in paragraphs][: 5 - len(bullets)]
    bullets += ["See the product details for full specifications."] * (5 - len(bullets))
    rating = float(meta.get("average_rating") or 0)
    review_count = int(meta.get("rating_number") or 0)
    conversion = round(0.06 + max(0.0, rating - 4.0) * 0.12 + min(review_count, 5000) / 5000 * 0.03, 3)
    keywords = title_keywords(title, subcategory)
    content = (
        f"Historical listing, real public Amazon metadata (Amazon Reviews 2023).\n"
        f"Scope: SKU {sku_id}, {subcategory}, US marketplace.\n"
        f"Title: {title}\n"
        "Bullets:\n"
        + "\n".join(f"- {item}" for item in bullets)
        + f"\nDescription: {description}\n"
        + f"Backend keywords: {', '.join(keywords)}\n"
        + f"Performance: conversion_rate={conversion:.3f} (estimated), "
        + f"rating={rating} (real), reviews={review_count} (real)."
    )
    return {
        "doc_id": f"HL-{sku_id}-{index:02d}",
        "sku_id": sku_id,
        "title": title,
        "bullets": bullets,
        "description": description,
        "keywords": keywords,
        "category": "Beauty & Personal Care",
        "subcategory": subcategory,
        "marketplace": "US",
        "conversion_rate": conversion,
        "rating": rating,
        "review_count": review_count,
        "content": content,
    }


def make_ads_daily(sku: dict[str, Any]) -> list[dict[str, Any]]:
    rng = random.Random(f"{sku['sku_id']}-ads")
    base = ADS_BASE[sku["sku_id"]]
    rows = []
    for i in range(90):
        when = TODAY - timedelta(days=89 - i)
        weekend = 1.08 if when.weekday() >= 5 else 1.0
        trend = (
            1.0 + 0.25 * (i / 89) + (0.20 if i >= 60 else 0.0)
            if sku["sku_id"] == "SKU-003"
            else 1.0
        )
        impressions = int(base["impressions"] * weekend * rng.uniform(0.85, 1.15))
        clicks = max(1, int(impressions * base["ctr"] * rng.uniform(0.85, 1.15)))
        cpc = base["cpc"] * rng.uniform(0.90, 1.10)
        spend = round(clicks * cpc * trend, 2)
        cvr = base["cvr"] * rng.uniform(0.90, 1.10)
        sales = round(clicks * cvr * sku["price"], 2)
        rows.append(
            {
                "sku_id": sku["sku_id"],
                "date": when.isoformat(),
                "impressions": impressions,
                "clicks": clicks,
                "spend": spend,
                "sales": sales,
            }
        )
    return rows


def make_ad_keywords(sku: dict[str, Any]) -> list[dict[str, Any]]:
    rng = random.Random(f"{sku['sku_id']}-keywords")
    rows = []
    for keyword in KEYWORDS[sku["sku_id"]]:
        if sku["sku_id"] == "SKU-003":
            bid = round(rng.uniform(0.85, 1.25), 2)
            impressions = rng.randint(28000, 62000)
            ctr = rng.uniform(0.0022, 0.0036)
            cvr = rng.uniform(0.030, 0.055)
        else:
            bid = round(rng.uniform(0.45, 0.95), 2)
            impressions = rng.randint(12000, 38000)
            ctr = rng.uniform(0.0035, 0.0055)
            cvr = rng.uniform(0.08, 0.14)
        clicks = max(1, int(impressions * ctr))
        cpc = bid * 0.85
        spend = round(clicks * cpc, 2)
        sales = round(clicks * cvr * sku["price"], 2)
        rows.append(
            {
                "sku_id": sku["sku_id"],
                "keyword": keyword,
                "match_type": rng.choice(["exact", "phrase", "broad"]),
                "bid": bid,
                "impressions_30d": impressions,
                "clicks_30d": clicks,
                "spend_30d": spend,
                "sales_30d": sales,
                "acos_30d": round(spend / sales, 3) if sales else 0.0,
            }
        )
    return rows


def align_ad_keywords(ad_keywords: list[dict[str, Any]], ads_daily: list[dict[str, Any]]) -> list[dict[str, Any]]:
    daily_by_sku: dict[str, list[dict[str, Any]]] = {}
    for row in ads_daily:
        daily_by_sku.setdefault(row["sku_id"], []).append(row)
    keywords_by_sku: dict[str, list[dict[str, Any]]] = {}
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
                round(row["spend_30d"] / row["sales_30d"], 3) if row["sales_30d"] else 0.0
            )
    return ad_keywords


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_provenance(skus: list[dict[str, Any]]) -> None:
    lines = [
        "# 数据来源与口径",
        "",
        f"- 数据集：Amazon Reviews 2023（{DATASET}），类别 All Beauty。",
        f"- 上游地址：{DATASET_URL}",
        "- 引用：Hou, Y., Li, J., He, Z., Yan, A., Chen, X., & McAuley, J. (2024). "
        "Bridging Language and Items for Retrieval and Recommendation. arXiv:2403.03952.",
        "- 许可与用途：该数据集面向研究与非商业用途；本仓库只用于公开演示。",
        f"- 快照下载日期：{TODAY.isoformat()}（评论时间截至 2023 年）。",
        f"- 元数据文件 sha256：`{META_SHA256}`",
        f"- 评论文件 sha256：`{REVIEW_SHA256}`",
        "",
        "## 哪些是真实数据",
        "",
        "- 5 个主 SKU 的商品标题、五点、描述、价格、评分、评论数、原始评论正文和评论日期。",
        "- 20 条历史 Listing 的标题、五点、描述、评分、评论数。",
        "- 评论按 helpful_vote 取前 50 条后确定性打乱，仅保留 rating/title/text/date/verified_purchase。",
        "",
        "## 哪些是模拟数据",
        "",
        "- 广告：90 天 impressions / clicks / spend / sales、关键词出价与 30 天回测数据。",
        "- 库存、成本、目标 ACOS、当前出价、关键词搜索量。",
        "- 历史 Listing 的 conversion_rate（由评分与评论数估算，非真实转化率）。",
        "",
        "## 匿名化与清洗",
        "",
        "- 5 个主 SKU 的品牌名替换为 Brand A–E；评论中的 user_id、图片、helpful_vote 不落种子。",
        "- 用于生成草稿的 title / bullets / description 会移除违规宣称（100%、guarantee、medical grade、made in USA 等）；",
        "  `current_listing` 保留真实原文，用于演示合规扫描。",
        "",
        "## 主 SKU 对照",
        "",
        "| SKU | parent_asin | 评分 | 评论数 | 价格 |",
        "|---|---|---|---|---|",
    ]
    for sku in skus:
        lines.append(
            f"| {sku['sku_id']} | {sku['asin']} | {sku['rating']} | "
            f"{sku['review_count']} | {sku['price']} |"
        )
    lines.append("")
    (SEED / "PROVENANCE.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-hash", action="store_true", help="skip source sha256 checks")
    args = parser.parse_args()

    CACHE.mkdir(parents=True, exist_ok=True)
    SEED.mkdir(parents=True, exist_ok=True)
    meta_path = CACHE / "meta_All_Beauty.jsonl"
    review_path = CACHE / "reviews_All_Beauty.jsonl"
    if args.skip_hash:
        if not meta_path.exists() or not review_path.exists():
            raise RuntimeError("cache missing; run without --skip-hash once")
    else:
        _download(META_URL, meta_path, META_SHA256)
        _download(REVIEW_URL, review_path, REVIEW_SHA256)

    all_asins = {item["asin"] for item in PRODUCTS}
    for asins in HISTORICAL.values():
        all_asins.update(asins)
    meta = _load_meta(all_asins)
    raw_reviews = _load_reviews({item["asin"] for item in PRODUCTS})

    skus = [make_sku(meta[item["asin"]], item) for item in PRODUCTS]
    reviews: list[dict[str, Any]] = []
    for sku in skus:
        reviews.extend(make_reviews(sku, raw_reviews[sku["asin"]]))

    all_listings: list[dict[str, Any]] = []
    for sku in skus:
        for index, asin in enumerate(HISTORICAL[sku["subcategory"]], start=1):
            all_listings.append(
                make_historical(sku["sku_id"], sku["subcategory"], meta[asin], index)
            )

    ads_daily: list[dict[str, Any]] = []
    ad_keywords: list[dict[str, Any]] = []
    for sku in skus:
        ads_daily.extend(make_ads_daily(sku))
        ad_keywords.extend(make_ad_keywords(sku))
    ad_keywords = align_ad_keywords(ad_keywords, ads_daily)

    write_json(SEED / "skus.json", skus)
    write_json(
        SEED / "keyword_bank.json",
        [
            {
                "sku_id": sku["sku_id"],
                "keywords": [
                    {"keyword": keyword, "search_volume": volume, "relevance": relevance}
                    for keyword, volume, relevance in KEYWORD_BANK[sku["sku_id"]]
                ],
            }
            for sku in skus
        ],
    )
    write_jsonl(SEED / "reviews.jsonl", reviews)
    write_jsonl(SEED / "historical_listings.jsonl", all_listings)
    write_json(SEED / "ads_keywords.json", ad_keywords)
    with (SEED / "ads_daily.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["sku_id", "date", "impressions", "clicks", "spend", "sales"],
        )
        writer.writeheader()
        writer.writerows(ads_daily)
    write_provenance(skus)
    (SEED / ".real_data").write_text(
        "Built from Amazon Reviews 2023 (All Beauty). See PROVENANCE.md.\n",
        encoding="utf-8",
    )

    print(f"Wrote real-data seed to {SEED}")
    print(f"  SKUs: {len(skus)}")
    print(f"  reviews: {len(reviews)}")
    print(f"  historical listings: {len(all_listings)}")
    print(f"  ads daily rows: {len(ads_daily)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
