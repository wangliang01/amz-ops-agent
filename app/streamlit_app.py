from __future__ import annotations

import html
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import requests
import streamlit as st

APP_DIR = Path(__file__).resolve().parent
MARK = APP_DIR / "assets" / "mark.png"

st.set_page_config(
    page_title="amz-ops-agent · 运营副驾驶",
    page_icon=str(MARK) if MARK.exists() else "▦",
    layout="wide",
    initial_sidebar_state="expanded",
)

CSS = """
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&display=swap');

:root {
  --primary-color: #9C631C;
  --background-color: #F7F4ED;
  --secondary-background-color: #FFFDF8;
  --text-color: #1F1D1A;
  --paper: #F7F4ED;
  --surface: #FFFDF8;
  --raised: #EFEAE0;
  --ink: #1F1D1A;
  --secondary: #5E574C;
  --muted: #756D60;
  --line: rgba(31, 29, 26, .12);
  --line-strong: rgba(31, 29, 26, .22);
  --brass: #9C631C;
  --brass-dark: #8A5515;
  --brass-soft: #F1E4CF;
  --pass: #2F6B4F;
  --block: #A33A32;
  --warn: #8A5A12;
  --radius: 14px;
  --font-sans: "IBM Plex Sans", "Microsoft YaHei", "PingFang SC", "Segoe UI", system-ui, sans-serif;
  --font-mono: "IBM Plex Mono", "Cascadia Mono", "Consolas", monospace;
}

html, body, .stApp, [class*="css"] {
  font-family: var(--font-sans);
  color: var(--ink);
}
.stApp, [data-testid="stAppViewContainer"] { background: var(--paper); }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stToolbar"] { background: transparent; }
[data-testid="stAppDeployButton"],
[data-testid="stMainMenu"],
[data-testid="stStatusWidget"],
[data-testid="stElementToolbar"] { display: none !important; }
[data-testid="stMainBlockContainer"] {
  max-width: 1280px;
  margin: 0 auto;
  padding: 24px 32px 64px;
}
[data-testid="stSidebar"] {
  background: var(--surface);
  border-right: 1px solid var(--line);
}
[data-testid="stSidebarContent"] { background: var(--surface); }
[data-testid="stSidebarUserContent"] { padding: 8px 20px 24px; }
[data-testid="stSidebarHeader"] { padding: 12px 20px 0; }

h1, h2, h3, h4 { color: var(--ink); letter-spacing: -.01em; }
p, li { color: var(--secondary); }
[data-testid="stCaptionContainer"] { color: var(--muted); }
[data-testid="stWidgetLabel"] p { color: var(--secondary); font-size: 12px; }

/* Buttons */
[data-testid="stButton"] button,
[data-testid="stBaseButton-secondary"] {
  border-radius: 8px;
  border: 1px solid var(--line-strong);
  background: var(--surface);
  color: var(--ink);
  font-weight: 500;
  min-height: 40px;
  box-shadow: none;
  transition: background-color .15s ease, border-color .15s ease, color .15s ease;
}
[data-testid="stButton"] button:hover,
[data-testid="stBaseButton-secondary"]:hover {
  border-color: var(--ink);
  background: var(--raised);
}
[data-testid="stButton"] button[kind="primary"],
[data-testid="stBaseButton-primary"] {
  background: var(--brass);
  border-color: var(--brass);
  color: #FFF9EE;
}
[data-testid="stButton"] button[kind="primary"] p,
[data-testid="stButton"] button[kind="primary"] span,
[data-testid="stBaseButton-primary"] p,
[data-testid="stBaseButton-primary"] span {
  color: #FFF9EE !important;
}
[data-testid="stButton"] button[kind="primary"]:hover,
[data-testid="stBaseButton-primary"]:hover {
  background: var(--brass-dark);
  border-color: var(--brass-dark);
}
[data-testid="stButton"] button:focus-visible,
[data-testid="stBaseButton-primary"]:focus-visible,
[data-testid="stBaseButton-secondary"]:focus-visible,
[data-testid="stTextInput"] input:focus-visible,
[data-testid="stSelectbox"] [data-baseweb="select"]:focus-within,
[data-testid="stSelectbox"] input:focus-visible,
[data-testid="stTabs"] [role="tab"]:focus-visible,
[data-testid="stTab"]:focus-visible,
[data-testid="stExpander"] summary:focus-visible {
  outline: 2px solid var(--brass);
  outline-offset: 2px;
}
button:focus-visible,
a:focus-visible {
  outline: 2px solid var(--brass);
  outline-offset: 2px;
}
[data-testid="stBaseButton-headerNoPadding"]:focus-visible,
[data-testid="stSidebarCollapseButton"] button:focus-visible,
[data-testid="stSkipToContent"]:focus-visible {
  outline: 2px solid var(--brass) !important;
  outline-offset: 2px;
}
[data-testid="stButton"] button:disabled {
  opacity: .45;
  cursor: not-allowed;
}

/* Inputs */
[data-testid="stTextInput"] [data-baseweb="input"],
[data-testid="stSelectbox"] [data-baseweb="select"] > div {
  background: var(--surface);
  border-color: var(--line-strong);
  border-radius: 8px;
  color: var(--ink);
}
[data-testid="stTextInput"] input,
[data-testid="stSelectbox"] input {
  color: var(--ink);
  font-family: var(--font-sans);
}
[data-baseweb="select"] [role="listbox"] { background: var(--surface); }

/* Tabs */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
  gap: 2px;
  border-bottom: 1px solid var(--line);
  background: transparent;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
  height: 40px;
  padding: 0 14px;
  color: var(--muted);
  font-weight: 500;
  background: transparent;
}
[data-testid="stTabs"] [data-baseweb="tab"]:hover { color: var(--ink); }
[data-testid="stTabs"] [aria-selected="true"] { color: var(--ink); }
[data-testid="stTabs"] [data-baseweb="tab-highlight"] {
  background: var(--brass);
  height: 2px;
}
[data-testid="stTabs"] [data-baseweb="tab-border"] { background: var(--line); }
[data-testid="stTabPanel"] { padding-top: 22px; }

/* Expander / JSON */
[data-testid="stExpander"] details {
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--surface);
}
[data-testid="stExpander"] summary { font-weight: 500; color: var(--secondary); }
[data-testid="stExpander"] summary:hover { color: var(--ink); }
[data-testid="stJson"] {
  background: var(--raised);
  border-radius: 10px;
  padding: 12px;
}

/* Brand */
.side-brand { display: flex; align-items: center; gap: 10px; padding: 4px 0 2px; }
.side-brand-name { font-size: 17px; font-weight: 600; letter-spacing: -.01em; color: var(--ink); }
.brand-mark {
  width: 18px; height: 18px; border: 1.5px solid var(--ink);
  position: relative; display: inline-block; flex: 0 0 18px;
}
.brand-mark::after {
  content: ""; position: absolute; inset: 4px; background: var(--brass);
}
.side-note { color: var(--muted); font-size: 12px; margin: 2px 0 14px; }
.side-rule { height: 1px; background: var(--line); margin: 0 0 14px; }
.side-section-label {
  font-size: 12px; color: var(--muted); margin: 18px 0 6px;
}
.side-foot {
  margin-top: 26px; padding-top: 14px; border-top: 1px solid var(--line);
  color: var(--muted); font-size: 11px; line-height: 1.6;
}

/* Header */
.app-head {
  display: flex; justify-content: space-between; align-items: flex-start;
  gap: 24px; margin: 4px 0 24px;
}
.brand-row { display: flex; align-items: center; gap: 12px; }
.brand-name { font-size: 30px; font-weight: 600; letter-spacing: -.03em; color: var(--ink); }
.lede {
  max-width: 720px; margin: 10px 0 0; color: var(--secondary);
  font-size: 15px; line-height: 1.65;
}
.demo-tag {
  font-family: var(--font-mono); font-size: 11px; color: var(--muted);
  border: 1px solid var(--line); padding: 4px 8px; border-radius: 4px;
  white-space: nowrap;
}

/* Status band */
.status-band {
  display: grid; grid-template-columns: 2fr repeat(4, 1fr);
  gap: 12px; margin: 24px 0 28px;
}
.gate-card, .stat, .score-card, .panel, .paper-card, .compare-card {
  background: var(--surface); border: 1px solid var(--line);
  border-radius: var(--radius);
}
.gate-card {
  position: relative; padding: 18px 20px; min-height: 112px;
  border-left: 3px solid var(--brass);
  background: #FCF8F0;
}
.gate-card.gate-closed { border-left-color: var(--pass); }
.gate-card.gate-rejected { border-left-color: var(--block); }
.gate-kicker, .stat-label, .panel-kicker, .card-kicker, .detail-label {
  font-size: 11px; color: var(--muted);
}
.gate-status { font-size: 27px; font-weight: 600; margin-top: 6px; letter-spacing: -.02em; }
.gate-detail { font-size: 12px; color: var(--secondary); line-height: 1.5; margin-top: 4px; max-width: 360px; }
.gate-stamp {
  position: absolute; top: 14px; right: 16px;
  font-family: var(--font-mono); font-size: 10px; color: var(--brass);
  border: 1px solid var(--brass); padding: 2px 5px; border-radius: 3px;
  transform: rotate(-2deg);
}
.gate-closed .gate-stamp { color: var(--pass); border-color: var(--pass); }
.gate-rejected .gate-stamp { color: var(--block); border-color: var(--block); }
.stat {
  padding: 16px; min-height: 112px;
  display: flex; flex-direction: column; justify-content: space-between;
}
.stat-value {
  font-family: var(--font-mono); font-size: 23px; font-weight: 500;
  font-variant-numeric: tabular-nums; color: var(--ink); line-height: 1.2;
}
.stat-note { font-size: 11px; color: var(--muted); }
.pass-text { color: var(--pass); }
.block-text { color: var(--block); }
.warn-text { color: var(--warn); }

/* Empty state */
.empty-wrap { display: grid; grid-template-columns: 1.45fr 1fr; gap: 20px; margin-top: 6px; }
.panel { padding: 24px; }
.panel-title { font-size: 21px; font-weight: 600; margin: 6px 0 8px; color: var(--ink); }
.panel-lede { font-size: 13px; line-height: 1.6; margin: 0 0 12px; color: var(--secondary); }
.run-sheet { list-style: none; padding: 0; margin: 14px 0 0; }
.run-step {
  display: grid; grid-template-columns: 34px 1fr; gap: 12px;
  padding: 11px 0; border-top: 1px solid var(--line);
}
.run-step:first-child { border-top: 0; }
.step-index { font-family: var(--font-mono); font-size: 11px; color: var(--muted); padding-top: 2px; }
.run-step strong { font-weight: 500; color: var(--ink); font-size: 14px; }
.run-step p { margin: 2px 0 0; font-size: 12px; line-height: 1.5; }
.run-step.gate {
  border-left: 2px solid var(--brass); margin-left: -16px;
  padding-left: 14px;
}
.run-step.gate .step-index { color: var(--brass); }
.rule-list { list-style: none; padding: 0; margin: 12px 0 0; }
.rule-list li {
  display: grid; grid-template-columns: 72px 1fr; gap: 10px;
  padding: 10px 0; border-top: 1px solid var(--line); font-size: 13px;
}
.rule-list li:first-child { border-top: 0; }
.rule-list strong { font-weight: 500; color: var(--ink); }
.panel-note {
  margin: 16px 0 0; padding-top: 12px; border-top: 1px solid var(--line);
  font-size: 11px; color: var(--muted);
}

/* Sidebar gate */
.gate-panel {
  border: 1px solid var(--line); border-left: 3px solid var(--brass);
  border-radius: 10px; padding: 12px 14px; background: var(--surface);
  margin-bottom: 10px;
}
.gate-panel.closed { border-left-color: var(--pass); }
.gate-panel.rejected { border-left-color: var(--block); }
.gate-panel.idle { border-left-color: var(--line-strong); }
.gate-panel-title { font-weight: 500; color: var(--ink); font-size: 14px; }
.gate-panel p { margin: 4px 0 0; font-size: 12px; line-height: 1.5; color: var(--secondary); }

/* Content */
.lead {
  font-size: 16px; line-height: 1.7; color: var(--ink);
  margin: 0 0 20px; max-width: 860px;
}
.section-title { font-size: 14px; font-weight: 500; color: var(--ink); margin: 22px 0 10px; }
.empty-row {
  border: 1px dashed var(--line-strong); border-radius: 10px;
  padding: 14px 16px; color: var(--muted); font-size: 12px;
}
.muted { color: var(--muted); }
.rationale { font-size: 12px; line-height: 1.6; margin-top: 10px; }

/* Pain points */
.pain-list { display: flex; flex-direction: column; gap: 12px; }
.pain-row {
  background: var(--surface); border: 1px solid var(--line);
  border-radius: 10px; padding: 12px 14px;
}
.pain-head { display: flex; justify-content: space-between; align-items: baseline; gap: 12px; }
.pain-theme { font-weight: 500; color: var(--ink); font-size: 14px; }
.pain-count { font-family: var(--font-mono); font-size: 12px; color: var(--secondary); }
.pain-track {
  height: 5px; background: var(--raised); border-radius: 3px;
  overflow: hidden; margin: 8px 0 6px;
}
.pain-track > span { display: block; height: 100%; background: var(--brass); }
.pain-quote { margin: 0; font-size: 12px; line-height: 1.5; color: var(--muted); }
.gap-list { margin: 0; padding-left: 18px; }
.gap-list li { font-size: 13px; line-height: 1.7; color: var(--secondary); }

/* Tables */
.table-wrap {
  overflow-x: auto; border: 1px solid var(--line);
  border-radius: 10px; background: var(--surface);
}
.table-wrap table { width: 100%; border-collapse: collapse; font-size: 12.5px; }
.table-wrap th {
  text-align: left; font-weight: 500; color: var(--muted);
  padding: 9px 12px; border-bottom: 1px solid var(--line);
  white-space: nowrap; background: var(--surface);
}
.table-wrap td {
  padding: 9px 12px; border-bottom: 1px solid var(--line);
  vertical-align: top; color: var(--secondary);
}
.table-wrap tr:last-child td { border-bottom: 0; }
.table-wrap .num {
  text-align: right; font-family: var(--font-mono);
  font-variant-numeric: tabular-nums; color: var(--ink);
}
.table-wrap .mono { font-family: var(--font-mono); font-size: 11.5px; color: var(--secondary); }
.table-wrap.wide-first table { table-layout: fixed; }
.table-wrap.wide-first th:first-child { width: 25%; }
.table-wrap.wide-first th:nth-child(2),
.table-wrap.wide-first th:nth-child(3),
.table-wrap.wide-first th:nth-child(4) { width: 25%; }
.cell-note { color: var(--muted); font-size: 11.5px; margin-top: 2px; }
.severity { display: inline-flex; align-items: center; gap: 6px; font-size: 12px; white-space: nowrap; }
.dot { width: 7px; height: 7px; border-radius: 50%; display: inline-block; }
.dot.block { background: var(--block); }
.dot.warn { background: var(--warn); }
.dot.info { background: var(--muted); }
.dot.pass { background: var(--pass); }

/* Listing */
.two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.paper-card { padding: 20px; }
.paper-card.draft { border-top: 3px solid var(--brass); }
.paper-card h3 { font-size: 17px; line-height: 1.45; margin: 6px 0 8px; font-weight: 600; }
.paper-card .meta { font-family: var(--font-mono); font-size: 11px; color: var(--muted); }
.paper-card ul { margin: 12px 0; padding-left: 18px; }
.paper-card li { font-size: 13px; line-height: 1.6; color: var(--secondary); }
.paper-card .card-desc { font-size: 12px; line-height: 1.6; color: var(--muted); margin: 10px 0 0; }
.detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 18px; }
.detail-block { background: var(--surface); border: 1px solid var(--line); border-radius: 10px; padding: 14px 16px; }
.tag-row { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px; }
.tag {
  font-family: var(--font-mono); font-size: 11px; color: var(--secondary);
  background: var(--raised); border: 1px solid var(--line);
  padding: 2px 6px; border-radius: 4px;
}

/* Compliance */
.score-band { display: grid; grid-template-columns: 1.5fr repeat(3, 1fr); gap: 12px; margin-bottom: 20px; }
.score-card { padding: 18px 20px; }
.score-value {
  font-family: var(--font-mono); font-size: 38px; font-weight: 500;
  font-variant-numeric: tabular-nums; color: var(--ink); line-height: 1.1; margin-top: 4px;
}
.score-track { height: 6px; background: var(--raised); border-radius: 3px; overflow: hidden; margin: 10px 0 8px; }
.score-track > span { display: block; height: 100%; background: var(--pass); }
.score-note { font-size: 12px; font-weight: 500; }

/* Ads */
.compare-card { padding: 18px 20px; margin-top: 8px; }
.compare-head {
  display: flex; justify-content: space-between; align-items: baseline;
  font-size: 12px; color: var(--muted); margin-bottom: 12px;
}
.compare-row {
  display: grid; grid-template-columns: 92px 1fr 64px; gap: 12px;
  align-items: center; margin: 8px 0; font-size: 12px; color: var(--secondary);
}
.compare-track { height: 8px; background: var(--raised); border-radius: 4px; overflow: hidden; }
.compare-track > span { display: block; height: 100%; background: var(--secondary); }
.compare-row.accent .compare-track > span { background: var(--brass); }
.compare-foot {
  margin-top: 12px; padding-top: 10px; border-top: 1px solid var(--line);
  font-size: 12px; color: var(--muted);
}
.compare-foot strong { color: var(--ink); font-weight: 500; }

/* Bars */
.bar-list { display: flex; flex-direction: column; gap: 9px; }
.bar-row {
  display: grid; grid-template-columns: 130px 1fr 56px; gap: 12px;
  align-items: center;
}
.bar-label { font-size: 12px; color: var(--secondary); }
.bar-track { height: 6px; background: var(--raised); border-radius: 3px; overflow: hidden; }
.bar-track > span { display: block; height: 100%; background: var(--secondary); }
.bar-row.accent .bar-track > span { background: var(--brass); }
.bar-value {
  font-family: var(--font-mono); font-size: 11.5px;
  font-variant-numeric: tabular-nums; color: var(--ink); text-align: right;
}
.mini-band { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin: 16px 0 20px; }

/* Error */
.error-card {
  background: #FBEFEC; border: 1px solid rgba(163, 58, 50, .25);
  border-left: 3px solid var(--block); border-radius: 10px;
  padding: 14px 16px; margin: 0 0 18px;
}
.error-title { font-weight: 500; color: var(--block); font-size: 14px; }
.error-card p { margin: 4px 0 0; font-size: 12px; line-height: 1.5; color: var(--secondary); }
.error-hint { color: var(--muted); }
.error-card code {
  display: inline-block; margin-top: 6px; font-family: var(--font-mono);
  font-size: 11px; background: var(--surface); border: 1px solid var(--line);
  padding: 3px 6px; border-radius: 4px; color: var(--ink);
}

/* Responsive */
@media (max-width: 1100px) {
  .status-band { grid-template-columns: 1fr 1fr; }
  .gate-card { grid-column: 1 / -1; }
  .empty-wrap { grid-template-columns: 1fr; }
  .score-band { grid-template-columns: 1fr 1fr; }
  .two-col, .detail-grid { grid-template-columns: 1fr; }
}
@media (max-width: 700px) {
  [data-testid="stMainBlockContainer"] { padding: 18px 16px 48px; }
  .app-head { flex-direction: column; gap: 10px; }
  .brand-name { font-size: 25px; }
  .status-band, .score-band, .mini-band { grid-template-columns: 1fr; }
  .bar-row { grid-template-columns: 1fr 56px; }
  .bar-track { grid-column: 1 / -1; order: 3; }
  .compare-row { grid-template-columns: 76px 1fr 56px; }
  .rule-list li { grid-template-columns: 1fr; gap: 2px; }
}
@media (prefers-reduced-motion: reduce) {
  * { transition: none !important; animation: none !important; }
}
"""


