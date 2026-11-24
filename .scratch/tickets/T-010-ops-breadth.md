# [T-010] 运营广度 P0：选品机会 / 库存补货 / 预算与定价 / ROI 面板

- **Status**: Done
- **Depends On**: T-009
- **对应 SPEC**: `SPEC.md` 的「运营广度 P0」（2026-11-24 用户批准）
- **预估轮数**: 3
- **预估 diff 行数**: < 700

## 要解决的问题

对照岗位职责，当前链路只覆盖「评论洞察 → Listing → 合规 → 广告」，缺选品机会、库存补货、预算/定价与 ROI 量化。面试官会把这四项当成运营 Agent 的主干。

## 范围

- 做：
  - `agent/opportunity.py`：5 个 SKU 的机会分（需求、痛点密度、评分、价格带、竞争），输出驱动因素 + 证据评论；纯确定性。
  - `agent/ops_plan.py`：可售天数、补货点、补货量、广告预算迁移（ACOS vs 目标）、价格护栏；模拟假设逐项标注。
  - LangGraph 新增 `ops` 节点（`ads` 之后、`executor` 之前），结果写入 `state.ops_plan`；审批闸门与 dry-run 不变。
  - API：`GET /opportunities`、运行详情返回 `ops_plan`。
  - UI：新增「选品」tab（排名 + 驱动 + 证据）；「补货 / 预算」面板；「指标」tab 增加 ROI 卡（节点耗时、成本、人工分钟节省、合规修复数、ACOS/转化预估 + 假设标签）。
  - `scripts/verify_ops.py`：确定性、排序、边界（无评论 / 缺广告）校验。
- 不做：接 SP-API / Ads API 真接口；真实写店铺；新增依赖；把模拟假设包装成真实经营数据。

## Stop conditions

- 需要读取或打印 `.env` / key
- 需要新增依赖
- 需要移除 `interrupt_before` 或增加真实写接口
- 同一处改 3 次不过

## 验收标准

- [x] AC-1：`GET /opportunities` 返回 5 个 SKU，分数 0–100 且排序稳定；每个 SKU 至少 3 条驱动因素、至少 1 条真实评论证据；同输入重复调用结果一致。
- [x] AC-2：`ops_plan` 含 `days_of_cover`、`reorder_point`、`reorder_qty`、`budget`、`price_guardrail`、`assumptions[]`；所有模拟字段在输出中标记 `simulated=true`。
- [x] AC-3：`full_chain` 运行后 `state.ops_plan` 非空；仍为 `interrupt_before=["executor"]`，批准后 `execution_log` 仍为 5 条 dry-run。
- [x] AC-4：UI 出现「选品」tab 与补货/预算面板、ROI 卡；`scripts.verify_ui` 在 remote 与 cloud 入口均通过。
- [x] AC-5：`scripts.verify_ops` 通过；fallback eval `10/10`；`scripts.smoke_test`、`scripts.verify_local_backend`、`compileall` 通过。
- [x] AC-6：README 增加 JD 能力对照；README / SPEC / `docs/verify.md` 明确模拟假设，不新增依赖。

## 完成记录

- 完成时间：2026-11-24。
- `scripts.verify_ops`：`OPS_VERIFY_OK skus=5 top=SKU-001:67.5 drivers=5 evidence=2 execution=5_dry_run`。
- fallback eval：`10/10 passed (100.0%); llm_calls=0, tokens=0, cost=$0.000000`。
- smoke：`errors=[]`、`passed=true`、`score=100`、`current_issues=2`、`execution_actions=5`。
- `LOCAL_BACKEND_OK skus=5 awaiting_approval=ok approve=5_dry_run audit=6`。
- `UI_VERIFY_OK tabs=7 awaiting_approval=ok approve=5_dry_run reject=1_skip errors=0`（`app/streamlit_app.py` 与 `app/streamlit_cloud.py` 两个入口各一次）。
- API 实测（uvicorn :8010）：`GET /opportunities` 返回 5 条，排名 `SKU-001 67.5 / SKU-005 66.8 / SKU-002 64.6 / SKU-003 60.6 / SKU-004 58.5`；`POST /runs` 返回 `awaiting_approval`、`next=["executor"]`，`state.ops_plan` 含 `inventory` / `budget` / `price_guardrail` / `roi` / `assumptions`。
- 浏览器实测（ego-browser）：7 个 tab；机会排名 5 行、权重说明、SKU-001 证据展开；补货画面 `95 件 / 72.6 天 / 补货点 58 / 建议补 50 / 日预算 $48.7→$34.1`；ROI `60 分钟 / $30 / $0 / ACOS -14.3% / 修复 2`；`innerWidth == scrollWidth`（1707/1707），无横向滚动。
- 截图：`.scratch/ui/T-010/opportunity-1440.png`、`ops-band-1440.png`、`roi-1440.png`、`metrics-1440.png`。
- 线上 E2E（2026-11-24，Streamlit Cloud）：push 后首次访问仍命中旧进程的模块缓存（`SeedStore` 缺 `historical_listings`）；在 share.streamlit.io 的 app 菜单执行 **Reboot** 并在确认框再次点 Reboot 后，线上恢复：7 个 tab、选品 5 行、`SKU-001` 与模拟说明、补货/预算 band 全部出现；批准后状态 `已完成`，审计 5 条 `dry-run 成功`。截图 `.scratch/ui/T-010/live-opportunity.png`、`live-completed.png`。
- `compileall -q agent api app core rag evals scripts data` 退出 0；未新增依赖。
- 提交：`a4f26b2`。
