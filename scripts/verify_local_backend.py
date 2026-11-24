from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path


def main() -> int:
    runtime = Path(tempfile.mkdtemp(prefix="amz-ops-local-"))
    os.environ["LLM_ENABLED"] = "false"
    os.environ["EMBEDDING_ENABLED"] = "false"
    os.environ["RUNS_DB_PATH"] = str(runtime / "runs.sqlite")
    os.environ["CHECKPOINT_DB_PATH"] = str(runtime / "checkpoints.sqlite")

    from app.local_backend import backend
    from core import db

    health = backend.health()
    skus = backend.list_skus()
    assert health["ok"] is True, health
    assert health["adapters"]["mode"] == "mock", health
    assert health["adapters"]["read_only"] is True, health
    assert len(skus) == 5, len(skus)

    snapshot = backend.create_run({"sku_id": "SKU-003", "mode": "full_chain"})
    assert snapshot["status"] == "awaiting_approval", snapshot["status"]
    assert snapshot["next"] == ["executor"], snapshot["next"]
    state = snapshot.get("state") or {}
    assert len((state.get("creative_brief") or {}).get("assets") or []) == 5
    assert (state.get("creative_review") or {}).get("passed") is True
    assert (state.get("creative_review") or {}).get("provider") == "mock"
    run_id = snapshot["run_id"]

    completed = backend.approve(run_id, {"decision": "approved", "actor": "verify"})
    assert completed["status"] == "completed", completed["status"]
    logs = (completed.get("state") or {}).get("execution_log") or []
    assert len(logs) == 5, len(logs)
    assert all(item.get("status") == "dry_run_success" for item in logs), logs
    assert backend.metrics()["runs"] == 1

    audit = db.get_audit(run_id)
    decisions = [
        item["payload"].get("decision")
        for item in audit
        if item["action"] == "approval_decision"
    ]
    assert decisions == ["approved"], decisions

    print(
        "LOCAL_BACKEND_OK "
        f"skus={len(skus)} awaiting_approval=ok creative=5_mock "
        f"adapters=mock approve=5_dry_run audit={len(audit)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