MODE_LABELS = {
    "full_chain": "全链路",
    "listing_only": "仅 Listing",
    "ads_only": "仅广告",
    "auto": "自动选择",
}
PAIN_LABELS = {
    "blending power": "搅拌力",
    "battery life": "续航",
    "noise": "噪音",
    "durability": "耐用性",
    "leaks": "漏水",
    "hard to clean": "难清洁",
    "size/fit": "尺寸与容量",
    "quality": "质量",
}
POSITIVE_LABELS = {
    "portability": "便携",
    "ease of use": "易用",
    "value": "性价比",
    "performance": "性能",
}
ACTION_LABELS = {
    "adjust_bid": "调整出价",
    "decrease_bid": "降价",
    "increase_bid": "提价",
    "skip": "跳过",
}
EXEC_STATUS_LABELS = {
    "dry_run_success": "dry-run 成功",
    "rejected": "已拒绝",
    "no_approval": "未审批",
}
SEVERITY_LABELS = {
    "block": "拦截",
    "warn": "警告",
    "info": "提示",
    "high": "高",
    "medium": "中",
    "low": "低",
}
CATEGORY_LABELS = {
    "prohibited_claim": "禁用声明",
    "prohibited_claims": "禁用声明",
    "medical_claim": "医疗声明",
    "certification": "认证",
    "guarantee": "保证承诺",
    "origin": "产地",
    "promotion": "促销",
    "format": "格式",
    "contact": "联系方式",
    "emoji": "表情符号",
    "llm_review": "模型复核",
}
FIELD_LABELS = {
    "title": "标题",
    "description": "描述",
    "bullets": "五点描述",
}
ANOMALY_LABELS = {
    "high_acos": "ACOS 偏高",
    "wasted_spend": "花费浪费",
    "low_ctr": "点击率偏低",
    "low_cvr": "转化率偏低",
}
NODE_LABELS = {
    "supervisor": "调度",
    "insight": "洞察",
    "listing": "Listing",
    "compliance": "合规",
    "ads": "广告",
    "executor": "执行器",
}
FALLBACK_DIAGNOSIS = (
    "Rule-based diagnosis: high ACOS keywords are driving spend "
    "without matching sales."
)

