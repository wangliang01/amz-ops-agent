from __future__ import annotations

import os
from typing import Any

import requests
import streamlit as st

st.set_page_config(
    page_title="amz-ops-agent",
    page_icon="📦",
    layout="wide",
)


def api_base() -> str:
    return st.session_state.get(
        "api_base", os.getenv("API_BASE_URL", "http://localhost:8000")
    ).rstrip("/")


def load_skus(base: str) -> tuple[list[dict[str, Any]], str | None]:
    try:
        res = requests.get(f"{base}/skus", timeout=10)
        res.raise_for_status()
        return res.json(), None
    except Exception as exc:
        return [], str(exc)


def post(path: str, payload: dict[str, Any], timeout: int = 300) -> dict[str, Any]:
    res = requests.post(f"{api_base()}{path}", json=payload, timeout=timeout)
    res.raise_for_status()
    return res.json()


def get(path: str, timeout: int = 30) -> dict[str, Any]:
    res = requests.get(f"{api_base()}{path}", timeout=timeout)
    res.raise_for_status()
    return res.json()


def show_table(rows: list[dict[str, Any]] | None) -> None:
    if not rows:
        st.caption("No rows.")
        return
    st.dataframe(rows, width="stretch", hide_index=True)


st.title("amz-ops-agent")
st.caption(
    "Multi-Agent Operations Copilot for Amazon Sellers · "
    "LangGraph + RAG + FastAPI · synthetic demo data"
)

with st.sidebar:
    st.subheader("Connection")
    base_input = st.text_input(
        "API base URL",
        value=st.session_state.get(
            "api_base", os.getenv("API_BASE_URL", "http://localhost:8000")
        ),
    )
    st.session_state["api_base"] = base_input.rstrip("/")

    st.divider()
    st.subheader("Run")
    skus, error = load_skus(api_base())
    if error:
        st.error(f"API not reachable: {error}")
        st.code("uvicorn api.main:app --reload", language="powershell")
        sku_id = "SKU-003"
        mode = "full_chain"
    else:
        labels = {
            item["sku_id"]: (
                f"{item['sku_id']} · {item['subcategory']} · ${item['price']:.2f}"
            )
            for item in skus
        }
        default_index = next(
            (
                index
                for index, item in enumerate(skus)
                if item["sku_id"] == "SKU-003"
            ),
            0,
        )
        sku_id = st.selectbox(
            "SKU",
            list(labels),
            index=default_index,
            format_func=lambda value: labels[value],
        )
        mode = st.selectbox(
            "Mode",
            ["full_chain", "listing_only", "ads_only", "auto"],
            index=0,
        )

    run_disabled = bool(error)
    if st.button(
        "Run pipeline",
        type="primary",
        width="stretch",
        disabled=run_disabled,
    ):
        with st.spinner("Running agents... this can take 30-60s with an LLM."):
            try:
                st.session_state["snapshot"] = post(
                    "/runs", {"sku_id": sku_id, "mode": mode}
                )
            except Exception as exc:
                st.error(f"Run failed: {exc}")
            else:
                st.rerun()

    snapshot = st.session_state.get("snapshot")
    if snapshot and snapshot.get("status") == "awaiting_approval":
        st.divider()
        st.caption("HITL gate: the executor is paused until you decide.")
        approve_col, reject_col = st.columns(2)
        if approve_col.button("Approve", type="primary", width="stretch"):
            with st.spinner("Executing dry-run..."):
                try:
                    st.session_state["snapshot"] = post(
                        f"/runs/{snapshot['run_id']}/approve",
                        {"decision": "approved", "actor": "streamlit"},
                    )
                except Exception as exc:
                    st.error(f"Approval failed: {exc}")
                else:
                    st.rerun()
        if reject_col.button("Reject", width="stretch"):
            try:
                st.session_state["snapshot"] = post(
                    f"/runs/{snapshot['run_id']}/approve",
                    {"decision": "rejected", "actor": "streamlit"},
                )
            except Exception as exc:
                st.error(f"Rejection failed: {exc}")
            else:
                st.rerun()

if not snapshot:
    st.info("Select a SKU in the sidebar and click **Run pipeline**.")
    st.markdown(
        """
        **What the run does**

        1. **Insight Agent** clusters review pain points and quotes the evidence.
        2. **Listing Agent** retrieves high-converting listings + policy docs and drafts new copy.
        3. **Compliance Agent** checks 21 rules against both the current and new listing.
        4. **Ads Agent** diagnoses 90 days of ad data, proposes bids, and backtests 30 days.
        5. **Executor** waits for human approval, then logs a dry-run action trail.
        """
    )
    st.stop()

state = snapshot.get("state") or {}
metrics = snapshot.get("metrics") or {}
insights = state.get("insights") or {}
listing = state.get("draft_listing") or {}
compliance = state.get("compliance_report") or {}
ads = state.get("ads_report") or {}
last30 = ads.get("last_30d") or {}
backtest = ads.get("backtest") or {}

metric_cols = st.columns(6)
metric_cols[0].metric("Status", str(snapshot.get("status", "unknown")))
metric_cols[1].metric(
    "Compliance", "PASS" if compliance.get("passed") else "CHECK"
)
metric_cols[2].metric("ACOS 30d", f"{float(last30.get('acos') or 0):.1%}")
pipeline_sec = metrics.get("pipeline_sec")
if pipeline_sec is None:
    pipeline_sec = sum(
        float(value) for value in (metrics.get("node_times") or {}).values()
    )
