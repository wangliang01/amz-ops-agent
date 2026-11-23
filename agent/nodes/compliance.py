from __future__ import annotations

import re
import time
from typing import Any

from agent.nodes.common import update_metrics
from agent.services import Services

URL_CONTACT_RE = re.compile(
    r"(https?://|www\.|[\w.+-]+@[\w-]+\.[\w.]+|\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b)",
    re.I,
)
EMOJI_RE = re.compile("[\U0001F300-\U0001FAFF☀-➿]")


def _fields(listing: dict[str, Any]) -> list[tuple[str, str]]:
    fields = [("title", str(listing.get("title") or ""))]
    for i, bullet in enumerate(listing.get("bullets") or [], start=1):
        fields.append((f"bullet_{i}", str(bullet or "")))
    fields.append(("description", str(listing.get("description") or "")))
    return fields


def _issue(rule: dict[str, Any], field: str, quote: str) -> dict[str, Any]:
    return {
        "rule_id": rule["rule_id"],
        "category": rule.get("category", "format"),
        "severity": rule.get("severity", "warn"),
        "field": field,
        "quote": str(quote)[:120],
        "message": rule.get("description", ""),
        "suggestion": rule.get("suggestion", ""),
    }


def check_rules(
    listing: dict[str, Any], rules: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for rule in rules:
        check_type = rule.get("check_type")
        if check_type == "regex":
            pattern = re.compile(rule["pattern"], re.I)
            for field, value in _fields(listing):
                match = pattern.search(value)
                if match:
                    issues.append(_issue(rule, field, match.group(0)))
        elif check_type == "max_length":
            field = rule.get("field", "title")
            value = str(listing.get(field) or "")
            if len(value) > int(rule["value"]):
                issues.append(_issue(rule, field, f"{len(value)} characters"))
        elif check_type == "max_items":
            field = rule.get("field", "bullets")
            value = listing.get(field) or []
            if len(value) > int(rule["value"]):
                issues.append(_issue(rule, field, f"{len(value)} items"))
        elif check_type == "all_caps_field":
            for field, value in _fields(listing):
                letters = [c for c in value if c.isalpha()]
                if len(letters) >= 12 and all(c.isupper() for c in letters):
                    issues.append(_issue(rule, field, "all caps"))
        elif check_type == "url_or_contact":
            for field, value in _fields(listing):
                match = URL_CONTACT_RE.search(value)
                if match:
                    issues.append(_issue(rule, field, match.group(0)))
        elif check_type == "emoji":
            for field, value in _fields(listing):
                match = EMOJI_RE.search(value)
                if match:
                    issues.append(_issue(rule, field, match.group(0)))

    seen: set[tuple[str, str, str]] = set()
    unique: list[dict[str, Any]] = []
    for issue in issues:
        key = (issue["rule_id"], issue["field"], issue["quote"])
        if key not in seen:
            seen.add(key)
            unique.append(issue)
    return unique


def _merge_llm_issues(
    llm_issues: Any, existing: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    if not isinstance(llm_issues, list):
        return existing
    seen = {(item["rule_id"], item["field"], item["quote"]) for item in existing}
    merged = list(existing)
    for index, raw in enumerate(llm_issues, start=1):
        if not isinstance(raw, dict):
            continue
        severity = str(raw.get("severity") or "warn").lower()
        if severity not in {"block", "warn", "info"}:
            severity = "warn"
        item = {
            "rule_id": str(raw.get("rule_id") or f"LLM-{index:02d}"),
            "category": str(raw.get("category") or "llm_review"),
            "severity": severity,
            "field": str(raw.get("field") or "listing"),
            "quote": str(raw.get("quote") or "")[:120],
            "message": str(raw.get("message") or "LLM compliance review flagged this copy."),
            "suggestion": str(raw.get("suggestion") or "Revise the copy."),
        }
        key = (item["rule_id"], item["field"], item["quote"])
        if key not in seen:
            seen.add(key)
            merged.append(item)
    return merged


def make_compliance_node(services: Services):
    def compliance_node(state: dict[str, Any]) -> dict[str, Any]:
        started = time.perf_counter()
        sku = state["sku"]
        listing = state.get("draft_listing") or {}
        current = sku.get("current_listing") or {}
        rules = services.store.compliance_rules

        draft_issues = check_rules(listing, rules)
        current_issues = check_rules(current, rules)

        query = f"{listing.get('title', '')} {' '.join(listing.get('bullets') or [])}"
        docs = services.retriever.search(
            query, top_k=5, doc_types=["policy", "compliance_rule"]
        )
        doc_block = "\n\n".join(
            f"[{doc['doc_id']}] {doc['title']}\n{doc['snippet']}" for doc in docs
        )
        fallback = {"additional_issues": [], "summary": "Rule checks completed."}

        data, usage = services.llm.json(
            system=(
                "You are an Amazon listing compliance reviewer. Review the draft listing "
                "against the policy evidence. Return JSON with additional_issues (list of "
                "{rule_id, category, severity, field, quote, message, suggestion}) and "
                "summary. Only flag real issues supported by the evidence."
            ),
            user=(
                f"Draft title: {listing.get('title', '')}\n"
                "Draft bullets:\n"
                + "\n".join(f"- {item}" for item in listing.get("bullets") or [])
                + f"\nDraft description: {listing.get('description', '')}\n\n"
                f"Policy evidence:\n{doc_block}"
            ),
            fallback=fallback,
            model=services.cfg.cheap_model,
        )

        merged = _merge_llm_issues(data.get("additional_issues"), draft_issues)
        blocks = sum(1 for item in merged if item["severity"] == "block")
        warns = sum(1 for item in merged if item["severity"] == "warn")
        score = max(0, 100 - 20 * blocks - 5 * warns)

        report = {
            "passed": blocks == 0,
            "score": score,
            "draft_issues": merged,
            "current_listing_issues": current_issues,
            "fixed_count": max(0, len(current_issues) - len(merged)),
            "checked_rules": len(rules),
            "summary": data.get("summary") or "Rule checks completed.",
            "citations": [doc["doc_id"] for doc in docs],
        }
        return {
            "compliance_report": report,
            "metrics": update_metrics(
                state,
                "compliance",
                started,
                usage,
                services.cfg.cheap_model,
                compliance_passed=report["passed"],
                compliance_issues=len(merged),
            ),
        }

    return compliance_node