_THEME_ZH = {
    **PAIN_LABELS,
    **POSITIVE_LABELS,
    "none": "无",
}


def zh_theme(text: str) -> str:
    """Translate rule-based theme labels while leaving model prose untouched."""
    return _THEME_ZH.get(text.strip().lower(), text)


def zh_gap(text: Any) -> str:
    """Translate the deterministic fallback gap template to Chinese."""
    match = re.fullmatch(
        r"Address '([^']+)' complaints with a clearer claim or design note\.",
        str(text or ""),
    )
    if match:
        return f"针对「{zh_theme(match.group(1))}」投诉，补充更清晰的卖点或设计说明。"
    return str(text or "")


def zh_anomaly(kind: Any, severity: Any, detail: Any) -> str:
    """Translate deterministic rule-based anomaly details."""
    key = str(kind or "")
    if key == "high_acos":
        return "ACOS 高于目标，预算效率偏低。"
    if key == "wasted_spend" and str(detail or "").startswith("Spend +"):
        return "花费上涨但销售额没有同步增长。"
    if key == "low_ctr" and "0.35%" in str(detail or ""):
        return "点击率低于 0.35% 演示基准。"
    if key == "low_cvr" and "6%" in str(detail or ""):
        return "转化率低于 6% 演示基准。"
    return str(detail or "")


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


