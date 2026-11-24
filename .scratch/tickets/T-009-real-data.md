# [T-009] 真实公开数据替换合成种子

- **Status**: Done
- **Depends On**: T-008
- **对应 SPEC**: `SPEC.md` 的演示边界（2026-11-24 用户批准的例外）
- **预估轮数**: 3
- **预估 diff 行数**: < 700

## 要解决的问题

用户要求「真实数据更有说服力」。公开渠道拿不到卖家的广告、库存、成本数据，但可以拿到真实的 Amazon 公开商品与评论数据。当前 `data/seed/**` 全部是合成数据，与真实 LLM 不匹配。

## 范围

- 做：新增 `data/fetch_real_seed.py`，从 Amazon Reviews 2023（All Beauty）拉取并校验固定快照，生成 5 个真实 SKU、250 条真实评论、20 条真实历史 Listing；品牌匿名化；广告/库存/成本/关键词量保持模拟并在 `PROVENANCE.md` 标注；更新 golden、UI 文案、README、SPEC、ADR、AGENTS、verify。
- 不做：接 SP-API / Ads API；抓取 Amazon 页面；使用带版权风险的图片；把真实品牌与负面评论绑定展示；改 `executor` dry-run 边界。

## Stop conditions

- 需要读取或打印 `.env` / key
- 数据源需要登录或付费
- 需要新增依赖
- 同一处改 3 次不过

## 验收标准

- [x] AC-1：`data/fetch_real_seed.py` 下载固定 URL，校验 sha256；缓存失败会拒绝生成；缓存目录被 gitignore。
- [x] AC-2：生成 5 个真实商品（标题/五点/描述/价格/评分/评论数/真实评论），品牌替换为 Brand A–E；评论不含 user_id、图片、helpful_vote。
- [x] AC-3：20 条历史 Listing 为真实公开商品；广告、库存、成本、关键词量、转化率为模拟，并在 `data/seed/PROVENANCE.md` 逐项列明。
- [x] AC-4：`current_listing` 保留真实原文（含违规宣称），草稿基线移除违规宣称；合规扫描能命中真实 warn/block。
- [x] AC-5：`evals/golden.jsonl` 按真实商品重写；无 LLM 时 `10/10 passed`（`llm_calls=0`）。
- [x] AC-6：`scripts.smoke_test` 合规通过、5 条 dry-run；`UI_VERIFY_OK`（local + cloud 入口）；`compileall` 退出 0。
- [x] AC-7：README / AGENTS / SPEC / ADR / `docs/verify.md` 不再声称全部为合成数据；写明数据来源、许可、匿名化与模拟边界。
- [x] AC-8：仓库不含 `.env`、key、token；`data/cache/` 与报告未跟踪。

## 完成记录

- 完成时间：2026-11-24。
- 种子重建（缓存命中，固定快照 + sha256）：
  ```
  cache hit meta_All_Beauty.jsonl sha256=1cfbdf6d2ccf…
  cache hit reviews_All_Beauty.jsonl sha256=36ca7c48440a…
  Wrote real-data seed to ...\data\seed
    SKUs: 5 / reviews: 250 / historical listings: 20 / ads daily rows: 450
  ```
- `LLM_ENABLED=false EMBEDDING_ENABLED=false` fallback eval：`10/10 passed (100.0%); llm_calls=0, tokens=0, cost=$0.000000`。
- 真实 LLM（Agnes AI，`--require-llm --max-cost-usd 0.50`）：`9/10 passed (90.0%)`，`llm_calls=30`、`tokens.total=63173`、`cost=$0.004921`、`duration_sec=528.99`；`G-003` 失败为 `missing: nail art drill`。未为过测修改 golden 或 prompt。
- smoke：`errors=[]`、`compliance.passed=true`、`score=100`、`draft_issues=0`、`current_issues=2`、`fixed_count=2`、`execution_actions=5`、`metrics.llm_calls=0`。
- `LOCAL_BACKEND_OK skus=5 awaiting_approval=ok approve=5_dry_run audit=6`。
- `UI_VERIFY_OK tabs=6 awaiting_approval=ok approve=5_dry_run reject=1_skip errors=0`（`app/streamlit_app.py` 与 `app/streamlit_cloud.py` 两个入口各一次）。
- `compileall -q agent api app core rag evals scripts data` 退出 0。
- 边缘情况：SKU-003 当前 Listing 命中的两条真实 warn 是 description `Guarantee` 与 bullet `medical grade`；`Made in USA` 已保留在 current bullets，但现有规则 `made\s+in\s+the?\s*usa` 不会匹配该写法，因此未计入 `current_issues`。规则文件属手写配置，本 Ticket 未改 `data/seed/**`。
- 提交：`acd1806`。
