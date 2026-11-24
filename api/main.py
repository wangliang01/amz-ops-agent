from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from langgraph.checkpoint.sqlite import SqliteSaver
from pydantic import BaseModel, Field

from agent.graph import build_graph
from agent.services import build_services
from core import db
from core.config import settings

services = None
graph = None


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global services, graph
    db.init_db()
    services = build_services()
    settings.checkpoint_db_path.parent.mkdir(parents=True, exist_ok=True)
    with SqliteSaver.from_conn_string(str(settings.checkpoint_db_path)) as checkpointer:
        graph = build_graph(services, checkpointer)
        yield


app = FastAPI(title="amz-ops-agent", version="0.1.0", lifespan=lifespan)


class RunRequest(BaseModel):
    sku_id: str = Field(default="SKU-003")
    mode: str = Field(default="full_chain")
    request: str = Field(
        default="Optimize this SKU across listing, compliance, and ads."
    )


class ApprovalRequest(BaseModel):
    decision: str = Field(default="approved")
    actor: str = Field(default="operator")
    note: str | None = None


def _config(run_id: str) -> dict[str, Any]:
    return {"configurable": {"thread_id": run_id}}


def _snapshot(run_id: str) -> dict[str, Any]:
    snapshot = graph.get_state(_config(run_id))
    state = dict(snapshot.values or {})
    return {
        "run_id": run_id,
        "next": list(snapshot.next or []),
        "status": "awaiting_approval" if snapshot.next else "completed",
        "state": state,
        "metrics": state.get("metrics") or {},
    }


def _save(run_id: str, snapshot: dict[str, Any]) -> None:
    state = snapshot.get("state") or {}
    db.save_run(
        run_id=run_id,
        thread_id=run_id,
        sku_id=str(state.get("sku_id") or ""),
        mode=str(state.get("mode") or ""),
        status=str(snapshot.get("status") or "unknown"),
        state=state,
        metrics=snapshot.get("metrics") or {},
    )


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "llm_enabled": bool(services and services.llm.enabled),
        "vector_index": bool(services and services.retriever.chroma),
    }


@app.get("/skus")
def list_skus() -> list[dict[str, Any]]:
    return [
        {
            "sku_id": sku["sku_id"],
            "title": sku["title"],
            "subcategory": sku["subcategory"],
            "price": sku["price"],
            "rating": sku["rating"],
            "review_count": sku["review_count"],
        }
        for sku in services.store.skus.values()
    ]


@app.post("/runs")
def create_run(payload: RunRequest) -> dict[str, Any]:
    if payload.mode not in {"full_chain", "listing_only", "ads_only", "auto"}:
        raise HTTPException(status_code=400, detail="invalid mode")
    try:
        services.store.sku(payload.sku_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=404, detail=f"unknown sku: {payload.sku_id}"
        ) from exc

    run_id = f"run-{uuid.uuid4().hex[:8]}"
    initial = {
        "run_id": run_id,
        "thread_id": run_id,
        "sku_id": payload.sku_id,
        "mode": payload.mode,
        "request": payload.request,
        "approval": None,
        "metrics": {"started_at": time.time()},
        "errors": [],
    }
    try:
        graph.invoke(initial, _config(run_id))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    snapshot = _snapshot(run_id)
    _save(run_id, snapshot)
    return snapshot


@app.get("/runs/{run_id}")
def get_run(run_id: str) -> dict[str, Any]:
    snapshot = _snapshot(run_id)
    if snapshot["state"]:
        return snapshot
    stored = db.get_run(run_id)
    if stored is None:
        raise HTTPException(status_code=404, detail="run not found")
    return {
        "run_id": run_id,
        "next": [],
        "status": stored["status"],
        "state": stored["state"],
        "metrics": stored["metrics"],
    }


@app.post("/runs/{run_id}/approve")
def approve(run_id: str, payload: ApprovalRequest) -> dict[str, Any]:
    if payload.decision not in {"approved", "rejected"}:
        raise HTTPException(
            status_code=400, detail="decision must be approved or rejected"
        )
    snapshot = _snapshot(run_id)
    if not snapshot["state"]:
        raise HTTPException(status_code=404, detail="run not found")
    if not snapshot["next"]:
        return snapshot

    graph.update_state(
        _config(run_id),
        {
            "approval": {
                "decision": payload.decision,
                "actor": payload.actor,
                "note": payload.note,
            }
        },
    )
    try:
        graph.invoke(None, _config(run_id))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    snapshot = _snapshot(run_id)
    _save(run_id, snapshot)
    db.add_audit(
        run_id,
        payload.actor,
        "approval_decision",
        {"decision": payload.decision, "note": payload.note},
    )
    return snapshot


@app.get("/runs")
def list_runs(limit: int = 20) -> list[dict[str, Any]]:
    return db.list_runs(limit)


@app.get("/metrics")
def metrics() -> dict[str, Any]:
    return db.metrics_summary()
