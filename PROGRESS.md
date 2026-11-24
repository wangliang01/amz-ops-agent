# 进度看板

> 规则：Pending ≤ 15；一个 Ticket 一个提交；做完立刻更新。
> Last updated: 2026-11-24 (运营广度 P0 完成)
> Mode: implement

## 冷启动摘要（新会话先读这里）
- 项目：Amazon 卖家多智能体运营副驾驶演示（LangGraph + RAG + FastAPI + Streamlit）
- 当前状态：可跑；种子为真实公开评论/商品（品牌匿名）+ 模拟广告；链路已扩展到选品机会、补货、预算/定价与 ROI；无 LLM key / 显式关闭 LLM 时走规则兜底；Agnes AI 真实 LLM 回归 9/10（`G-003` 未命中 `nail art drill`，未放宽 golden）；Streamlit Cloud 单进程入口已上线
- 启动：`.\run.ps1`（API :8000 + UI :8501）；在线 Demo <https://amz-ops-agent-g9pckbqru2xenyystgiaas.streamlit.app/>（入口 `app/streamlit_cloud.py`，local 模式）
- 上次验证（2026-11-24）：显式关闭 LLM 时 `-m evals.run_eval` → 10/10（`llm_calls=0`）；真实 LLM `--require-llm` → 9/10（`llm_calls=30`、`cost=$0.004921`）；`OPS_VERIFY_OK`；`LOCAL_BACKEND_OK`；两入口 `UI_VERIFY_OK`（tabs=7）；`smoke_test` → `current_issues=2`、5 条 dry-run；`compileall` 退出 0
- 最近决策：真实 LLM 使用 Agnes AI OpenAI 兼容端点 + 成本封顶 + 429 退避（`T-005`）；中文 UI + 纸白/墨色/黄铜改版（`SPEC-004`）；HITL checkpoint 用官方 `SqliteSaver`（`ADR-002`）；种子改真实公开数据（`ADR-003`，`T-009`）；免费部署走 Streamlit Community Cloud（`T-007`）
- 下一步：T-011 美工 AIGC brief + 审核 rubric + 可插拔接口；之后 T-012 SP-API/Ads adapter mock
- 未决问题：Render 免费服务创建仍要求绑卡；Hugging Face 免费账号只能建 Static Space，Docker/Gradio 需 PRO；Zeabur 公告 2026/12/31 停止运营

## 当前迭代
T-010 已完成：选品机会排名、补货/预算/定价计划、ROI 面板；审批闸门与 5 条 dry-run 保持不变。

## 进行中
| ID | 任务 | 开始时间 |
|---|---|---|
| - | 无 | - |

## 待办（按依赖排序）
| ID | 任务 | 依赖 | 预估轮数 |
|---|---|---|---|
| T-011 | 美工 AIGC：brief + 审核 rubric + 可插拔接口 | T-010 | 2 |
| T-012 | SP-API / Ads API adapter 接口 + mock | T-010 | 2 |

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
| T-008 | 品牌 mark 改为审批闸门 glyph | `98fb544` | 页头 20px / 侧栏 18px；1440/390 无横向滚动；两入口 `UI_VERIFY_OK`；`compileall` 通过 |
| T-009 | 真实公开数据替换合成种子 | `acd1806` | 5 SKU / 250 条真实评论 / 20 条真实历史 Listing；fallback eval 10/10；真实 LLM 9/10；smoke / local backend / UI / compileall 通过 |
| T-010 | 运营广度 P0：选品 / 补货 / 预算定价 / ROI | `a4f26b2` | `OPS_VERIFY_OK`；API `/opportunities` + `state.ops_plan`；UI tabs=7 与 ROI 浏览器实测；5 条 dry-run 不变 |

## 阻塞 / 待决策
| 问题 | 需要谁决定 | 影响范围 |
|---|---|---|
| 配置真实 LLM key 以完成 T-003 的 AC-2/3/4/8 | 已完成（Agnes AI，本地 `.env`） | 真实回归证据 / 费用 |
| checkpoint 库是否需要保留期 / GC | 用户 | 磁盘增长 / 演示数据 |
| 是否需要多 worker（改用 Postgres checkpoint） | 用户 | 部署形态 |

## 交接
- 上次停在哪：T-010（`a4f26b2`）已完成；链路增加选品机会、补货/预算/定价与 ROI，审批闸门与 5 条 dry-run 未变；真实 LLM 回归仍为 9/10（`G-003` 原样记录）。
- 下一步：T-011 美工 AIGC brief + 审核 rubric + 可插拔接口；再做 T-012 adapter mock。
- 不要重复的尝试 / 已否决的方案：不接真实 SP-API / Ads API；不绕过审批；不把 demo 包装成生产系统；不自写 checkpoint saver；不为通过测试放宽 golden 判定；不在 Render / Hugging Face 上继续尝试需要绑卡或付费的方案。
