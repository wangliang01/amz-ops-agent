# 进度看板

> 规则：Pending ≤ 15；一个 Ticket 一个提交；做完立刻更新。
> Last updated: 2026-11-24 (real LLM verified with Agnes AI)
> Mode: implement

## 冷启动摘要（新会话先读这里）
- 项目：Amazon 卖家多智能体运营副驾驶演示（LangGraph + RAG + FastAPI + Streamlit）
- 当前状态：可跑；无 LLM key / 显式关闭 LLM 时走规则兜底；已用 Agnes AI 完成真实 LLM 回归（当前重跑 10/10）
- 启动：`.\run.ps1`（API :8000 + UI :8501）
- 上次验证：显式关闭 LLM 时 `-m evals.run_eval` → 10/10（`llm_calls=0`）；显式 `--require-llm` 真实回归 → 10/10（`llm_calls=30`）；`-m scripts.verify_llm_eval` → `LLM_EVAL_VERIFY_OK`；`-m scripts.smoke_test` → 5 条 dry-run；`scripts/verify_hitl_restart.py` → `HITL_RESTART_OK`；`-m scripts.verify_ui` → `UI_VERIFY_OK`（2026-11-24）
- 最近决策：真实 LLM 使用 Agnes AI OpenAI 兼容端点 + 成本封顶 + 429 退避（`T-005`）；中文 UI + 纸白/墨色/黄铜改版（`SPEC-004`）；HITL checkpoint 用官方 `SqliteSaver`（`ADR-002`）；演示边界见 `ADR-001`
- 下一步：T-005 独立裁判与提交；checkpoint GC 待决策
- 未决问题：`.env` 是否长期保留 Agnes AI 配置（未提交，避免接触密钥）；Agnes 免费 key 的 RPM 限制需要更高配额时可升级 Token Plan；带 key 时默认 eval 会真实调用 LLM，兜底回归须显式 `LLM_ENABLED=false`

## 当前迭代
T-005 真实 LLM 回归已完成（Agnes AI），复判全部 AC 达成；本轮记录提交。

## 进行中
| ID | 任务 | 开始时间 |
|---|---|---|
| - | 无 | - |

## 待办（按依赖排序）
| ID | 任务 | 依赖 | 预估轮数 |
|---|---|---|---|
| - | 无 | - | - |

## 已完成
| ID | 任务 | 提交 | 验证证据 |
|---|---|---|---|
| T-000 | SPEC / AGENTS / 验证说明 / 重定向 / git 初始化 | `b693674` | AC-1..AC-7（见 `SPEC.md`） |
| T-001 | 替换 Streamlit `use_container_width` | `6c3900e` | 8501 返回 200；6 tabs；5 条 dry-run；API 不可达兜底；裁判 4/4 达成 |
| T-002 | HITL 待审批状态跨 API 重启持久化 | `0417240` | 重启后 awaiting_approval / approve / reject / 幂等；eval 10/10；裁判 8/8 达成 |
| T-003 | 真实 LLM 回归入口 / 成本闸门 / 报告 | `517ad68` | `verify_llm_eval` 全 PASS；fallback eval 10/10；无 key 退出 2；AC-2/3/4/8 待 key |
| T-004 | UI 中文改版（unslop） | `dc8ea44` | AppTest / eval / smoke / 四视口 / 对比度 / 键盘均通过；独立裁判 AC-1..AC-7 全 PASS |
| T-005 | 真实 LLM 回归收尾（Agnes AI） | 待回填 | 真实 `--require-llm` 10/10；`verify_llm_eval` / fallback 10/10 / smoke / UI 全通过；独立裁判复判全 AC 达成 |

## 阻塞 / 待决策
| 问题 | 需要谁决定 | 影响范围 |
|---|---|---|
| 配置真实 LLM key 以完成 T-003 的 AC-2/3/4/8 | 已完成（Agnes AI，本地 `.env`） | 真实回归证据 / 费用 |
| checkpoint 库是否需要保留期 / GC | 用户 | 磁盘增长 / 演示数据 |
| 是否需要多 worker（改用 Postgres checkpoint） | 用户 | 部署形态 |

## 交接
- 上次停在哪：T-005 真实 LLM 回归已用 Agnes AI 完成；待独立裁判与提交。
- 下一步：裁判 T-005 后提交；checkpoint GC / 多 worker 属后续部署决策。
- 不要重复的尝试 / 已否决的方案：不接真实 SP-API / Ads API；不绕过审批；不把 demo 包装成生产系统；不自写 checkpoint saver；不为通过测试放宽 golden 判定。
