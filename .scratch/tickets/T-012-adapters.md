# [T-012] SP-API / Ads API adapter 接口 + mock

- **Status**: Done
- **Depends On**: T-011
- **对应 SPEC**: 用户 2026-11-24 批准的 JD 补强顺序（真实数据 → P0 运营广度 → 美工 AIGC → SP-API/Ads adapter）
- **预估轮数**: 2
- **预估 diff 行数**: < 600

## 要解决的问题

节点直接依赖 `SeedStore`，卖家和面试官看不到「哪些调用会替换成真实 SP-API / Ads API」。需要把目录、库存、Listing 与广告数据收进只读 adapter 接口，默认 mock 复用现有种子；未来接真实 API 时只换 adapter，不改节点与 UI。仍不接真实店铺、不增加写接口。

## 范围

- 做：
  - `integrations/`：`SPAPIAdapter` / `AdsAPIAdapter` Protocol；`MockSPAPIAdapter` / `MockAdsAPIAdapter` 从种子读数据；`Adapters` 装配与注册表；`ADAPTER_MODE=mock`。
  - `Services` 增加 `adapters`；Supervisor 的 SKU 读取、Ads 节点的日报/关键词、Ops 的库存/预算改走 adapter。
  - `health` 返回 `adapters` 能力摘要；UI 侧栏显示当前 adapter 模式（只读）。
  - `scripts/verify_adapters.py`：mock 形状、只读、确定性、未知 SKU、可替换 fake adapter 后 Ops 使用新数据、`full_chain` 闸门与 5 条 dry-run。
  - README / `docs/verify.md` / `.env.example` / PROGRESS 同步；明确真实 API 未接入。
- 不做：真实 SP-API / Ads API 调用；OAuth/凭据；真实写接口；新增依赖；把 mock 描述成生产接入。

## Stop conditions

- 需要读取或打印 `.env` / key
- 需要新增依赖或真实 API 凭据
- 需要移除 `interrupt_before` 或增加真实写接口
- 同一处改 3 次不过

## 验收标准

- [x] AC-1：`SPAPIAdapter` / `AdsAPIAdapter` Protocol 与 `Adapters` 装配存在；默认 `ADAPTER_MODE=mock`，`describe()` 返回 `read_only=true`、provider 名与能力列表。
- [x] AC-2：Mock adapter 从现有种子返回 catalog item、inventory、current listing、90 天广告日报与关键词；不修改种子；未知 SKU 抛出 `KeyError`。
- [x] AC-3：Supervisor / Ads / Ops 不再直接为这些数据调用 `store`；注入 fake adapter 后 Ops 的库存与预算使用 fake 数据，证明可替换。
- [x] AC-4：`full_chain` 运行后 `ops_plan.adapter_mode=mock`，仍停在 executor 闸门，批准后 5 条 dry-run；`health` 返回 adapter 摘要。
- [x] AC-5：UI 侧栏显示 adapter 模式；`scripts.verify_ui` 通过（tabs=8）。
- [x] AC-6：`scripts.verify_adapters` 通过；fallback eval 10/10；smoke / local backend / verify_ops / verify_creative / compileall 通过；未新增依赖。
- [x] AC-7：README / `docs/verify.md` 明确「adapter 为只读 mock、真实 SP-API/Ads API 未接入、executor 仍 dry-run」。

## 完成记录

- 完成时间：2026-11-24
- 改动：
  - 新增 `integrations/`：`SPAPIAdapter` / `AdsAPIAdapter` Protocol，`MockSPAPIAdapter` / `MockAdsAPIAdapter`，`Adapters` 装配与 `build_adapters`（仅注册 `mock`）。
  - `Services.adapters`；Supervisor 的 catalog、Ads 的日报/关键词、Ops 的库存/预算全部改走 adapter；`ops_plan` 增加 `adapter_mode` / `adapter_sources`。
  - `/health` 与本地后端 `health()` 返回 adapter 摘要；UI 侧栏显示「数据适配器：SP-API mock · Ads API mock（只读）」。
  - 新增 `scripts/verify_adapters.py`；`verify_ui` 增加侧栏 adapter 断言；README / `docs/verify.md` / `AGENTS.md` / `.env.example` 同步。
- 验证输出（2026-11-24）：
  - `ADAPTERS_VERIFY_OK sp=mock_sp_api ads=mock_ads_api read_only=yes inventory=95 daily_rows=90 fake_swap=ok execution=5_dry_run`
  - `CREATIVE_VERIFY_OK slots=5 score=100.0 provider=mock negative_control=blocked execution=5_dry_run`
  - `OPS_VERIFY_OK skus=5 top=SKU-001:67.5 drivers=5 evidence=2 execution=5_dry_run`
  - `LOCAL_BACKEND_OK skus=5 awaiting_approval=ok creative=5_mock adapters=mock approve=5_dry_run audit=6`
  - `UI_VERIFY_OK tabs=8 awaiting_approval=ok approve=5_dry_run reject=1_skip errors=0`
  - eval：`10/10 passed (100.0%); llm_calls=0, tokens=0, cost=$0.000000`
  - smoke：`adapters {mode: mock, sp_api: mock_sp_api, ads_api: mock_ads_api}`、creative 5 素材、`execution_actions=5`
  - `compileall` 退出 0；`git diff --check` 通过；未新增依赖
  - `/health`（TestClient + lifespan）：`{"ok":true,"llm_enabled":false,"vector_index":false,"adapters":{"mode":"mock","read_only":true,"sp_api":{"provider":"mock_sp_api","capabilities":["get_catalog_item","get_inventory","get_listing"]},"ads_api":{"provider":"mock_ads_api","capabilities":["get_daily_metrics","get_keyword_performance"]}}}`
- 本地浏览器 E2E（`:8503`，`API_BASE_URL=local`）：侧栏显示 adapter 只读 caption；`full_chain` 停在审批，8 个 tab；选品页显示库存 95 / 补货点 58 / 预算 $48.7→$34.1；批准后审计 5 条 `dry-run 成功`。截图：`.scratch/ui/T-012/empty-local-1440.png`、`awaiting-local-1440.png`、`ops-local-1440.png`、`completed-local-1440.png`、`audit-local-1440.png`。
- 线上 E2E（2026-11-24，Streamlit Cloud，首次加载发现侧栏缺 adapter caption＝模块缓存旧版，按 `docs/deploy-streamlit-cloud.md` Reboot 后通过）：侧栏显示「数据适配器：SP-API mock · Ads API mock（只读）」；运行 `full_chain` → 等待审批（8 tabs）→ 批准 → 已完成，审计 5 条 `dry-run 成功`，模型调用 0。截图：`.scratch/ui/T-012/live-awaiting-1440.png`、`live-audit-1440.png`。
- 提交：`b5753cd`（实现 + 文档 + 验证脚本）。
- 未做：真实 SP-API / Ads API 调用、OAuth/凭据、真实店铺写接口。