metric_cols[3].metric("Pipeline", f"{float(pipeline_sec):.2f}s")
metric_cols[4].metric("LLM calls", int(metrics.get("llm_calls") or 0))
metric_cols[5].metric("Cost", f"${float(metrics.get('cost_usd') or 0):.4f}")

tabs = st.tabs(
    ["Insight", "Listing", "Compliance", "Ads", "Audit", "Metrics"]
)

with tabs[0]:
    st.subheader("Review insight")
    st.write(insights.get("summary") or "No insight generated.")
    pain_rows = [
        {
            "theme": item.get("theme"),
            "frequency": item.get("frequency"),
            "quotes": " | ".join(item.get("quotes") or []),
        }
        for item in insights.get("pain_points") or []
    ]
    st.markdown("**Pain points**")
    show_table(pain_rows)
    st.markdown("**Positive themes**")
    show_table(insights.get("positive_themes") or [])
    st.markdown("**Competitor gaps**")
    for gap in insights.get("competitor_gaps") or []:
        st.write(f"- {gap}")
    with st.expander("Raw insight JSON"):
        st.json(insights)

with tabs[1]:
    st.subheader("Listing draft")
    current = (state.get("sku") or {}).get("current_listing") or {}
    left, right = st.columns(2)
    with left:
        st.markdown("**Current listing**")
        st.write(current.get("title") or "—")
        for bullet in current.get("bullets") or []:
            st.write(f"- {bullet}")
        st.caption(current.get("description") or "")
    with right:
        st.markdown("**New draft**")
        st.write(listing.get("title") or "—")
        st.caption(f"{len(listing.get('title') or '')} characters")
        for bullet in listing.get("bullets") or []:
            st.write(f"- {bullet}")
        st.caption(listing.get("description") or "")
    st.markdown("**Backend keywords**")
    st.write(", ".join(listing.get("backend_keywords") or []) or "—")
    st.markdown("**Citations**")
    st.write(", ".join(listing.get("citations") or []) or "—")
    st.caption(listing.get("rationale") or "")
    with st.expander("Retrieved evidence"):
        show_table(state.get("retrieved_docs") or [])

with tabs[2]:
    st.subheader("Compliance review")
    c1, c2, c3 = st.columns(3)
    c1.metric("Result", "PASS" if compliance.get("passed") else "BLOCKED")
    c2.metric("Score", int(compliance.get("score") or 0))
    c3.metric("Issues fixed", int(compliance.get("fixed_count") or 0))
    st.markdown("**Draft issues**")
    show_table(compliance.get("draft_issues") or [])
    st.markdown("**Current listing issues**")
    show_table(compliance.get("current_listing_issues") or [])
    st.caption(
        f"Checked {compliance.get('checked_rules') or 0} rules · "
        f"citations: {', '.join(compliance.get('citations') or []) or '—'}"
    )

with tabs[3]:
    st.subheader("Ads diagnosis")
    st.write(ads.get("diagnosis") or "No diagnosis generated.")
    st.markdown("**30-day performance**")
    perf_rows = []
    for label, payload in [
        ("Last 30 days", ads.get("last_30d") or {}),
        ("Previous 30 days", ads.get("previous_30d") or {}),
    ]:
        perf_rows.append({"window": label, **payload})
    show_table(perf_rows)
    st.markdown("**Anomalies**")
    show_table(ads.get("anomalies") or [])
    st.markdown("**Bid recommendations**")
    show_table(ads.get("recommendations") or [])
    st.markdown("**30-day backtest**")
    b1, b2, b3 = st.columns(3)
    b1.metric(
        "Baseline ACOS",
        f"{float((backtest.get('baseline') or {}).get('acos') or 0):.1%}",
    )
    b2.metric(
        "Projected ACOS",
        f"{float((backtest.get('projected') or {}).get('acos') or 0):.1%}",
    )
    b3.metric(
        "Projected spend delta",
        f"${float((backtest.get('delta') or {}).get('spend') or 0):,.2f}",
    )
    st.caption(backtest.get("assumption") or "")
    with st.expander("Backtest detail"):
        st.json(backtest)

with tabs[4]:
    st.subheader("Execution and audit")
    st.markdown("**Execution log**")
    show_table(state.get("execution_log") or [])
    st.markdown("**Proposals**")
    show_table(state.get("proposals") or [])
    if not state.get("execution_log"):
        st.caption("The executor is waiting for approval in the sidebar.")

with tabs[5]:
    st.subheader("Run metrics")
    st.json(metrics)
    st.markdown("**Node latency (seconds)**")
    node_times = metrics.get("node_times") or {}
    if node_times:
        st.bar_chart(node_times)
    st.markdown("**Aggregate metrics**")
    try:
        st.json(get("/metrics"))
    except Exception as exc:
        st.caption(f"Could not load aggregate metrics: {exc}")
    with st.expander("Demo script (5 minutes)"):
        st.markdown(
            """
            1. Pick `SKU-003` — low rating, high ACOS.
            2. Run the pipeline and open **Insight**: pain points quote real review text.
            3. Open **Listing**: the draft cites a historical high-converting listing.
            4. Open **Compliance**: the current listing has 6 issues; the draft has 0.
            5. Open **Ads**: ACOS 97%, spend spike, 5 bid cuts, 30-day backtest.
            6. Approve in the sidebar: the executor writes a dry-run audit trail.
            7. Open **Metrics**: latency, token cost, compliance result.
            """
        )
