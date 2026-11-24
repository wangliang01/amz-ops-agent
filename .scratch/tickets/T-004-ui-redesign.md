# [T-004] UI 中文改版（unslop）

- **Status**: Done (judge pass; pending commit)
- **Depends On**: 无
- **对应 SPEC**: `SPEC-004-ui-redesign.md` AC-1..AC-7
- **预估轮数**: 8
- **预估 diff 行数**: 原估 < 520；实际约 2000+（含 UI CSS / 自定义表格 / 验证脚本 / 文档）；属于呈现层大改，见完成记录。
- **Target Files**:
  - `app/streamlit_app.py`
  - `app/assets/mark.png`
  - `scripts/verify_ui.py`
  - `AGENTS.md`
  - `SPEC.md`
  - `SPEC-004-ui-redesign.md`
  - `docs/verify.md`
  - `PROGRESS.md`
  - `.claude/skills/unslop/`、`skills-lock.json`（CC BY 4.0，署名保留）

## 要解决的问题

默认 Streamlit 界面是英文模板：红按钮、蓝信息框、默认图表色、六个等宽 metric、截断状态、canvas 表格横向溢出、Deploy/菜单/📦 chrome。最重要的 HITL 闸门最弱，且界面不是中文。

## 范围

- 做：中文文案；纸白/墨色/黄铜视觉；闸门状态带；五步空状态；六 tab 重做；自定义表格/条形；四视口响应式；`unslop` 安装后的声明更新。
- 不做：API / 图 / 节点 / seed / 评测 / HITL 语义 / dry-run；新依赖；深色模式；第二 UI 技能；伪造数据。

## Stop conditions（遇到就停，不要硬做）

- 需要改 API / 节点 / 图 / 数据 / 评测
- 需要新增依赖或第二个 UI 技能
- 需要读取或打印 `.env` / key
- 同一处改 3 次不过
- AC 与 SPEC 冲突，或 AC 无法验证

## 验收标准（必须可执行）

- [ ] AC-1：界面文案中文（品牌名 / Listing / 评论 / 关键词除外）；无 `awaiting_approval` / `No rows.` / `Deploy` / `Run pipeline` / `Approve` / `Reject` 等英文 UI 文案。
- [ ] AC-2：空 / 待审批 / 已完成三状态截图；状态不截断；闸门是首屏焦点。
- [ ] AC-3：六个 tab 保留且顺序不变；Run / Approve / Reject 可用；批准 5 条 dry-run、拒绝 1 条 skip。
- [ ] AC-4：1440 / 1024 / 768 / 390 无页面级横向滚动；无控制台错误；正文对比度 ≥ 4.5:1；截图存 `.scratch/ui/T-004/`。
- [ ] AC-5：键盘可达、focus 可见；`prefers-reduced-motion` 不丢信息；状态不只靠颜色。
- [ ] AC-6：`-m evals.run_eval` 10/10；`-m scripts.smoke_test` 5 条 dry-run；AppTest 6 tabs / awaiting_approval / completed / 5 条动作；`compileall` 退出 0。
- [ ] AC-7：无新增依赖；`.env` / 报告 / 截图不进 git；`git status` 只含预期文件。

## 验证方式

```powershell
# 1. 语法
.\.venv\Scripts\python.exe -m compileall -q app agent api core rag evals scripts

# 2. 回归
.\.venv\Scripts\python.exe -m evals.run_eval
.\.venv\Scripts\python.exe -m scripts.smoke_test

# 3. AppTest（6 tabs / awaiting / completed / approve 5 / reject 1）
.\.venv\Scripts\python.exe -m scripts.verify_ui
# 期望：UI_VERIFY_OK tabs=6 awaiting_approval=ok approve=5_dry_run reject=1_skip errors=0

# 4. 浏览器四视口截图
# ego-browser 打开 http://127.0.0.1:8501
```

## 完成记录

- 提交：待裁判后提交
- 证据：
  - `compileall` 退出 0；`-m evals.run_eval` 10/10；`-m scripts.smoke_test` 5 条 dry-run；`-m scripts.verify_ui` → `UI_VERIFY_OK tabs=6 awaiting_approval=ok approve=5_dry_run reject=1_skip errors=0`。
  - 截图：`.scratch/ui/T-004/`（empty / awaiting / completed / error @1440；empty / completed @1024/768/390；六个 tab）。
  - 四视口 `scrollWidth == innerWidth`，越界元素 0；CDP 控制台报错 0。
  - 对比度：墨色 15.31:1、次级 6.49:1、弱化 4.65:1（纸白）/ 5.02:1（表面）、黄铜 4.54:1、奶油/黄铜 4.75:1。
  - 键盘 focus：skip link / 侧栏折叠 / 展开器 / SKU / 模式 / 运行 / tab 均为 `solid 2px #9C631C`；`prefers-reduced-motion` 下 transition/animation 为 0s。
  - 中文扫描：空状态与六个 tab 均无 `awaiting_approval` / `completed` / `No rows.` / `Deploy` / `Run pipeline` / `Approve` / `Reject` / `Insight` / `Compliance` / `Audit` / `Metrics` / `Connection` / `Status` / `Pipeline` / `Cost` / `LLM calls` / `HITL` / `GATE` / `Loading` / `Error`。

## 裁判记录

独立裁判（新上下文，只读）逐条复核：AC-1..AC-7 全部 PASS，最终 `READY TO COMMIT`。

| AC | 判定 | 证据 |
|---|---|---|
| AC-1 | PASS | 渲染文本与源码扫描：无禁用英文 UI 文案；错误态与展开器均中文；保留 Listing / 评论 / 关键词等业务数据英文 |
| AC-2 | PASS | `empty-1440.png` / `awaiting-1440.png` / `completed-1440.png` / `error-1440.png`；闸门卡首屏最显眼，状态不截断 |
| AC-3 | PASS | `scripts.verify_ui`：6 tabs；运行→待审批；批准 5 条 dry-run；拒绝 1 条 skip；错误 0 |
| AC-4 | PASS | 四视口截图；`scrollWidth == innerWidth`；越界元素 0；控制台报错 0；对比度均 ≥ 4.5:1 |
| AC-5 | PASS | focus 截图中 skip link / 侧栏折叠 / 输入框 / tab 均有 2px 黄铜描边；reduced-motion 为 0s；状态有文字不靠颜色 |
| AC-6 | PASS | compileall 0；eval 10/10；smoke 5 条；AppTest 覆盖 6 tabs / awaiting / completed / 5 动作 / 1 skip |
| AC-7 | PASS | requirements.txt 未改；`.env` / 报告 / 截图被忽略；git status 仅预期文件；unslop CC BY 4.0 署名保留 |
