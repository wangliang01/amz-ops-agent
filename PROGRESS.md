# 进度看板

> 规则：Pending ≤ 15；一个 Ticket 一个提交；做完立刻更新。
> Last updated: 2026-11-24
> Mode: implement

## 冷启动摘要（新会话先读这里）
- 项目：Amazon 卖家多智能体运营副驾驶演示（LangGraph + RAG + FastAPI + Streamlit）
- 当前状态：可跑；无 LLM key 时走规则兜底
- 启动：`.\run.ps1`（API :8000 + UI :8501）
- 上次验证：`-m evals.run_eval` → 10/10；`-m scripts.smoke_test` → 5 条 dry-run；API 与 AppTest 全流程通过（2026-11-24）
- 最近决策：合成数据 + dry-run + 人工审批，见 `docs/adr/ADR-001-demo-boundaries.md`
- 下一步：T-001 替换 Streamlit 弃用参数；真实 LLM 路径待验证
- 未决问题：`.env` 是否启用 LLM / embedding（未读取，避免接触密钥）

## 当前迭代
工程契约回填完成；开始小步技术债，不扩功能。

## 进行中
| ID | 任务 | 开始时间 |
|---|---|---|
| - | - | - |

## 待办（按依赖排序）
| ID | 任务 | 依赖 | 预估轮数 |
|---|---|---|---|
| T-001 | 替换 Streamlit `use_container_width` | - | 3 |

## 已完成
| ID | 任务 | 提交 | 验证证据 |
|---|---|---|---|
| T-000 | SPEC / AGENTS / 验证说明 / 重定向 / git 初始化 | bootstrap | AC-1..AC-7（见 `SPEC.md`） |

## 阻塞 / 待决策
| 问题 | 需要谁决定 | 影响范围 |
|---|---|---|
| 是否投入真实 LLM 回归与成本 | 用户 | 评测可信度 / 费用 |
| HITL 状态是否需要跨重启持久化 | 用户 | API 可靠性 |

## 交接
- 上次停在哪：完成文档与工程契约回填，业务代码未改。
- 下一步：领 T-001，先红后绿；或先补真实 LLM 评测。
- 不要重复的尝试 / 已否决的方案：不接真实 SP-API / Ads API；不绕过审批；不把 demo 包装成生产系统。
