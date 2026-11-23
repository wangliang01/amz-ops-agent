from __future__ import annotations

import argparse
import json
import time
import uuid
from typing import Any

from agent.graph import build_graph
from agent.services import build_services
from core import db


def _state(graph, config) -> dict[str, Any]:
    return dict(graph.get_state(config).values or {})


def _section(title: str, payload: Any) -> None:
    print(f"\n=== {title} ===")
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the amz-ops-agent demo end to end."
    )
    parser.add_argument("--sku", default="SKU-003")
    parser.add_argument(
        "--mode",
        default="full_chain",
        choices=["full_chain", "listing_only", "ads_only", "auto"],
    )
    parser.add_argument(
        "--approve", action="store_true", help="Approve proposals without prompting."
    )
    parser.add_argument(
        "--reject", action="store_true", help="Reject proposals without prompting."
    )
    parser.add_argument("--json", action="store_true", help="Print the full state.")
    args = parser.parse_args()

    db.init_db()
    services = build_services()
    graph = build_graph(services)

    run_id = f"run-{uuid.uuid4().hex[:8]}"
    config = {"configurable": {"thread_id": run_id}}
    initial: dict[str, Any] = {
        "run_id": run_id,
        "thread_id": run_id,
        "sku_id": args.sku,
        "mode": args.mode,
        "request": f"Optimize {args.sku} across listing, compliance, and ads.",
        "approval": None,
        "metrics": {"started_at": time.time()},
        "errors": [],
    }

    print(f"Run {run_id} | SKU {args.sku} | mode {args.mode}")
    graph.invoke(initial, config)
    state = _state(graph, config)

    if args.json:
        _section("STATE (before approval)", state)
    else:
        for key, title in [
            ("insights", "Insight"),
            ("draft_listing", "Listing draft"),
            ("compliance_report", "Compliance"),
            ("ads_report", "Ads diagnosis"),
        ]:
            if state.get(key):
                _section(title, state[key])
        if state.get("retrieved_docs"):
            _section("Retrieved evidence", state["retrieved_docs"])

    snapshot = graph.get_state(config)
    if snapshot.next:
        print("\nGraph paused before executor. Proposals:")
        print(json.dumps(state.get("proposals") or [], ensure_ascii=False, indent=2))
        if args.reject:
            decision = "rejected"
        elif args.approve:
            decision = "approved"
        else:
            answer = input("Approve these dry-run actions? [y/N] ").strip().lower()
            decision = "approved" if answer in {"y", "yes"} else "rejected"
        graph.update_state(
            config, {"approval": {"decision": decision, "actor": "cli"}}
        )
        graph.invoke(None, config)
        state = _state(graph, config)
        _section("Execution log", state.get("execution_log") or [])
    else:
        print("\nGraph completed without an approval step.")

    _section("Metrics", state.get("metrics") or {})
    status = "completed" if not graph.get_state(config).next else "awaiting_approval"
    db.save_run(
        run_id=run_id,
        thread_id=run_id,
        sku_id=args.sku,
        mode=args.mode,
        status=status,
        state=state,
        metrics=state.get("metrics") or {},
    )
    print(f"\nSaved run {run_id} (status={status}).")


if __name__ == "__main__":
    main()
