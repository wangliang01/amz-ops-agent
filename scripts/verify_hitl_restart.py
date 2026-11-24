"""Restart the API and verify that an awaiting-approval run survives."""
from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = ROOT / ".venv" / "Scripts" / "python.exe"
PORT = int(os.getenv("HITL_TEST_PORT", "8015"))
BASE = f"http://127.0.0.1:{PORT}"


def call(method: str, path: str, payload: dict | None = None) -> dict:
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        BASE + path,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as response:
        return json.loads(response.read().decode())


class Api:
    def __init__(self, env: dict[str, str]):
        self.env = env
        self.proc: subprocess.Popen[str] | None = None

    def start(self) -> None:
        self.proc = subprocess.Popen(
            [
                str(PY),
                "-m",
                "uvicorn",
                "api.main:app",
                "--port",
                str(PORT),
                "--log-level",
                "warning",
            ],
            cwd=ROOT,
            env=self.env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        for _ in range(120):
            if self.proc.poll() is not None:
                raise RuntimeError("API exited during startup\n" + self._output())
            try:
                urllib.request.urlopen(BASE + "/health", timeout=2)
                return
            except Exception:
                time.sleep(0.25)
        raise RuntimeError("API did not start\n" + self._output())

    def stop(self) -> None:
        if self.proc is None:
            return
        self.proc.terminate()
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait(timeout=5)
        self.proc = None

    def _output(self) -> str:
        if self.proc is None or self.proc.stdout is None:
            return ""
        try:
            return self.proc.stdout.read()
        except Exception:
            return ""


def audit_counts(runs_db: Path, run_id: str) -> dict[str, int]:
    conn = sqlite3.connect(runs_db)
    try:
        rows = conn.execute(
            "SELECT action, COUNT(*) FROM audit WHERE run_id = ? GROUP BY action",
            (run_id,),
        ).fetchall()
    finally:
        conn.close()
    return {action: count for action, count in rows}


def run_status(runs_db: Path, run_id: str) -> str:
    conn = sqlite3.connect(runs_db)
    try:
        row = conn.execute(
            "SELECT status FROM runs WHERE run_id = ?", (run_id,)
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        raise AssertionError(f"run {run_id} missing from runs table")
    return row[0]


def main() -> None:
    with tempfile.TemporaryDirectory(
        prefix="amz-hitl-", ignore_cleanup_errors=True
    ) as tmp:
        tmp_path = Path(tmp)
        runs_db = tmp_path / "runs.sqlite"
        checkpoint_db = tmp_path / "checkpoints.sqlite"
        env = os.environ.copy()
        env["LLM_ENABLED"] = "false"
        env["EMBEDDING_ENABLED"] = "false"
        env["RUNS_DB_PATH"] = str(runs_db)
        env["CHECKPOINT_DB_PATH"] = str(checkpoint_db)

        api = Api(env)
        try:
            api.start()
            run_a = call("POST", "/runs", {"sku_id": "SKU-003", "mode": "full_chain"})
            run_b = call("POST", "/runs", {"sku_id": "SKU-001", "mode": "listing_only"})
            assert run_a["status"] == "awaiting_approval", run_a["status"]
            assert run_b["status"] == "awaiting_approval", run_b["status"]
            before = run_a["state"]
            rid_a, rid_b = run_a["run_id"], run_b["run_id"]
            api.stop()

            # Restart 1: the paused run survives; approve it.
            api.start()
            after = call("GET", f"/runs/{rid_a}")
            assert after["status"] == "awaiting_approval", after["status"]
            assert after["next"] == ["executor"], after["next"]
            assert after["state"]["sku_id"] == before["sku_id"]
            assert after["state"]["mode"] == before["mode"]
            assert (
                after["state"]["draft_listing"]["title"]
                == before["draft_listing"]["title"]
            )
            assert (
                after["state"]["ads_report"]["last_30d"]["acos"]
                == before["ads_report"]["last_30d"]["acos"]
            )

            done = call(
                "POST",
                f"/runs/{rid_a}/approve",
                {"decision": "approved", "actor": "verify"},
            )
            assert done["status"] == "completed", done["status"]
            log = done["state"].get("execution_log") or []
            assert len(log) == 5, len(log)
            assert all(item.get("status") == "dry_run_success" for item in log), log
            assert audit_counts(runs_db, rid_a).get("approval_decision") == 1
            assert audit_counts(runs_db, rid_a).get("execute_dry_run") == 5
            assert run_status(runs_db, rid_a) == "completed"
            api.stop()

            # Restart 2: repeated approval is idempotent; B can still be rejected.
            api.start()
            again = call(
                "POST",
                f"/runs/{rid_a}/approve",
                {"decision": "approved", "actor": "verify"},
            )
            assert again["status"] == "completed", again["status"]
            assert len(again["state"].get("execution_log") or []) == 5
            assert audit_counts(runs_db, rid_a).get("approval_decision") == 1
            assert audit_counts(runs_db, rid_a).get("execute_dry_run") == 5

            rejected = call(
                "POST",
                f"/runs/{rid_b}/approve",
                {"decision": "rejected", "actor": "verify"},
            )
            assert rejected["status"] == "completed", rejected["status"]
            rejected_log = rejected["state"].get("execution_log") or []
            assert len(rejected_log) == 1, rejected_log
            assert rejected_log[0].get("action") == "skip", rejected_log[0]
            assert rejected_log[0].get("status") == "rejected", rejected_log[0]
            assert audit_counts(runs_db, rid_b).get("approval_decision") == 1
            assert audit_counts(runs_db, rid_b).get("execute_skipped") == 1
            assert audit_counts(runs_db, rid_b).get("execute_dry_run", 0) == 0
            assert run_status(runs_db, rid_b) == "completed"
        finally:
            api.stop()

        assert checkpoint_db.exists(), f"missing checkpoint db: {checkpoint_db}"
        conn = sqlite3.connect(checkpoint_db)
        try:
            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
            }
        finally:
            conn.close()
        assert "checkpoints" in tables, tables
        assert checkpoint_db.stat().st_size > 0, checkpoint_db.stat().st_size
        print(f"HITL_RESTART_OK {rid_a} {rid_b}")


if __name__ == "__main__":
    main()