def e(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def fmt_pct(value: Any, digits: int = 1) -> str:
    try:
        return f"{float(value):.{digits}%}"
    except (TypeError, ValueError):
        return "—"


def fmt_signed_pct(value: Any) -> str:
    try:
        return f"{float(value):+.1%}"
    except (TypeError, ValueError):
        return "—"


def fmt_signed_pp(current: Any, previous: Any) -> str:
    try:
        return f"{float(current) - float(previous):+.1%}"
    except (TypeError, ValueError):
        return "—"


def fmt_money(value: Any, digits: int = 2) -> str:
    try:
        return f"${float(value):,.{digits}f}"
    except (TypeError, ValueError):
        return "—"


def fmt_signed_money(value: Any) -> str:
    try:
        return f"${float(value):+,.2f}"
    except (TypeError, ValueError):
        return "—"


def fmt_num(value: Any) -> str:
    try:
        number = float(value)
        return f"{number:,.0f}" if number.is_integer() else f"{number:,.1f}"
    except (TypeError, ValueError):
        return "—"


def fmt_ts(value: Any) -> str:
    try:
        text = str(value).replace("Z", "+00:00")
        return datetime.fromisoformat(text).strftime("%m-%d %H:%M:%S")
    except (TypeError, ValueError):
        return str(value or "—")


def pain_label(theme: Any) -> str:
    key = str(theme or "")
    return PAIN_LABELS.get(key, key or "—")


def positive_label(theme: Any) -> str:
    key = str(theme or "")
    return POSITIVE_LABELS.get(key, key or "—")


def field_label(field: Any) -> str:
    key = str(field or "")
    if key.startswith("bullet_"):
        return f"五点 {key.split('_', 1)[1]}"
    return FIELD_LABELS.get(key, key or "—")


def action_label(action: Any) -> str:
    key = str(action or "")
    return ACTION_LABELS.get(key, key or "—")


def render_table(
    rows: list[dict[str, Any]],
    columns: list[tuple[str, str, str]],
    empty: str = "暂无数据",
    table_class: str = "",
) -> None:
    if not rows:
        st.markdown(f'<div class="empty-row">{e(empty)}</div>', unsafe_allow_html=True)
        return
    head = "".join(f'<th class="{cls}">{e(label)}</th>' for _, label, cls in columns)
    body: list[str] = []
    for row in rows:
        cells = []
        for key, _, cls in columns:
            value = row.get(key, "")
            if isinstance(value, (list, tuple)):
                value = " · ".join(str(item) for item in value)
            cells.append(f'<td class="{cls}">{e(value)}</td>')
        body.append("<tr>" + "".join(cells) + "</tr>")
    st.markdown(
        f'<div class="table-wrap {table_class}"><table><thead><tr>{head}</tr></thead>'
        f'<tbody>{"".join(body)}</tbody></table></div>',
        unsafe_allow_html=True,
    )


def render_issue_table(issues: list[dict[str, Any]], empty: str) -> None:
    if not issues:
        st.markdown(f'<div class="empty-row">{e(empty)}</div>', unsafe_allow_html=True)
        return
    rows: list[str] = []
    for item in issues:
        severity = str(item.get("severity") or "warn")
        dot = "block" if severity == "block" else "warn" if severity == "warn" else "info"
        rows.append(
            "<tr>"
            f'<td class="mono">{e(item.get("rule_id"))}</td>'
            f'<td><span class="severity"><span class="dot {dot}"></span>'
            f'{e(SEVERITY_LABELS.get(severity, severity))}</span></td>'
            f'<td>{e(CATEGORY_LABELS.get(str(item.get("category")), item.get("category")))}</td>'
            f'<td>{e(field_label(item.get("field")))}</td>'
            f'<td><div>{e(item.get("message"))}</div>'
            f'<div class="cell-note">“{e(item.get("quote"))}”</div></td>'
            f'<td>{e(item.get("suggestion"))}</td>'
            "</tr>"
        )
    st.markdown(
        '<div class="table-wrap"><table><thead><tr>'
        '<th>规则</th><th>级别</th><th>类别</th><th>字段</th><th>问题</th><th>建议</th>'
        f'</tr></thead><tbody>{"".join(rows)}</tbody></table></div>',
        unsafe_allow_html=True,
    )


def render_bars(
    items: list[dict[str, Any]],
    label_fn: Callable[[dict[str, Any]], str],
    value_fn: Callable[[dict[str, Any]], float],
    fmt_fn: Callable[[float], str],
    accent_index: int = 0,
) -> None:
    if not items:
        st.markdown('<div class="empty-row">暂无数据</div>', unsafe_allow_html=True)
        return
    values = [max(0.0, float(value_fn(item) or 0)) for item in items]
    max_value = max(values) if values else 0.0
    rows: list[str] = []
    for index, (item, value) in enumerate(zip(items, values)):
        width = (value / max_value * 100) if max_value else 0.0
        cls = "bar-row accent" if index == accent_index else "bar-row"
        rows.append(
            f'<div class="{cls}"><div class="bar-label">{e(label_fn(item))}</div>'
            f'<div class="bar-track"><span style="width:{width:.1f}%"></span></div>'
            f'<div class="bar-value">{e(fmt_fn(value))}</div></div>'
        )
    st.markdown(f'<div class="bar-list">{"".join(rows)}</div>', unsafe_allow_html=True)


def render_header() -> None:
    st.markdown(
        """
        <div class="app-head">
          <div>
            <div class="brand-row">
              <span class="brand-mark" aria-hidden="true"></span>
              <span class="brand-name">amz-ops-agent</span>
            </div>
            <p class="lede">把评论痛点变成合规的 Listing 草稿和广告出价方案。人工闸门之前，不执行任何动作。</p>
          </div>
          <div class="demo-tag">合成数据 · dry-run 演示</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_error_card(title: str, detail: str) -> None:
    st.markdown(
        f'<div class="error-card"><div class="error-title">{e(title)}</div>'
        "<p>请检查 API 连接后重试。</p></div>",
        unsafe_allow_html=True,
    )
    with st.expander("错误详情"):
        st.caption(str(detail))


def render_gate_panel(snapshot: dict[str, Any] | None, metrics: dict[str, Any]) -> None:
    if not snapshot:
        st.markdown(
            '<div class="gate-panel idle"><div class="gate-panel-title">尚无运行</div>'
            "<p>运行流水线后，执行器会停在这里等你决定。</p></div>",
            unsafe_allow_html=True,
        )
        return

    status = str(snapshot.get("status") or "")
    approved = metrics.get("approved")
    if status == "awaiting_approval":
        st.markdown(
            '<div class="gate-panel open"><div class="gate-panel-title">等待审批</div>'
            "<p>执行器已暂停。批准后写入 dry-run 审计。</p></div>",
            unsafe_allow_html=True,
        )
        if st.button("批准并执行 dry-run", type="primary", use_container_width=True):
            with st.spinner("正在写入 dry-run 审计…"):
                try:
                    st.session_state["snapshot"] = post(
                        f"/runs/{snapshot['run_id']}/approve",
                        {"decision": "approved", "actor": "streamlit"},
                    )
                    st.session_state.pop("last_error", None)
                except Exception as exc:
                    st.session_state["last_error"] = f"批准失败：{exc}"
                st.rerun()
        if st.button("拒绝", use_container_width=True):
            with st.spinner("正在记录拒绝…"):
                try:
                    st.session_state["snapshot"] = post(
                        f"/runs/{snapshot['run_id']}/approve",
                        {"decision": "rejected", "actor": "streamlit"},
                    )
                    st.session_state.pop("last_error", None)
                except Exception as exc:
                    st.session_state["last_error"] = f"拒绝失败：{exc}"
                st.rerun()
    elif status == "completed" and approved is False:
        st.markdown(
            '<div class="gate-panel rejected"><div class="gate-panel-title">已拒绝</div>'
            "<p>本次运行没有执行任何动作。</p></div>",
            unsafe_allow_html=True,
        )
    elif status == "completed":
        st.markdown(
            '<div class="gate-panel closed"><div class="gate-panel-title">已完成</div>'
            "<p>dry-run 审计已记录。</p></div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="gate-panel idle"><div class="gate-panel-title">{e(status or "未知状态")}</div>'
            "<p>等待后端返回下一步。</p></div>",
            unsafe_allow_html=True,
        )


def render_sidebar(snapshot: dict[str, Any] | None, metrics: dict[str, Any]) -> None:
    with st.sidebar:
        st.markdown(
            '<div class="side-brand"><span class="brand-mark" aria-hidden="true"></span>'
            '<span class="side-brand-name">amz-ops-agent</span></div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="side-note">运营副驾驶 · 合成数据</div>', unsafe_allow_html=True)
        st.markdown('<div class="side-rule"></div>', unsafe_allow_html=True)

        with st.expander("API 连接", expanded=bool(st.session_state.get("api_error"))):
            base_input = st.text_input(
                "API 地址",
                value=st.session_state.get(
                    "api_base", os.getenv("API_BASE_URL", "http://localhost:8000")
                ),
            )
            st.session_state["api_base"] = base_input.rstrip("/")
            st.caption("默认 http://localhost:8000")

        skus, error = load_skus(api_base())
        st.session_state["api_error"] = bool(error)

        st.markdown('<div class="side-section-label">运行</div>', unsafe_allow_html=True)
        if error:
            st.markdown(
                '<div class="error-card"><div class="error-title">API 不可达</div>'
                f"<p>无法连接 {e(api_base())}。</p>"
                '<p class="error-hint">先在终端启动 API：</p>'
                "<code>uvicorn api.main:app --reload</code></div>",
                unsafe_allow_html=True,
            )
            with st.expander("错误详情"):
                st.caption(str(error))
            sku_id = "SKU-003"
            mode = "full_chain"
        else:
            labels = {
                item["sku_id"]: f"{item['sku_id']} · ${float(item['price']):.2f}"
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
                "商品 SKU",
                list(labels),
                index=default_index,
                format_func=lambda value: labels[value],
            )
            mode = st.selectbox(
                "运行模式",
                list(MODE_LABELS),
                index=0,
                format_func=lambda value: MODE_LABELS[value],
            )

        run_disabled = bool(error)
        if st.button(
            "运行流水线",
            type="primary",
            use_container_width=True,
            disabled=run_disabled,
        ):
            with st.spinner("正在运行智能体… 启用 LLM 时约 30–60 秒"):
                try:
                    st.session_state["snapshot"] = post(
                        "/runs", {"sku_id": sku_id, "mode": mode}
                    )
                    st.session_state.pop("last_error", None)
                except Exception as exc:
                    st.session_state["last_error"] = f"运行失败：{exc}"
                st.rerun()

        st.markdown('<div class="side-section-label">审批闸门</div>', unsafe_allow_html=True)
        render_gate_panel(snapshot, metrics)
        st.markdown(
            '<div class="side-foot">合成数据 · 仅 dry-run<br>不写真实店铺</div>',
            unsafe_allow_html=True,
        )


def render_empty_state() -> None:
    st.markdown(
        """
        <div class="empty-wrap">
          <div class="panel">
            <div class="panel-kicker">还没有运行</div>
            <h2 class="panel-title">从一次评论洞察开始</h2>
            <p class="panel-lede">在左侧选择 SKU 和运行模式。流水线会依次经过洞察、Listing、合规、广告，然后停在人工闸门前。</p>
            <ol class="run-sheet">
              <li class="run-step"><span class="step-index">01</span><div><strong>洞察</strong><p>聚合评论痛点，引用原文证据。</p></div></li>
              <li class="run-step"><span class="step-index">02</span><div><strong>Listing</strong><p>检索历史高转化 Listing 与政策文档，生成新草稿。</p></div></li>
              <li class="run-step"><span class="step-index">03</span><div><strong>合规</strong><p>按规则检查当前 Listing 与新草稿，标出拦截项。</p></div></li>
              <li class="run-step"><span class="step-index">04</span><div><strong>广告</strong><p>诊断 90 天广告数据，给出出价建议与 30 天回测。</p></div></li>
              <li class="run-step gate"><span class="step-index">05</span><div><strong>审批闸门</strong><p>你批准后，执行器才写 dry-run 审计；拒绝则不执行。</p></div></li>
            </ol>
          </div>
          <div class="panel">
            <div class="panel-kicker">闸门规则</div>
            <h3 class="panel-title">先看结果，再决定是否执行</h3>
            <ul class="rule-list">
              <li><strong>批准</strong><span>执行器写入 5 条 dry-run 审计记录。</span></li>
              <li><strong>拒绝</strong><span>执行器只记录一次跳过，不产生 dry-run。</span></li>
              <li><strong>重复批准</strong><span>幂等，不会重复写审计。</span></li>
            </ul>
            <p class="panel-note">合成数据 · 仅 dry-run，不写真实店铺。</p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_status_band(
    snapshot: dict[str, Any],
    metrics: dict[str, Any],
    state: dict[str, Any],
) -> None:
    status = str(snapshot.get("status") or "")
    approved = metrics.get("approved")
    ads = state.get("ads_report") or {}
    compliance = state.get("compliance_report") or {}
    last30 = ads.get("last_30d") or {}
    target = float(ads.get("target_acos") or 0)

    if status == "awaiting_approval":
        gate_label = "等待审批"
        gate_detail = "执行器已暂停；批准后才会写 dry-run 审计。"
        gate_class = "gate-open"
        stamp = "闸门 · 待批"
    elif status == "completed" and approved is False:
        gate_label = "已拒绝"
        gate_detail = "审批为拒绝；执行器未执行任何动作。"
        gate_class = "gate-rejected"
        stamp = "闸门 · 已拒"
    elif status == "completed":
        gate_label = "已完成"
        gate_detail = "审批已记录；执行器已完成 dry-run。"
        gate_class = "gate-closed"
        stamp = "闸门 · 已批"
    else:
        gate_label = status or "未知状态"
        gate_detail = "等待后端返回下一步。"
        gate_class = "gate-open"
        stamp = "闸门 · 待批"

    pipeline_sec = metrics.get("pipeline_sec")
    if pipeline_sec is None:
        pipeline_sec = sum(
            float(value) for value in (metrics.get("node_times") or {}).values()
        )
    compliance_label = "通过" if compliance.get("passed") else "需复核"
    compliance_class = "pass-text" if compliance.get("passed") else "warn-text"
    acos = float(last30.get("acos") or 0)
    acos_class = "warn-text" if target and acos > target else ""
    llm_calls = int(metrics.get("llm_calls") or 0)

    st.markdown(
        f"""
        <div class="status-band">
          <div class="gate-card {gate_class}">
            <div class="gate-kicker">人工闸门</div>
            <div class="gate-status">{e(gate_label)}</div>
            <div class="gate-detail">{e(gate_detail)}</div>
            <div class="gate-stamp">{e(stamp)}</div>
          </div>
          <div class="stat">
            <div class="stat-label">合规</div>
            <div class="stat-value {compliance_class}">{e(compliance_label)}</div>
            <div class="stat-note">规则检查</div>
          </div>
          <div class="stat">
            <div class="stat-label">30 天 ACOS</div>
            <div class="stat-value {acos_class}">{e(fmt_pct(acos))}</div>
            <div class="stat-note">目标 {e(fmt_pct(target))}</div>
          </div>
          <div class="stat">
            <div class="stat-label">流水线</div>
            <div class="stat-value">{e(f"{float(pipeline_sec):.2f}s")}</div>
            <div class="stat-note">节点耗时合计</div>
          </div>
          <div class="stat">
            <div class="stat-label">模型调用</div>
            <div class="stat-value">{llm_calls}</div>
            <div class="stat-note">无 key 时为 0</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_insight(insights: dict[str, Any]) -> None:
    pain_points = insights.get("pain_points") or []
    gaps = [zh_gap(item) for item in insights.get("competitor_gaps") or []]
    review_count = int(insights.get("review_count") or 0)
    negative_share = insights.get("negative_share")
    top_theme = pain_label(pain_points[0].get("theme")) if pain_points else "—"
    summary = (
        f"{review_count} 条评论，首要痛点是「{top_theme}」，"
        f"负面占比 {fmt_pct(negative_share)}。"
        if review_count
        else "暂无评论洞察。"
    )
    st.markdown(f'<div class="lead">{e(summary)}</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-title">痛点排行</div>', unsafe_allow_html=True)
    if pain_points:
        max_freq = max(int(item.get("frequency") or 0) for item in pain_points) or 1
        rows = []
        for item in pain_points:
            freq = int(item.get("frequency") or 0)
            quotes = item.get("quotes") or []
            quote = quotes[0] if quotes else ""
            more = f"等 {len(quotes)} 条" if len(quotes) > 1 else ""
            rows.append(
                '<div class="pain-row">'
                f'<div class="pain-head"><span class="pain-theme">{e(pain_label(item.get("theme")))}</span>'
                f'<span class="pain-count">{freq} 次</span></div>'
                f'<div class="pain-track"><span style="width:{freq / max_freq * 100:.1f}%"></span></div>'
                f'<p class="pain-quote">“{e(quote)}” {e(more)}</p></div>'
            )
        st.markdown(f'<div class="pain-list">{"".join(rows)}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="empty-row">暂无痛点数据</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-title">正向主题</div>', unsafe_allow_html=True)
    positive = [
        {"theme": positive_label(item.get("theme")), "mentions": item.get("mentions")}
        for item in insights.get("positive_themes") or []
    ]
    render_table(
        positive,
        [("theme", "主题", ""), ("mentions", "提及", "num")],
        "暂无正向主题",
    )

    st.markdown('<div class="section-title">可改进点</div>', unsafe_allow_html=True)
    if gaps:
        st.markdown('<ul class="gap-list">' + "".join(f"<li>{e(gap)}</li>" for gap in gaps) + "</ul>", unsafe_allow_html=True)
    else:
        generated_gaps = [
            f"针对「{pain_label(item.get('theme'))}」投诉，补充更清晰的卖点或设计说明。"
            for item in pain_points[:3]
        ]
        if generated_gaps:
            st.markdown(
                '<ul class="gap-list">' + "".join(f"<li>{e(gap)}</li>" for gap in generated_gaps) + "</ul>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown('<div class="empty-row">暂无改进建议</div>', unsafe_allow_html=True)

    with st.expander("原始洞察数据"):
        st.json(insights)


def listing_card(kicker: str, data: dict[str, Any], draft: bool = False) -> str:
    title = data.get("title") or "—"
    bullets = data.get("bullets") or []
    description = data.get("description") or ""
    cls = "paper-card draft" if draft else "paper-card current"
    bullet_html = "".join(f"<li>{e(item)}</li>" for item in bullets)
    return (
        f'<div class="{cls}"><div class="card-kicker">{e(kicker)}</div>'
        f"<h3>{e(title)}</h3>"
        f'<div class="meta">{len(str(title))} 字符 · {len(bullets)} 条五点</div>'
        f"<ul>{bullet_html}</ul>"
        f'<p class="card-desc">{e(description)}</p></div>'
    )


def render_listing(state: dict[str, Any], listing: dict[str, Any]) -> None:
    current = (state.get("sku") or {}).get("current_listing") or {}
    st.markdown(
        '<div class="two-col">'
        + listing_card("当前 Listing", current)
        + listing_card("新草稿", listing, draft=True)
        + "</div>",
        unsafe_allow_html=True,
    )

    keywords = listing.get("backend_keywords") or []
    citations = listing.get("citations") or []
    keyword_html = "".join(f'<span class="tag">{e(item)}</span>' for item in keywords)
    citation_html = "".join(f'<span class="tag">{e(item)}</span>' for item in citations)
    st.markdown(
        '<div class="detail-grid">'
        '<div class="detail-block"><div class="detail-label">后台关键词</div>'
        f'<div class="tag-row">{keyword_html or "—"}</div></div>'
        '<div class="detail-block"><div class="detail-label">引用证据</div>'
        f'<div class="tag-row">{citation_html or "—"}</div></div>'
        "</div>",
        unsafe_allow_html=True,
    )
    if listing.get("rationale"):
        st.markdown(
            f'<p class="muted rationale">{e(listing.get("rationale"))}</p>',
            unsafe_allow_html=True,
        )

    with st.expander("检索证据"):
        render_table(
            state.get("retrieved_docs") or [],
            [
                ("doc_id", "文档", "mono"),
                ("doc_type", "类型", ""),
                ("title", "标题", ""),
                ("snippet", "摘要", ""),
            ],
            "没有检索到证据",
        )


def render_compliance(compliance: dict[str, Any]) -> None:
    score = int(compliance.get("score") or 0)
    passed = bool(compliance.get("passed"))
    result = "通过" if passed else "需复核"
    result_class = "pass-text" if passed else "block-text"
    draft_issues = compliance.get("draft_issues") or []
    current_issues = compliance.get("current_listing_issues") or []
    checked = int(compliance.get("checked_rules") or 0)
    fixed = int(compliance.get("fixed_count") or 0)

    st.markdown(
        f"""
        <div class="score-band">
          <div class="score-card">
            <div class="stat-label">合规分</div>
            <div class="score-value">{score}</div>
            <div class="score-track"><span style="width:{score}%"></span></div>
            <div class="score-note {result_class}">{e(result)}</div>
          </div>
          <div class="stat">
            <div class="stat-label">检查规则</div>
            <div class="stat-value">{checked}</div>
            <div class="stat-note">条规则</div>
          </div>
          <div class="stat">
            <div class="stat-label">已修复</div>
            <div class="stat-value">{fixed}</div>
            <div class="stat-note">相对当前 Listing</div>
          </div>
          <div class="stat">
            <div class="stat-label">草稿问题</div>
            <div class="stat-value">{len(draft_issues)}</div>
            <div class="stat-note">新草稿</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-title">新草稿问题</div>', unsafe_allow_html=True)
    render_issue_table(draft_issues, "新草稿没有发现问题")
    st.markdown('<div class="section-title">当前 Listing 问题</div>', unsafe_allow_html=True)
    render_issue_table(current_issues, "当前 Listing 没有发现问题")
    citations = compliance.get("citations") or []
    st.markdown(
        f'<p class="muted rationale">检查 {checked} 条规则 · 引用：'
        f'{e(", ".join(citations) or "—")}</p>',
        unsafe_allow_html=True,
    )


def render_ads(ads: dict[str, Any]) -> None:
    last = ads.get("last_30d") or {}
    prev = ads.get("previous_30d") or {}
    target = float(ads.get("target_acos") or 0)
    backtest = ads.get("backtest") or {}

    diagnosis = str(ads.get("diagnosis") or "")
    if diagnosis == FALLBACK_DIAGNOSIS:
        diagnosis = "规则诊断：高 ACOS 关键词在消耗预算，但没有带来相应销售。"
    st.markdown(f'<div class="lead">{e(diagnosis or "暂无广告诊断。")}</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-title">30 天表现</div>', unsafe_allow_html=True)
    perf_rows = [
        {
            "metric": "花费",
            "last": fmt_money(last.get("spend")),
            "prev": fmt_money(prev.get("spend")),
            "delta": fmt_signed_pct(ads.get("spend_delta")),
        },
        {
            "metric": "销售额",
            "last": fmt_money(last.get("sales")),
            "prev": fmt_money(prev.get("sales")),
            "delta": fmt_signed_pct(ads.get("sales_delta")),
        },
        {
            "metric": "ACOS",
            "last": fmt_pct(last.get("acos")),
            "prev": fmt_pct(prev.get("acos")),
            "delta": fmt_signed_pp(last.get("acos"), prev.get("acos")),
        },
        {
            "metric": "点击",
            "last": fmt_num(last.get("clicks")),
            "prev": fmt_num(prev.get("clicks")),
            "delta": "",
        },
        {
            "metric": "曝光",
            "last": fmt_num(last.get("impressions")),
            "prev": fmt_num(prev.get("impressions")),
            "delta": "",
        },
        {
            "metric": "订单",
            "last": fmt_num(last.get("orders")),
            "prev": fmt_num(prev.get("orders")),
            "delta": "",
        },
        {
            "metric": "CTR",
            "last": fmt_pct(last.get("ctr"), 2),
            "prev": fmt_pct(prev.get("ctr"), 2),
            "delta": "",
        },
        {
            "metric": "CVR",
            "last": fmt_pct(last.get("cvr")),
            "prev": fmt_pct(prev.get("cvr")),
            "delta": "",
        },
    ]
    render_table(
        perf_rows,
        [
            ("metric", "指标", ""),
            ("last", "最近 30 天", "num"),
            ("prev", "前 30 天", "num"),
            ("delta", "变化", "num"),
        ],
        table_class="wide-first",
    )

    st.markdown('<div class="section-title">异常</div>', unsafe_allow_html=True)
    anomalies = []
    for item in ads.get("anomalies") or []:
        kind = str(item.get("type") or "")
        if kind == "high_acos":
            detail = f"ACOS {fmt_pct(last.get('acos'))} 高于目标 {fmt_pct(target)}。"
        elif kind == "wasted_spend":
            detail = (
                f"花费 {fmt_signed_pct(ads.get('spend_delta'))}，"
                f"销售额 {fmt_signed_pct(ads.get('sales_delta'))}。"
            )
        elif kind == "low_ctr":
            detail = f"点击率 {fmt_pct(last.get('ctr'), 2)} 低于 0.35% 演示基准。"
        elif kind == "low_cvr":
            detail = f"转化率 {fmt_pct(last.get('cvr'))} 低于 6% 演示基准。"
        else:
            detail = zh_anomaly(kind, severity, item.get("detail"))
        severity = str(item.get("severity") or "")
        dot = "block" if severity == "high" else "warn" if severity == "medium" else "info"
        anomalies.append(
            {
                "type": ANOMALY_LABELS.get(kind, kind),
                "severity": (
                    f'<span class="severity"><span class="dot {dot}"></span>'
                    f'{e(SEVERITY_LABELS.get(severity, severity))}</span>'
                ),
                "detail": detail,
            }
        )
    if anomalies:
        rows = "".join(
            f"<tr><td>{e(item['type'])}</td><td>{item['severity']}</td>"
            f"<td>{e(item['detail'])}</td></tr>"
            for item in anomalies
        )
        st.markdown(
            '<div class="table-wrap"><table><thead><tr><th>类型</th><th>级别</th>'
            f"<th>说明</th></tr></thead><tbody>{rows}</tbody></table></div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown('<div class="empty-row">没有发现异常</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-title">出价建议</div>', unsafe_allow_html=True)
    rec_rows = []
    for rec in ads.get("recommendations") or []:
        action = str(rec.get("action") or "")
        if action == "decrease_bid":
            reason = f"ACOS {fmt_pct(rec.get('current_acos'))} 高于目标 {fmt_pct(target)}，建议降价。"
        elif action == "increase_bid":
            reason = f"ACOS {fmt_pct(rec.get('current_acos'))} 低于目标 {fmt_pct(target)}，有放量空间。"
        else:
            reason = "调整出价以接近目标 ACOS。"
        rec_rows.append(
            {
                "keyword": rec.get("keyword") or "—",
                "action": action_label(action),
                "current": fmt_money(rec.get("current_bid")),
                "proposed": fmt_money(rec.get("proposed_bid")),
                "reason": reason,
            }
        )
    render_table(
        rec_rows,
        [
            ("keyword", "关键词", ""),
            ("action", "动作", ""),
            ("current", "当前出价", "num"),
            ("proposed", "建议出价", "num"),
            ("reason", "理由", ""),
        ],
        "暂无出价建议",
    )

    st.markdown('<div class="section-title">30 天回测</div>', unsafe_allow_html=True)
    baseline_acos = float((backtest.get("baseline") or {}).get("acos") or 0)
    projected_acos = float((backtest.get("projected") or {}).get("acos") or 0)
    max_acos = max(baseline_acos, projected_acos, 0.0001)
    delta_spend = (backtest.get("delta") or {}).get("spend")
    st.markdown(
        f"""
        <div class="compare-card">
          <div class="compare-head"><span>ACOS 对比</span><span>30 天回测</span></div>
          <div class="compare-row">
            <span>当前出价</span>
            <div class="compare-track"><span style="width:{baseline_acos / max_acos * 100:.1f}%"></span></div>
            <span class="num">{e(fmt_pct(baseline_acos))}</span>
          </div>
          <div class="compare-row accent">
            <span>建议出价</span>
            <div class="compare-track"><span style="width:{projected_acos / max_acos * 100:.1f}%"></span></div>
            <span class="num">{e(fmt_pct(projected_acos))}</span>
          </div>
          <div class="compare-foot">预计花费变化 <strong>{e(fmt_signed_money(delta_spend))}</strong></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="muted rationale">假设：点击量随出价按 0.6 弹性变化，CPC 按 0.5 变化；CVR 与客单价保持不变。</p>',
        unsafe_allow_html=True,
    )
    with st.expander("回测明细"):
        st.json(backtest)


def render_audit(state: dict[str, Any], snapshot: dict[str, Any]) -> None:
    logs = state.get("execution_log") or []
    proposals = state.get("proposals") or []

    st.markdown('<div class="section-title">执行记录</div>', unsafe_allow_html=True)
    if logs:
        rows = [
            {
                "ts": fmt_ts(item.get("ts")),
                "action": action_label(item.get("action")),
                "keyword": item.get("keyword") or "—",
                "current": fmt_money(item.get("current_bid")),
                "proposed": fmt_money(item.get("proposed_bid")),
                "status": EXEC_STATUS_LABELS.get(str(item.get("status")), item.get("status")),
            }
            for item in logs
        ]
        render_table(
            rows,
            [
                ("ts", "时间", "mono"),
                ("action", "动作", ""),
                ("keyword", "关键词", ""),
                ("current", "当前出价", "num"),
                ("proposed", "建议出价", "num"),
                ("status", "状态", ""),
            ],
        )
    elif snapshot.get("status") == "awaiting_approval":
        st.markdown(
            '<div class="empty-row">执行器正在闸门后等待审批。批准后会生成 dry-run 审计记录。</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown('<div class="empty-row">没有执行记录。</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-title">出价提案</div>', unsafe_allow_html=True)
    proposal_rows = []
    for item in proposals:
        current = float(item.get("current_bid") or 0)
        proposed = float(item.get("proposed_bid") or 0)
        reason = "降低出价以压 ACOS。" if proposed < current else "提高出价以争取曝光。"
        proposal_rows.append(
            {
                "keyword": item.get("keyword") or "—",
                "action": action_label(item.get("action")),
                "current": fmt_money(current),
                "proposed": fmt_money(proposed),
                "reason": reason,
            }
        )
    render_table(
        proposal_rows,
        [
            ("keyword", "关键词", ""),
            ("action", "动作", ""),
            ("current", "当前出价", "num"),
            ("proposed", "建议出价", "num"),
            ("reason", "理由", ""),
        ],
        "暂无出价提案",
    )
    st.markdown(
        '<p class="muted rationale">批准 → 5 条 dry-run；拒绝 → 1 条跳过；重复批准幂等。</p>',
        unsafe_allow_html=True,
    )


def render_metrics(metrics: dict[str, Any]) -> None:
    node_times = metrics.get("node_times") or {}
    items = [
        {"node": node, "value": float(value)}
        for node, value in node_times.items()
    ]
    items.sort(key=lambda item: -item["value"])
    st.markdown('<div class="section-title">节点耗时</div>', unsafe_allow_html=True)
    render_bars(
        items,
        label_fn=lambda item: NODE_LABELS.get(str(item["node"]), str(item["node"])),
        value_fn=lambda item: float(item["value"]),
        fmt_fn=lambda value: f"{value:.2f}s",
        accent_index=0,
    )

    wall = metrics.get("wall_clock_sec")
    wait = metrics.get("approval_wait_sec")
    pipeline = metrics.get("pipeline_sec")
    st.markdown(
        f"""
        <div class="mini-band">
          <div class="stat"><div class="stat-label">墙钟耗时</div>
            <div class="stat-value">{e(fmt_num(wall)) if wall is not None else "—"}s</div>
            <div class="stat-note">含审批等待</div></div>
          <div class="stat"><div class="stat-label">审批等待</div>
            <div class="stat-value">{e(fmt_num(wait)) if wait is not None else "—"}s</div>
            <div class="stat-note">闸门打开的时间</div></div>
          <div class="stat"><div class="stat-label">流水线</div>
            <div class="stat-value">{e(fmt_num(pipeline)) if pipeline is not None else "—"}s</div>
            <div class="stat-note">节点合计</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("本次运行指标"):
        st.json(metrics)
    try:
        aggregate = get("/metrics")
    except Exception as exc:
        st.caption(f"无法读取聚合指标：{exc}")
    else:
        with st.expander("聚合指标"):
            st.json(aggregate)
    with st.expander("5 分钟演示脚本"):
        st.markdown(
            """
            1. 选择 `SKU-003`（低评分、高 ACOS）。
            2. 运行流水线，打开「洞察」：痛点是真实评论引用。
            3. 打开「Listing」：新草稿引用了历史高转化 Listing。
            4. 打开「合规」：当前 Listing 有问题，新草稿通过。
            5. 打开「广告」：ACOS 偏高、花费上涨，查看出价建议与回测。
            6. 在侧栏批准：执行器写入 dry-run 审计。
            7. 打开「指标」：节点耗时、调用成本、合规结果。
            """
        )


def main() -> None:
    st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)

    snapshot = st.session_state.get("snapshot")
    metrics = (snapshot or {}).get("metrics") or {}
    last_error = st.session_state.get("last_error")

    render_sidebar(snapshot, metrics)
    render_header()

    if last_error:
        render_error_card("操作失败", str(last_error))

    if not snapshot:
        render_empty_state()
        return

    state = snapshot.get("state") or {}
    insights = state.get("insights") or {}
    listing = state.get("draft_listing") or {}
    compliance = state.get("compliance_report") or {}
    ads = state.get("ads_report") or {}

    render_status_band(snapshot, metrics, state)

    tabs = st.tabs(["洞察", "Listing", "合规", "广告", "审计", "指标"])
    with tabs[0]:
        render_insight(insights)
    with tabs[1]:
        render_listing(state, listing)
    with tabs[2]:
        render_compliance(compliance)
    with tabs[3]:
        render_ads(ads)
    with tabs[4]:
        render_audit(state, snapshot)
    with tabs[5]:
        render_metrics(metrics)


if __name__ == "__main__":
    main()
