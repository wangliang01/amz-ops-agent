from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Callable

from agent.graph import build_graph
from agent.services import build_services
from core import db
from core.config import settings

GOLDEN = Path(__file__).resolve().parent / "golden.jsonl"
REPORT = Path(__file__).resolve().parent / "report.json"
LLM_REPORT = Path(__file__).resolve().parent / "llm_report.json"

# listing_only runs insight + listing + compliance, one LLM call each.
EXPECTED_LLM_CALLS = {"listing_only": 3}

Runner = Callable[[dict[str, Any]], dict[str, Any]]


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


def _case_metrics(state: dict[str, Any]) -> dict[str, Any]:
    metrics = state.get("metrics") or {}
    tokens = metrics.get("tokens") or {}
    return {
        "llm_calls": int(metrics.get("llm_calls", 0) or 0),
        "tokens": {
            "prompt": int(tokens.get("prompt", 0) or 0),
            "completion": int(tokens.get("completion", 0) or 0),
            "total": int(tokens.get("total", 0) or 0),
        },
        "cost_usd": float(metrics.get("cost_usd", 0.0) or 0.0),
    }


def run_cases(
    cases: list[dict[str, Any]],
    runner: Runner,
    *,
    require_llm: bool,
    max_cost_usd: float | None,
    expected_calls: int,
) -> tuple[list[dict[str, Any]], float, str | None]:
    """Run cases and enforce the LLM / cost contract.

    Returns (results, total_cost_usd, aborted). ``aborted`` is
    ``"cost_cap"`` when the accumulated cost exceeded the cap.
    """
    results: list[dict[str, Any]] = []
    total_cost = 0.0
    aborted: str | None = None

    for case in cases:
        result = dict(runner(case))
        calls = int(result.get("llm_calls", 0) or 0)
        if require_llm:
            failures = list(result.get("failures") or [])
            if calls == 0:
                failures.append("llm_not_used")
            elif calls < expected_calls:
                failures.append(
                    f"llm_calls_below_expected ({calls}/{expected_calls})"
                )
            if failures:
                result["failures"] = failures
                result["passed"] = False
        results.append(result)

        total_cost += float(result.get("cost_usd", 0.0) or 0.0)
        if max_cost_usd is not None and total_cost > max_cost_usd:
            aborted = "cost_cap"
            break

    return results, round(total_cost, 6), aborted


def _aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    tokens = {"prompt": 0, "completion": 0, "total": 0}
    for item in results:
        item_tokens = item.get("tokens") or {}
        for key in tokens:
            tokens[key] += int(item_tokens.get(key, 0) or 0)
    return {
        "llm_calls": sum(int(item.get("llm_calls", 0) or 0) for item in results),
        "tokens": tokens,
        "cost_usd": round(
            sum(float(item.get("cost_usd", 0.0) or 0.0) for item in results), 6
        ),
    }


def build_report(
    results: list[dict[str, Any]],
    *,
    mode: str,
    model: str,
    duration_sec: float,
    aborted: str | None,
    require_llm: bool,
) -> dict[str, Any]:
    passed = sum(1 for item in results if item["passed"])
    return {
        "mode": mode,
        "model": model,
        "require_llm": require_llm,
        "cases": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "pass_rate": round(passed / len(results), 3) if results else 0,
        **_aggregate(results),
        "duration_sec": round(duration_sec, 2),
        "aborted": aborted,
        "results": results,
    }


def _make_runner(graph: Any, delay_sec: float = 0) -> Runner:
    def runner(case: dict[str, Any]) -> dict[str, Any]:
        if delay_sec > 0:
            time.sleep(delay_sec)
        started = time.perf_counter()
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
        result = _evaluate(case, state)
        result.update(_case_metrics(state))
        result["latency_sec"] = round(time.perf_counter() - started, 2)
        return result

    return runner


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run golden listing evaluations.")
    parser.add_argument(
        "--require-llm",
        action="store_true",
        help="Fail when the LLM is not configured and when a case did not use it.",
    )
    parser.add_argument("--case", help="Run a single golden case id (e.g. G-001).")
    parser.add_argument("--limit", type=int, help="Run only the first N selected cases.")
    parser.add_argument(
        "--max-cost-usd",
        type=float,
        help="Stop after the accumulated estimated cost exceeds this value.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        help="Report path (default: evals/report.json or evals/llm_report.json).",
    )
    args = parser.parse_args(argv)

    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be >= 1")
    if args.max_cost_usd is not None and args.max_cost_usd < 0:
        parser.error("--max-cost-usd must be >= 0")

    if args.require_llm and not settings.llm_ready:
        print(
            "LLM 未启用：--require-llm 需要 OPENAI_API_KEY（且 LLM_ENABLED=true）。\n"
            "请在 .env 中配置后重试；不要提交或粘贴 key。",
            file=sys.stderr,
        )
        return 2

    cases = _load_cases()
    if args.case:
        cases = [case for case in cases if case["case_id"] == args.case]
        if not cases:
            print(f"unknown case: {args.case}", file=sys.stderr)
            return 2
    if args.limit is not None:
        cases = cases[: args.limit]

    llm_configured = settings.llm_ready
    report_path = args.report or (
        LLM_REPORT if (args.require_llm or llm_configured) else REPORT
    )
    report_path = Path(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    started = time.perf_counter()
    db.init_db()
    services = build_services()
    graph = build_graph(services)
    results, _total_cost, aborted = run_cases(
        cases,
        _make_runner(graph, settings.llm_case_delay_sec),
        require_llm=args.require_llm,
        max_cost_usd=args.max_cost_usd,
        expected_calls=EXPECTED_LLM_CALLS.get("listing_only", 0),
    )
    duration_sec = time.perf_counter() - started

    actual_calls = sum(int(item.get("llm_calls", 0) or 0) for item in results)
    mode = "llm" if actual_calls > 0 else "fallback"
    report = build_report(
        results,
        mode=mode,
        model=settings.chat_model,
        duration_sec=duration_sec,
        aborted=aborted,
        require_llm=args.require_llm,
    )
    report_path.write_text(
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
        f"\n{report['passed']}/{report['cases']} passed "
        f"({report['pass_rate']:.1%}); "
        f"llm_calls={report['llm_calls']}, tokens={report['tokens']['total']}, "
        f"cost=${report['cost_usd']:.6f}. Report: {report_path}"
    )
    if aborted:
        print(f"ABORTED: {aborted} (--max-cost-usd {args.max_cost_usd})")

    if aborted == "cost_cap":
        return 3
    if report["passed"] != report["cases"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
