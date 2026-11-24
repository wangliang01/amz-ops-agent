# [T-011] 美工 AIGC：brief + 审核 rubric + 可插拔接口

- **Status**: In progress
- **Depends On**: T-010
- **对应 SPEC**: 用户 2026-11-24 批准的 JD 补强顺序（真实数据 → P0 运营广度 → 美工 AIGC → SP-API/Ads adapter）
- **预估轮数**: 2
- **预估 diff 行数**: < 650

## 要解决的问题

岗位职责包含 AIGC 素材生产（主图 / 场景图 / A+），当前链路只覆盖文字 Listing。需要补一个可信的「美工 brief → 生成接口 → 审核 rubric」闭环，同时不接真实图像模型、不新增依赖、不伪造生成图片。

## 范围

- 做：
  - `agent/creative.py`：
    - `build_creative_brief`：由 SKU 属性、真实评论痛点/正向主题、Listing 草稿与 21 条合规规则确定性生成 5 个素材位 brief（主图 / 场景图 / 细节图 / 套装图 / A+ 横幅）。
    - `CreativeProvider` Protocol + `MockCreativeProvider`：默认 mock 只返回素材元数据，不调图像模型；注册表支持替换真实 provider。
    - `review_creative`：确定性 rubric（合规政策、评论证据、产品还原、文案可读、素材覆盖），输出分数、维度分与 findings；mock 未渲染像素级内容时明确标注「无法验证」。
  - LangGraph 新增 `creative` 节点（`compliance` 之后、`ads` 之前，仅 `full_chain`），结果写入 `state.creative_brief` / `creative_assets` / `creative_review`；审批闸门与 dry-run 不变。
  - UI 新增「美工」tab（brief、素材元数据、rubric、证据展开）；空状态与演示脚本同步。
  - `scripts/verify_creative.py`：brief 确定性、5 个素材位、主图无文字、rubric 基线、负向对照（注入 `Best Seller` 必须被 block）、`full_chain` 闸门与 5 条 dry-run。
  - README / `docs/verify.md` / `AGENTS.md` / `PROGRESS.md` 同步；`.env.example` 增加 `CREATIVE_PROVIDER=mock`。
- 不做：调用真实图像/视频模型；新增依赖；把 mock 元数据包装成已生成图片；接真实店铺写接口。

## Stop conditions

- 需要读取或打印 `.env` / key
- 需要新增依赖或真实图像 API
- 需要移除 `interrupt_before` 或增加真实写接口
- 同一处改 3 次不过

## 验收标准

- [x] AC-1：`build_creative_brief` 对同一输入重复调用结果一致；5 个素材位齐全；主图 `overlay_text` 为空（主图政策）；每个素材位至少 1 条证据。
- [x] AC-2：默认 `MockCreativeProvider` 不发起网络请求，输出 `provider=mock`、`rendered=false`；`CreativeProvider` Protocol 与注册表可替换，节点/API/UI 不依赖具体实现。
- [x] AC-3：`review_creative` 输出 0–100 分、5 个维度、block/warn/info findings；注入 `Best Seller` 等禁用宣称时 `passed=false` 且出现 block；mock 未渲染时给出「像素级未验证」提示且不虚报。
- [x] AC-4：`full_chain` 运行后 state 含 `creative_brief` / `creative_assets` / `creative_review`，仍为 `interrupt_before=["executor"]`，批准后 5 条 dry-run；`listing_only` / `ads_only` 不执行 creative。
- [x] AC-5：UI 出现「美工」tab（共 8 个），brief / rubric / 证据渲染正常；`scripts.verify_ui` 在两个入口通过。
- [x] AC-6：`scripts.verify_creative` 通过；fallback eval 10/10；`scripts.smoke_test`、`scripts.verify_local_backend`、`scripts.verify_ops`、`compileall` 通过；未新增依赖。
- [x] AC-7：README / `docs/verify.md` 明确「brief 与 rubric 为确定性规则、mock 未渲染图片、接入真实 AIGC 需实现 provider」，不把 mock 说成真实生成。

## 完成记录

- 完成时间：2026-11-24。
- `scripts.verify_creative`：`CREATIVE_VERIFY_OK slots=5 score=100.0 provider=mock negative_control=blocked execution=5_dry_run`；负向对照把 `Best Seller #1` 注入场景图后 `passed=false`、`block_count=1`、分数从 100 降到 91。
- 5 个 SKU 的 brief / mock / rubric 全部 `passed=true`、每个素材位有证据；`listing_only` / `ads_only` 不经过 creative。
- `scripts.verify_local_backend`：`LOCAL_BACKEND_OK skus=5 awaiting_approval=ok creative=5_mock approve=5_dry_run audit=6`。
- `scripts.verify_ui`（`API_BASE_URL=local`）：`UI_VERIFY_OK tabs=8 awaiting_approval=ok approve=5_dry_run reject=1_skip errors=0`。
- `scripts.verify_ops`：`OPS_VERIFY_OK skus=5 top=SKU-001:67.5 drivers=5 evidence=2 execution=5_dry_run`。
- fallback eval：`10/10 passed (100.0%); llm_calls=0, tokens=0, cost=$0.000000`。
- smoke：`errors=[]`、`creative={assets:5, score:100.0, passed:true, provider:mock}`、`execution_actions=5`、`current_issues=2`。
- 浏览器实测（ego-browser，1440×1000）：美工 tab 显示 `审核分 100 通过 / 素材位 5 / 拦截 0 / 警告 0`；素材位表主图为「无文字（主图政策）」、场景图「无文字」、细节图 `Breathable tape`、套装图 `12 lifts per kit`、A+ `For neck and jaw`，状态均为 `mock 未渲染`；审核发现含「mock 提供方未渲染图片，像素级产品还原无法验证」；`innerWidth == scrollWidth == 1707`；批准后 `已完成`、审计 5 条 `dry-run 成功`。
- 390×844 实测：`innerWidth == scrollWidth == bodyScrollWidth == 390`，无横向滚动。
- 截图：`.scratch/ui/T-011/creative-1440.png`、`live-completed.png`、`creative-390.png`。
- `compileall -q agent api app core rag evals scripts data` 退出 0；未新增依赖。
- 提交：`3fe7699`。
- 实际规模：新增 `agent/creative.py`（570 行，含注释与数据表）、`agent/nodes/creative.py`（47 行）、`scripts/verify_creative.py`（166 行）；总 diff 约 1,180 行，高于原估 < 650，原因是为 5 个素材位、5 个 rubric 维度与负向对照补齐了确定性逻辑与测试。
