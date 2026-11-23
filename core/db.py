from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from core.config import settings


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _conn() -> sqlite3.Connection:
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                thread_id TEXT NOT NULL,
                sku_id TEXT NOT NULL,
                mode TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                state_json TEXT NOT NULL,
                metrics_json TEXT
            );
            CREATE TABLE IF NOT EXISTS audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                ts TEXT NOT NULL,
                actor TEXT NOT NULL,
                action TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );
            """
        )


def save_run(
    run_id: str,
    thread_id: str,
    sku_id: str,
    mode: str,
    status: str,
    state: dict[str, Any],
    metrics: dict[str, Any] | None = None,
) -> None:
    now = _now()
    with _conn() as conn:
        existing = conn.execute(
            "SELECT created_at FROM runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        created = existing["created_at"] if existing else now
        conn.execute(
            """
            INSERT INTO runs (
                run_id, thread_id, sku_id, mode, status,
                created_at, updated_at, state_json, metrics_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                status = excluded.status,
                updated_at = excluded.updated_at,
                state_json = excluded.state_json,
                metrics_json = excluded.metrics_json
            """,
            (
                run_id,
                thread_id,
                sku_id,
                mode,
                status,
                created,
                now,
                json.dumps(state, ensure_ascii=False, default=str),
                json.dumps(metrics or {}, ensure_ascii=False, default=str),
            ),
        )


def get_run(run_id: str) -> dict[str, Any] | None:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
    if row is None:
        return None
    data = dict(row)
    data["state"] = json.loads(data.pop("state_json"))
    data["metrics"] = json.loads(data.pop("metrics_json") or "{}")
    return data


def list_runs(limit: int = 20) -> list[dict[str, Any]]:
    with _conn() as conn:
        rows = conn.execute(
            """
            SELECT run_id, sku_id, mode, status, created_at, updated_at, metrics_json
            FROM runs ORDER BY created_at DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
    out = []
    for row in rows:
        item = dict(row)
        item["metrics"] = json.loads(item.pop("metrics_json") or "{}")
        out.append(item)
    return out


def add_audit(run_id: str, actor: str, action: str, payload: dict[str, Any]) -> None:
    with _conn() as conn:
        conn.execute(
            "INSERT INTO audit (run_id, ts, actor, action, payload_json) VALUES (?, ?, ?, ?, ?)",
            (
                run_id,
                _now(),
                actor,
                action,
                json.dumps(payload, ensure_ascii=False, default=str),
            ),
        )


def get_audit(run_id: str) -> list[dict[str, Any]]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM audit WHERE run_id = ? ORDER BY id", (run_id,)
        ).fetchall()
    out = []
    for row in rows:
        item = dict(row)
        item["payload"] = json.loads(item.pop("payload_json") or "{}")
        out.append(item)
    return out


def metrics_summary() -> dict[str, Any]:
    with _conn() as conn:
        rows = conn.execute("SELECT status, metrics_json FROM runs").fetchall()

    total = len(rows)
    completed = sum(1 for r in rows if r["status"] == "completed")
    awaiting = sum(1 for r in rows if r["status"] == "awaiting_approval")
    durations: list[float] = []
    pipeline_times: list[float] = []
    costs: list[float] = []
    compliance_pass = 0
    compliance_total = 0

    for row in rows:
        m = json.loads(row["metrics_json"] or "{}")
        if m.get("duration_sec"):
            durations.append(float(m["duration_sec"]))
        if m.get("pipeline_sec"):
            pipeline_times.append(float(m["pipeline_sec"]))
        if m.get("cost_usd") is not None:
            costs.append(float(m["cost_usd"]))
        if "compliance_passed" in m:
            compliance_total += 1
            if m["compliance_passed"]:
                compliance_pass += 1

    return {
        "runs": total,
        "completed": completed,
        "awaiting_approval": awaiting,
        "avg_duration_sec": round(sum(durations) / len(durations), 2) if durations else 0,
        "avg_wall_clock_sec": round(sum(durations) / len(durations), 2) if durations else 0,
        "avg_pipeline_sec": (
            round(sum(pipeline_times) / len(pipeline_times), 2)
            if pipeline_times
            else 0
        ),
        "total_cost_usd": round(sum(costs), 6),
        "avg_cost_usd": round(sum(costs) / len(costs), 6) if costs else 0,
        "compliance_pass_rate": (
            round(compliance_pass / compliance_total, 3) if compliance_total else None
        ),
    }
