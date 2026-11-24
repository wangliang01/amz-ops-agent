# SPEC-004 · UI 中文改版（unslop）

- **状态**: approved
- **Approved**: 2026-11-24，用户明确「中文界面 + 整体视觉改版，改好给我」
- **批准范围**: 只改 `app/streamlit_app.py` 的呈现层与中文文案；不改 API、图、节点、数据、HITL 语义。
- **关联**: `SPEC.md`（基线）、`SPEC-003-llm-regression.md`（评测）、`docs/adr/ADR-001-demo-boundaries.md`

## 一句话

把默认 Streamlit 的「模板感」改成一张中文的运营台账：纸白底、墨色字、黄铜闸门，最重要的 HITL 审批成为首屏视觉焦点，所有界面文案中文化。

## 用户与场景

- **演示者**：在 5 分钟里讲清「洞察 → Listing → 合规 → 广告 → 人工闸门 → dry-run」，界面不抢戏，闸门一眼可见。
- **评审者**：不读代码也能看懂当前状态、风险、审批结果和审计记录。
- **开发者**：功能、六个 tab、API 调用与 session state 不变，只换呈现。

## 本期范围

- **做**：
  - 中文界面：导航、按钮、状态、空/加载/错误、表头、提示、演示脚本。
  - 视觉方向：纸白 / 墨色 / 黄铜；IBM Plex Sans + Mono；4px 网格；发丝边框；无渐变、无发光。
  - 首屏状态带：HITL 闸门卡 + 4 个紧凑指标；状态不截断。
  - 空状态：五步 run sheet，最后一步是闸门；右侧闸门规则。
  - 六个 tab 的呈现重做：洞察、Listing、合规、广告、审计、指标。
  - 表格改为自定义 HTML，横向溢出限制在卡片内。
  - 图表改为自定义条形对比，只用一个强调色。
  - 响应式：1440 / 1024 / 768 / 390 四视口。
- **不做**：
  - 不改 API、LangGraph 图、节点、seed 数据、评测、HITL 语义、dry-run。
  - 不新增 Python 依赖；不引入第二个 UI 技能。
  - 不做深色模式；不做登录、多页面、真实店铺写接口。
  - 不伪造数据或装饰性图表。

## 明确不做（Non-goals）

- 不把 demo 包装成生产系统。
- 不为了视觉效果改业务数字、状态或审计记录。
- 不用 emoji 当图标；不用紫渐变、玻璃拟态、发光、彩色阴影。
- 不隐藏或删除 Stop / Approve / Reject 等功能控件。
- 不把英文业务数据（Amazon Listing 文案、评论原文、关键词）强行翻译成中文；只翻译界面文案与已知枚举。

## 验收标准（可执行）

- [ ] **AC-1 中文界面**：所有界面文案为中文（品牌名 `amz-ops-agent`、Listing 文案、评论原文、关键词等业务数据除外）；页面不出现 `awaiting_approval`、`completed`、`No rows.`、`Deploy`、`Run pipeline`、`Approve`、`Reject` 等英文 UI 文案。
- [ ] **AC-2 三状态**：空 / 待审批 / 已完成三状态各有截图；状态文字不截断；HITL 闸门是首屏最显眼的元素。
- [ ] **AC-3 功能不变**：六个 tab（洞察 / Listing / 合规 / 广告 / 审计 / 指标）保留且顺序不变；Run、Approve、Reject 仍可用；批准后 5 条 dry-run、拒绝后 1 条 skip。
- [ ] **AC-4 四视口**：1440 / 1024 / 768 / 390 宽无页面级横向滚动；无控制台错误；正文对比度 ≥ 4.5:1；截图存 `.scratch/ui/T-004/`。
- [ ] **AC-5 可访问性**：Tab 可达所有可操作元素，focus 可见；`prefers-reduced-motion` 下不丢信息；表格有表头，状态不只靠颜色。
- [ ] **AC-6 回归**：`-m evals.run_eval` → 10/10；`-m scripts.smoke_test` → 5 条 dry-run；`AppTest` → 6 tabs、awaiting_approval、completed、5 条动作；`compileall` 退出 0。
- [ ] **AC-7 卫生**：无新增依赖；`.env` / 报告 / 截图不进 git；`git status` 只含预期文件。

## 现状地图（已有代码必填）

- **入口**：`app/streamlit_app.py`（315 行）——`st.set_page_config`、侧栏 Connection/Run、Run/Approve/Reject、六指标、六个 tab、`st.dataframe`、`st.bar_chart`、`st.json`。
- **数据源**：`POST /runs`、`POST /runs/{id}/approve`、`GET /skus`、`GET /metrics`；`snapshot` 存 `st.session_state`。
- **状态字段**：`snapshot.status`（`awaiting_approval` / `completed`）、`snapshot.metrics.approved`、`state.execution_log`、`state.proposals`、`state.insights`、`state.draft_listing`、`state.compliance_report`、`state.ads_report`。
- **UI 声明**：`AGENTS.md` 只允许 `unslop`；本轮已安装到 `.claude/skills/unslop`。
- **不能碰的边界**：API / 图 / 节点 / seed / HITL / dry-run / 评测；不新增依赖；不读取 `.env`。

