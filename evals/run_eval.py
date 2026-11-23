from __future__ import annotations

import json
import sys
import time
import uuid
from pathlib import Path
from typing import Any

from agent.graph import build_graph
from agent.services import build_services
from core import db

GOLDEN = Path(__file__).resolve().parent / "golden.jsonl"
REPORT = Path(__file__).resolve().parent / "report.json"


def _load_cases() -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in GOLDEN.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _evaluate(case: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    listing = state.get("draft_listing") or {}
    compliance = state.get("compliance_report") or {}
    title = str(listing.get("title") or "")
    bullets = listing.get("bullets") or []
    text = " ".join(
        [title, *[str(item) for item in bullets], str(listing.get("description") or "")]
    ).lower()

    failures = []
    if len(title) > int(case.get("max_title_len", 200)):
        failures.append("title too long")
    if len(bullets) != int(case.get("bullets", 5)):
        failures.append(f"bullet count {len(bullets)}")
    for keyword in case.get("must_include") or []:
        if keyword.lower() not in text:
            failures.append(f"missing: {keyword}")
    for phrase in case.get("forbidden") or []:
        if phrase.lower() in text:
            failures.append(f"forbidden: {phrase}")
    if not listing.get("citations"):
        failures.append("no citations")
    if not compliance.get("passed"):
        failures.append("compliance blocked")

    return {
        "case_id": case["case_id"],
        "sku_id": case["sku_id"],
        "passed": not failures,
        "failures": failures,
        "title_len": len(title),
        "bullets": len(bullets),
        "citations": listing.get("citations") or [],
        "compliance_score": compliance.get("score"),
    }


def main() -> None:
    db.init_db()
    services = build_services()
    graph = build_graph(services)
    cases = _load_cases()
    results = []

    for case in cases:
        run_id = f"eval-{uuid.uuid4().hex[:6]}"
        config = {"configurable": {"thread_id": run_id}}
        graph.invoke(
            {
                "run_id": run_id,
                "thread_id": run_id,
                "sku_id": case["sku_id"],
                "mode": "listing_only",
                "request": f"Eval {case['case_id']}",
                "approval": None,
                "metrics": {"started_at": time.time()},
                "errors": [],
            },
            config,
        )
        state = dict(graph.get_state(config).values)
        results.append(_evaluate(case, state))

    passed = sum(1 for item in results if item["passed"])
    report = {
        "cases": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "pass_rate": round(passed / len(results), 3) if results else 0,
        "results": results,
    }
    REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"{'CASE':<8} {'SKU':<8} {'RESULT':<7} FAILURES")
    for item in results:
        print(
            f"{item['case_id']:<8} {item['sku_id']:<8} "
            f"{'PASS' if item['passed'] else 'FAIL':<7} "
            f"{', '.join(item['failures']) or '-'}"
        )
    print(
        f"\n{passed}/{len(results)} passed "
        f"({report['pass_rate']:.1%}). Report: {REPORT}"
    )
    if passed != len(results):
        sys.exit(1)


if __name__ == "__main__":
    main()
