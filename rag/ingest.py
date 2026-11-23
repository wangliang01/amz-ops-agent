from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.config import settings


@dataclass
class Doc:
    doc_id: str
    doc_type: str
    title: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


def _listing_docs(seed: Path) -> list[Doc]:
    docs: list[Doc] = []
    path = seed / "historical_listings.jsonl"
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        docs.append(
            Doc(
                doc_id=item["doc_id"],
                doc_type="historical_listing",
                title=item["title"],
                content=item["content"],
                metadata={
                    "sku_id": item["sku_id"],
                    "category": item["category"],
                    "subcategory": item["subcategory"],
                    "marketplace": item["marketplace"],
                    "conversion_rate": item["conversion_rate"],
                    "rating": item["rating"],
                    "review_count": item["review_count"],
                },
            )
        )
    return docs


def _policy_docs(seed: Path) -> list[Doc]:
    docs: list[Doc] = []
    for path in sorted((seed / "policies").glob("*.md")):
        text = path.read_text(encoding="utf-8")
        parts = re.split(r"\n(?=##\s+)", text)
        for i, part in enumerate(parts):
            part = part.strip()
            if not part:
                continue
            lines = part.splitlines()
            if lines[0].startswith("## "):
                heading = lines[0].lstrip("# ").strip()
            elif lines[0].startswith("# "):
                heading = lines[0].lstrip("# ").strip()
            else:
                heading = path.stem
            docs.append(
                Doc(
                    doc_id=f"POL-{path.stem}-{i:02d}",
                    doc_type="policy",
                    title=heading,
                    content=part,
                    metadata={"source": path.name, "section": heading},
                )
            )
    return docs


def _rule_docs(seed: Path) -> list[Doc]:
    rules = json.loads((seed / "compliance_rules.json").read_text(encoding="utf-8"))
    docs: list[Doc] = []
    for rule in rules:
        content = (
            f"Rule {rule['rule_id']} ({rule['category']}, severity={rule['severity']}). "
            f"{rule['description']} Suggestion: {rule['suggestion']}"
        )
        docs.append(
            Doc(
                doc_id=f"RULE-{rule['rule_id']}",
                doc_type="compliance_rule",
                title=f"{rule['rule_id']} {rule['category']}",
                content=content,
                metadata={
                    "rule_id": rule["rule_id"],
                    "category": rule["category"],
                    "severity": rule["severity"],
                },
            )
        )
    return docs


def load_seed_docs(seed_dir: Path | None = None) -> list[Doc]:
    seed = seed_dir or settings.data_dir
    return _listing_docs(seed) + _policy_docs(seed) + _rule_docs(seed)
