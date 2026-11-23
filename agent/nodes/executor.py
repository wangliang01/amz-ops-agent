from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from agent.nodes.common import update_metrics
from agent.services import Services
from core import db


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def make_executor_node(services: Services):
    def executor_node(state: dict[str, Any]) -> dict[str, Any]:
        started = time.perf_counter()
        run_id = state.get("run_id", "")
        approval = state.get("approval") or {}
        decision = str(approval.get("decision") or "pending").lower()
        actor = str(approval.get("actor") or "operator")
        proposals = list(state.get("proposals") or [])

        logs: list[dict[str, Any]] = []
        if decision == "approved":
            for proposal in proposals:
                log = {
                    "ts": _now(),
                    "action": proposal.get("action"),
                    "keyword": proposal.get("keyword"),
                    "current_bid": proposal.get("current_bid"),
                    "proposed_bid": proposal.get("proposed_bid"),
                    "status": "dry_run_success",
                }
                logs.append(log)
                db.add_audit(run_id, actor, "execute_dry_run", log)
        else:
            logs.append(
                {
                    "ts": _now(),
                    "action": "skip",
                    "status": "rejected" if decision == "rejected" else "no_approval",
                }
            )
            db.add_audit(
                run_id,
                actor,
                "execute_skipped",
                {"decision": decision, "proposals": len(proposals)},
            )

        metrics = update_metrics(
            state,
            "executor",
            started,
            execution_mode="dry_run",
            approved=decision == "approved",
            actions_executed=sum(
                1 for item in logs if item.get("status") == "dry_run_success"
            ),
        )
        start_ts = float(metrics.get("started_at") or time.time())
        wall_clock_sec = round(time.time() - start_ts, 2)
        pipeline_sec = round(
            sum(
                float(value)
                for value in (metrics.get("node_times") or {}).values()
            ),
            2,
        )
        metrics["pipeline_sec"] = pipeline_sec
        metrics["wall_clock_sec"] = wall_clock_sec
        metrics["approval_wait_sec"] = round(
            max(0.0, wall_clock_sec - pipeline_sec), 2
        )
        metrics["duration_sec"] = wall_clock_sec
        return {"execution_log": logs, "metrics": metrics}

    return executor_node