## 设计

### 审计摘要

默认 Streamlit 的三套强调色（红按钮、蓝信息框、默认图表色）、六个等宽 metric、截断的状态、默认 canvas 表格横向溢出、平台 chrome（Deploy / 菜单 / 📦）和英文技术文案，构成结构性模板感。按 unslop 的 heavy slop 走完整九轮，保留功能与区块顺序。

### 方向（5 行）

- **Product**：把评论痛点变成合规的 Listing 草稿和广告出价方案，然后在人工闸门前停住，dry-run 之前不执行任何动作。
- **Character**：operational, exact, a little warm。
- **World**：履约台面：牛皮纸、墨水、黄铜夹、打包胶带、一本 run ledger。
- **Moments**：① HITL 闸门做成黄铜印章式台账条目；② Listing current → new 像一张校样；③ ACOS backtest 用 baseline vs projected 双条对比。
- **Signature**：小方形 `GATE · DRY-RUN` 印章，只出现在状态卡和审计区。

### 视觉 token

- **颜色**：纸白 `#F7F4ED`、表面 `#FFFDF8`、抬升 `#EFEAE0`、墨色 `#1F1D1A`、次级 `#5E574C`、弱化 `#756D60`、发丝线 `rgba(31,29,26,.12)`、黄铜 `#9C631C`（为 4.5:1 对比度加深）、黄铜深 `#8A5515`、通过 `#2F6B4F`、拦截 `#A33A32`、警告 `#8A5A12`。
- **字体**：IBM Plex Sans（界面）+ IBM Plex Mono（数字/元信息）；中文回退 Microsoft YaHei / PingFang SC；400/500/600；数字 `tabular-nums`。
- **布局**：侧栏 280px；主区最大 1280px；页边距 32px；4px 网格；卡片 14–16px 圆角；发丝边框；无阴影（闸门卡最多一条中性软阴影）。
- **动效**：只保留 hover / focus / 短淡入；无循环、无弹跳、无布局属性动画；`prefers-reduced-motion` 关闭。

### 中文文案

- 导航：连接 / 运行 / 审批闸门；按钮：运行流水线 / 批准并执行 dry-run / 拒绝。
- 状态：等待审批 / 已完成 / 已拒绝 / 失败。
- Tab：洞察 / Listing / 合规 / 广告 / 审计 / 指标。
- 空状态：还没有运行 / 从一次评论洞察开始 / 闸门规则。
- 错误：API 不可达 / 先在终端启动 API。
- 已知枚举映射：`full_chain` → 全链路、`listing_only` → 仅 Listing、`ads_only` → 仅广告、`auto` → 自动选择；`block/warn/info` → 拦截/警告/提示；`dry_run_success` → dry-run 成功。
- 业务数据（Listing 英文文案、评论原文、关键词、规则说明）保留原文。

## 技术决策

| 项 | 选择 | 理由 | 备选 / 何时重评 |
|---|---|---|---|
| 呈现方式 | 自定义 HTML + CSS，保留 `st.button` / `st.selectbox` / `st.tabs` | 完全控制版式，功能不丢 | Streamlit 大版本升级后重评选择器 |
| 表格 | 自定义 HTML 表格 | 去掉 canvas 表格与页面级横滚 | 数据量 > 100 行时改回 dataframe |
| 图表 | 自定义条形 | 一个强调色、无默认配色 | 需要交互时改用 Altair |
| 字体 | Google Fonts + 系统回退 | 方向明确，离线可用 | 内网部署时改为本地字体 |
| 主题 | CSS 变量覆盖，不加 `.streamlit/config.toml` | 避免动 gitignore 与本地配置 | 需要深色模式时再加 config |

## 风险与未知

- **风险 1**：Streamlit DOM 选择器随版本变化；用 `data-testid` 为主，视觉验收兜底。
- **风险 2**：中文回退字体在不同 Windows 机器上不同；用 Microsoft YaHei / PingFang SC 栈。
- **风险 3**：英文业务数据较长，表格可能仍溢出；限制在卡片内滚动。
- **风险 4**：移动端 Streamlit 侧栏折叠行为不同；390px 需实测。
- **风险 5**：自定义 HTML 可能被 Streamlit sanitize；只用 `unsafe_allow_html` 的静态结构，所有动态值 `html.escape`。
- **未知**：浏览器控制台是否有第三方字体/Streamlit 警告；以截图和控制台检查为准。

## 批准记录

- 用户原话：「还有，我们要中文的，不要英文的界面，加上一起，改好给我」
- 批准时间：2026-11-24
- 批准范围：中文界面 + 整体视觉改版；不改后端与业务语义。
