from __future__ import annotations

import threading
import time
import uuid
from contextlib import ExitStack
from typing import Any

from langgraph.checkpoint.sqlite import SqliteSaver

from agent.graph import build_graph
from agent.services import build_services
from core import db
from core.config import settings


class LocalBackend:
    """Run the existing graph inside the Streamlit process.

    This mirrors the FastAPI endpoints used by the demo UI. It keeps the
    executor approval interrupt intact and only writes dry-run audit rows.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._stack = ExitStack()
        self.services = None
        self.graph = None

    def _ensure(self) -> None:
        if self.graph is not None:
            return
        db.init_db()
        self.services = build_services()
        settings.checkpoint_db_path.parent.mkdir(parents=True, exist_ok=True)
        checkpointer = self._stack.enter_context(
            SqliteSaver.from_conn_string(str(settings.checkpoint_db_path))
        )
        self.graph = build_graph(self.services, checkpointer)

    def _config(self, run_id: str) -> dict[str, Any]:
        return {"configurable": {"thread_id": run_id}}

    def _snapshot(self, run_id: str) -> dict[str, Any]:
        assert self.graph is not None
        snapshot = self.graph.get_state(self._config(run_id))
        state = dict(snapshot.values or {})
        return {
            "run_id": run_id,
            "next": list(snapshot.next or []),
            "status": "awaiting_approval" if snapshot.next else "completed",
            "state": state,
            "metrics": state.get("metrics") or {},
        }

    def _save(self, run_id: str, snapshot: dict[str, Any]) -> None:
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

    def health(self) -> dict[str, Any]:
        with self._lock:
            self._ensure()
            assert self.services is not None
            return {
                "ok": True,
                "llm_enabled": bool(self.services.llm.enabled),
                "vector_index": bool(self.services.retriever.chroma),
            }

    def list_skus(self) -> list[dict[str, Any]]:
        with self._lock:
            self._ensure()
            assert self.services is not None
            return [
                {
                    "sku_id": sku["sku_id"],
                    "title": sku["title"],
                    "subcategory": sku["subcategory"],
                    "price": sku["price"],
                    "rating": sku["rating"],
                    "review_count": sku["review_count"],
                }
                for sku in self.services.store.skus.values()
            ]

    def create_run(self, payload: dict[str, Any]) -> dict[str, Any]:
        mode = str(payload.get("mode") or "full_chain")
        sku_id = str(payload.get("sku_id") or "SKU-003")
        request = str(
            payload.get("request")
            or "Optimize this SKU across listing, compliance, and ads."
        )
        if mode not in {"full_chain", "listing_only", "ads_only", "auto"}:
            raise ValueError("invalid mode")
        with self._lock:
            self._ensure()
            assert self.services is not None and self.graph is not None
            try:
                self.services.store.sku(sku_id)
            except KeyError as exc:
                raise KeyError(f"unknown sku: {sku_id}") from exc

            run_id = f"run-{uuid.uuid4().hex[:8]}"
            initial = {
                "run_id": run_id,
                "thread_id": run_id,
                "sku_id": sku_id,
                "mode": mode,
                "request": request,
                "approval": None,
                "metrics": {"started_at": time.time()},
                "errors": [],
            }
            self.graph.invoke(initial, self._config(run_id))
            snapshot = self._snapshot(run_id)
            self._save(run_id, snapshot)
            return snapshot

    def get_run(self, run_id: str) -> dict[str, Any]:
        with self._lock:
            self._ensure()
            snapshot = self._snapshot(run_id)
            if snapshot["state"]:
                return snapshot
            stored = db.get_run(run_id)
            if stored is None:
                raise KeyError("run not found")
            return {
                "run_id": run_id,
                "next": [],
                "status": stored["status"],
                "state": stored["state"],
                "metrics": stored["metrics"],
            }

    def approve(self, run_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        decision = str(payload.get("decision") or "approved")
        actor = str(payload.get("actor") or "streamlit")
        note = payload.get("note")
        if decision not in {"approved", "rejected"}:
            raise ValueError("decision must be approved or rejected")
        with self._lock:
            self._ensure()
            assert self.graph is not None
            snapshot = self._snapshot(run_id)
            if not snapshot["state"]:
                raise KeyError("run not found")
            if not snapshot["next"]:
                return snapshot
            self.graph.update_state(
                self._config(run_id),
                {"approval": {"decision": decision, "actor": actor, "note": note}},
            )
            self.graph.invoke(None, self._config(run_id))
            snapshot = self._snapshot(run_id)
            self._save(run_id, snapshot)
            db.add_audit(
                run_id,
                actor,
                "approval_decision",
                {"decision": decision, "note": note},
            )
            return snapshot

    def list_runs(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._lock:
            return db.list_runs(limit)

    def metrics(self) -> dict[str, Any]:
        with self._lock:
            return db.metrics_summary()


backend = LocalBackend()
