from __future__ import annotations

import os
import sys
from pathlib import Path

import requests
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py"
EXPECTED_TABS = ["洞察", "Listing", "合规", "广告", "审计", "指标"]
EXPECTED_ACTIONS = 5


def labels(items) -> list[str]:
    return [getattr(item, "label", "") for item in items]


def button(at: AppTest, label: str):
    for item in at.button:
        if item.label == label:
            return item
    raise AssertionError(f"button not found: {label}; have {labels(at.button)}")


def main() -> int:
    base = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
    try:
        requests.get(f"{base}/skus", timeout=5).raise_for_status()
    except Exception as exc:
        print(f"UI_VERIFY_FAILED: API not reachable at {base}: {exc}")
        return 1

    at = AppTest.from_file(str(APP), default_timeout=180)
    at.run()
    assert not at.error, [str(item.value) for item in at.error]
    assert labels(at.selectbox) == ["商品 SKU", "运行模式"]
    assert labels(at.button) == ["运行流水线"]
    assert labels(at.tabs) == []

    at.selectbox[0].set_value("SKU-003")
    at.selectbox[1].set_value("full_chain")
    button(at, "运行流水线").click()
    at.run()
    assert not at.error, [str(item.value) for item in at.error]
    snapshot = at.session_state.get("snapshot") or {}
    assert snapshot.get("status") == "awaiting_approval", snapshot.get("status")
    assert snapshot.get("next") == ["executor"], snapshot.get("next")
    assert labels(at.tabs) == EXPECTED_TABS, labels(at.tabs)
    assert "批准并执行 dry-run" in labels(at.button)
    assert "拒绝" in labels(at.button)

    button(at, "批准并执行 dry-run").click()
    at.run()
    assert not at.error, [str(item.value) for item in at.error]
    snapshot = at.session_state.get("snapshot") or {}
    state = snapshot.get("state") or {}
    assert snapshot.get("status") == "completed", snapshot.get("status")
    assert (snapshot.get("metrics") or {}).get("approved") is True
    assert len(state.get("execution_log") or []) == EXPECTED_ACTIONS
    assert all(
        item.get("status") == "dry_run_success"
        for item in state.get("execution_log") or []
    )
    assert (state.get("compliance_report") or {}).get("passed") is True
    assert labels(at.tabs) == EXPECTED_TABS

    button(at, "运行流水线").click()
    at.run()
    snapshot = at.session_state.get("snapshot") or {}
    assert snapshot.get("status") == "awaiting_approval", snapshot.get("status")
    button(at, "拒绝").click()
    at.run()
    assert not at.error, [str(item.value) for item in at.error]
    snapshot = at.session_state.get("snapshot") or {}
    state = snapshot.get("state") or {}
    assert snapshot.get("status") == "completed", snapshot.get("status")
    assert (snapshot.get("metrics") or {}).get("approved") is False
    log = state.get("execution_log") or []
    assert len(log) == 1, len(log)
    assert log[0].get("status") == "rejected", log[0].get("status")

    print(
        "UI_VERIFY_OK tabs=6 awaiting_approval=ok "
        "approve=5_dry_run reject=1_skip errors=0"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
