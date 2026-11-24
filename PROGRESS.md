# 进度看板

> 规则：Pending ≤ 15；一个 Ticket 一个提交；做完立刻更新。
> Last updated: 2026-11-24 (Streamlit Cloud 已上线)
> Mode: implement

## 冷启动摘要（新会话先读这里）
- 项目：Amazon 卖家多智能体运营副驾驶演示（LangGraph + RAG + FastAPI + Streamlit）
- 当前状态：可跑；无 LLM key / 显式关闭 LLM 时走规则兜底；已用 Agnes AI 完成真实 LLM 回归（当前重跑 10/10）；Streamlit Cloud 单进程入口已上线（免费公开，无需外部 API）
- 启动：`.\run.ps1`（API :8000 + UI :8501）；在线 Demo <https://amz-ops-agent-g9pckbqru2xenyystgiaas.streamlit.app/>（入口 `app/streamlit_cloud.py`，local 模式）
- 上次验证：显式关闭 LLM 时 `-m evals.run_eval` → 10/10（`llm_calls=0`）；`-m scripts.verify_local_backend` → `LOCAL_BACKEND_OK`；`API_BASE_URL=local -m scripts.verify_ui` → `UI_VERIFY_OK`；`-m scripts.smoke_test` → 5 条 dry-run（2026-11-24）
- 最近决策：真实 LLM 使用 Agnes AI OpenAI 兼容端点 + 成本封顶 + 429 退避（`T-005`）；中文 UI + 纸白/墨色/黄铜改版（`SPEC-004`）；HITL checkpoint 用官方 `SqliteSaver`（`ADR-002`）；演示边界见 `ADR-001`；免费部署走 Streamlit Community Cloud（`T-007`）
- 下一步：T-007 已上线并回填 URL；可选：独立裁判复判 T-007、绑定更短的应用 URL、在 App settings 固定 Python 3.11
- 未决问题：Render 免费服务创建仍要求绑卡；Hugging Face 免费账号只能建 Static Space，Docker/Gradio 需 PRO；Zeabur 公告 2026/12/31 停止运营

## 当前迭代
T-007 已完成：Streamlit Community Cloud 单进程入口、本地后端、在线部署与 URL 回填全部完成。

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
| T-005 | 真实 LLM 回归收尾（Agnes AI） | `0a6a598` | 真实 `--require-llm` 10/10；`verify_llm_eval` / fallback 10/10 / smoke / UI 全通过；独立裁判复判全 AC 达成 |
| T-006 | Render + GitHub Actions 部署配置 | `f88ac44` | YAML/端口/健康检查/密钥扫描通过；Actions 缺失 hooks 时 warning 跳过；独立裁判 AC-1..AC-8 全达成；Render 实际创建仍要求绑卡 |
| T-007 | Streamlit Community Cloud 免费部署 | `f5fd95f` | 本地 `LOCAL_BACKEND_OK` / `UI_VERIFY_OK` / eval 10/10；线上 <https://amz-ops-agent-g9pckbqru2xenyystgiaas.streamlit.app/> 浏览器 E2E：审批 → 5 条 dry-run、模型调用 0 |

## 阻塞 / 待决策
| 问题 | 需要谁决定 | 影响范围 |
|---|---|---|
| 配置真实 LLM key 以完成 T-003 的 AC-2/3/4/8 | 已完成（Agnes AI，本地 `.env`） | 真实回归证据 / 费用 |
| checkpoint 库是否需要保留期 / GC | 用户 | 磁盘增长 / 演示数据 |
| 是否需要多 worker（改用 Postgres checkpoint） | 用户 | 部署形态 |

## 交接
- 上次停在哪：T-007 已上线（`f5fd95f`），公网地址已回填 README / 部署文档 / Ticket；本地与线上验证均通过。
- 下一步：可选独立裁判复判 T-007；可选把应用 URL 改短、在 App settings 固定 Python 3.11。
- 不要重复的尝试 / 已否决的方案：不接真实 SP-API / Ads API；不绕过审批；不把 demo 包装成生产系统；不自写 checkpoint saver；不为通过测试放宽 golden 判定；不在 Render / Hugging Face 上继续尝试需要绑卡或付费的方案。
