# 验证 amz-ops-agent

> 这是唯一的验证说明。`AGENTS.md` 的「全部验证」指向这里；`.claude/skills/verify-app/SKILL.md` 和 `.codebuddy/skills/verify-app/SKILL.md` 只是薄包装。

按顺序执行，任何一步失败就停下并原样贴出输出，不要跳过、不要重试超过两次。

## 1. 静态检查

本项目未配置 mypy / ruff。最低限度做语法编译：

```powershell
.\.venv\Scripts\python.exe -m compileall -q agent api app core rag evals scripts
```

期望：无输出，退出码 0。**不要声称「类型检查通过」。**

## 2. 测试 / 评测

种子数据已随仓库提供。需要从公开数据集重建时（约 540MB 下载，固定快照 + sha256）：

```powershell
.\.venv\Scripts\python.exe data\fetch_real_seed.py
# 期望：cache hit ... / Wrote real-data seed ...
#       SKUs: 5 / reviews: 250 / historical listings: 20 / ads daily rows: 450
```

`data/seed/PROVENANCE.md` 列明真实字段、模拟字段、匿名化与许可。

评测与冒烟：

```powershell
$env:LLM_ENABLED="false"; $env:EMBEDDING_ENABLED="false"
.\.venv\Scripts\python.exe -m evals.run_eval
.\.venv\Scripts\python.exe -m scripts.smoke_test
.\.venv\Scripts\python.exe -m scripts.verify_ops
.\.venv\Scripts\python.exe -m scripts.verify_local_backend
```

`scripts.verify_ops` 校验选品排名确定性、5 个 SKU 的补货/预算/定价计划，以及 `full_chain` 仍停在 executor 闸门、批准后 5 条 dry-run：

```text
OPS_VERIFY_OK skus=5 top=SKU-001:67.5 drivers=5 evidence=2 execution=5_dry_run
```

`scripts.verify_local_backend` 使用临时 `runs.sqlite` / `checkpoints.sqlite`，验证 Streamlit 云端单进程后端的完整闸门：

```text
LOCAL_BACKEND_OK skus=5 awaiting_approval=ok approve=5_dry_run audit=6
```

`evals.run_eval` 期望（2026-11-24 实测）：

```
G-001    SKU-001  PASS    -
...
G-010    SKU-005  PASS    -
10/10 passed (100.0%); llm_calls=0, tokens=0, cost=$0.000000. Report: ...\evals\report.json
```

无 key 时这是**兜底回归**（`llm_calls=0`），不能证明真实 LLM 路径；真实调用见 §3.4。有 key 且未加 `--require-llm` 时，默认评测会实际调用 LLM，报告落到 `evals/llm_report.json`，模型非确定性失败会以退出 1 呈现；无 key 时落 `evals/report.json`。要稳定复验兜底路径，请显式设置 `LLM_ENABLED=false; EMBEDDING_ENABLED=false`。

`scripts.smoke_test` 期望（2026-11-24 实测，节选）：

```json
{
  "errors": [],
  "compliance": {"passed": true, "score": 100, "draft_issues": 0, "current_issues": 2, "fixed_count": 2},
  "execution_actions": 5,
  "metrics": {"llm_calls": 0}
}
```

`current_issues=2` 是 SKU-003 真实 Listing 命中的两条 warn：description 的 `Guarantee` 与 bullet 的 `medical grade`；草稿基线已清零。

**注意**：必须用 `-m`。直接跑 `python scripts\smoke_test.py` 会 `ModuleNotFoundError: No module named 'agent'`。

## 3. 真实运行

### 3.1 API

终端 A：

```powershell
$env:LLM_ENABLED="false"; $env:EMBEDDING_ENABLED="false"
.\.venv\Scripts\python.exe -m uvicorn api.main:app --port 8000
```

终端 B：

```powershell
curl.exe -s http://127.0.0.1:8000/health
curl.exe -s http://127.0.0.1:8000/skus
curl.exe -s http://127.0.0.1:8000/opportunities
curl.exe -s -X POST http://127.0.0.1:8000/runs -H "Content-Type: application/json" -d '{"sku_id":"SKU-003","mode":"full_chain"}'
```

期望：

```
{"ok":true,"llm_enabled":false,"vector_index":false}
```

- `/skus` 返回 5 个 SKU。
- `/opportunities` 返回 `items` 5 条，`rank` 1–5，每条含 `score` / `drivers` / `evidence`。
- `/runs` 返回 `"status":"awaiting_approval"`、`"next":["executor"]`；`state.ops_plan` 含 `inventory` / `budget` / `price_guardrail` / `roi`；记下 `run_id`。

批准：

```powershell
curl.exe -s -X POST http://127.0.0.1:8000/runs/<run_id>/approve -H "Content-Type: application/json" -d '{"decision":"approved","actor":"verify"}'
```

期望：`"status":"completed"`，`state.execution_log` 有 5 条 dry-run 动作。2026-11-24 实测：合规 `passed=true`、`score=100`。

### 3.2 UI

```powershell
.\run.ps1
```

打开 <http://localhost:8501>：

1. 侧栏选 `SKU-003`（真实颈膜商品，3.4 星）+ `full_chain`，点 **运行流水线**。
2. 期望：状态 `等待审批`；主区出现 洞察 / Listing / 合规 / 广告 / 选品 / 审计 / 指标 七个 tab。
3. 打开 **选品**：5 个 SKU 的机会排名、驱动因素与真实评论证据；下方是补货/预算/定价。打开 **指标**：ROI 显示人工分钟节省、LLM 成本与净收益。
4. 侧栏点 **批准并执行 dry-run**。期望：状态 `已完成`；`审计` 出现 5 条 dry-run 记录；`指标` 显示 `模型调用: 0`（无 LLM 时）。
5. 停掉 API 再刷新。期望：侧栏 `API 不可达` + 启动命令，不白屏。

UI 逻辑可用 `streamlit.testing.v1.AppTest` 复现：

```powershell
.\.venv\Scripts\python.exe -m scripts.verify_ui
# 期望：UI_VERIFY_OK tabs=7 awaiting_approval=ok approve=5_dry_run reject=1_skip errors=0
```

Streamlit Cloud 单进程模式（不需要先启动 API）：

```powershell
$env:API_BASE_URL="local"
$env:LLM_ENABLED="false"; $env:EMBEDDING_ENABLED="false"
.\.venv\Scripts\python.exe -m scripts.verify_ui
# 云端入口本身：
$env:UI_APP=(Resolve-Path 'app\streamlit_cloud.py').Path
.\.venv\Scripts\python.exe -m scripts.verify_ui
# 期望：两者均为 UI_VERIFY_OK ...

2026-11-24 实测输出：

```
UI_VERIFY_OK tabs=7 awaiting_approval=ok approve=5_dry_run reject=1_skip errors=0
```

### 3.3 HITL 重启持久化

```powershell
.\.venv\Scripts\python.exe scripts\verify_hitl_restart.py
```

期望：`HITL_RESTART_OK <run_a> <run_b>`。脚本用临时 `runs.sqlite` / `checkpoints.sqlite`，起停 API 三次，验证：

- 停/起后 `GET /runs/{id}` 仍为 `awaiting_approval`，`next` 为 `["executor"]`；
- 重启后 Approve → `completed`，`execution_log` 5 条 `dry_run_success`，审计 5 条 `execute_dry_run`；
- 再次重启后重复 Approve 幂等，执行记录不增加；
- 重启后 Reject → `completed`，`execution_log` 只有 1 条 `skip`，审计有 `execute_skipped`、无 `execute_dry_run`；
- checkpoint 库含 `checkpoints` 表。

默认 API 使用 `data/checkpoints.sqlite`；该文件及 `-wal` / `-shm` 已被 `.gitignore` 的 `data/*.sqlite*` 覆盖。

### 3.4 真实 LLM 回归（需 key）

默认评测在无 key 时走规则兜底，`llm_calls=0`，只能证明兜底路径。真实 LLM 回归必须显式开启。

1. 在 `.env` 中配置（不要把 key 提交或贴到聊天里）：

```dotenv
LLM_ENABLED=true
OPENAI_API_KEY=...
OPENAI_BASE_URL=https://apihub.agnes-ai.com/v1
CHAT_MODEL=agnes-3.0-flash
CHEAP_MODEL=agnes-3.0-flash
# 端点不支持 embeddings 时：
EMBEDDING_ENABLED=false
# provider 刊例价（USD / 1M token），影响 --max-cost-usd 估算：
MODEL_PRICE_INPUT=0.05
MODEL_PRICE_OUTPUT=0.15
# 免费 provider 容易触发 RPM 限流；case 间隔按需设置：
LLM_CASE_DELAY_SEC=40
```

任何 OpenAI 兼容端点均可；把 Base URL、模型名、价格与限流间隔替换为 provider 对应值。不要把真实 key 提交或贴到聊天里。

2. 单 case 连通性（几分钱）：

```powershell
.\.venv\Scripts\python.exe -m evals.run_eval --require-llm --case G-001 --max-cost-usd 0.10
```

期望：退出码 0，`1/1 passed`；`evals/llm_report.json` 中 `mode="llm"`、`model` 非空、`llm_calls >= 3`、`tokens.total > 0`、`cost_usd > 0`。

3. 全量：

```powershell
.\.venv\Scripts\python.exe -m evals.run_eval --require-llm --max-cost-usd 0.50
```

期望：退出码 0（全过）或 1（有结构性失败，`failures` 列原因）。真实模型输出非确定，失败是回归证据，不要为了全绿去改 prompt。

2026-11-24 真实数据实测：9/10，`llm_calls=30`、`tokens.total=63173`、`cost=$0.004921`；`G-003` 失败原因为 `missing: nail art drill`，未放宽 golden。免费 / 低 RPM 端点如出现 429，优先增大 `LLM_CASE_DELAY_SEC` 或升级 provider 套餐；不会通过放宽 AC 来“过测”。

4. 无 key 时 `--require-llm` 必须失败：

```powershell
$env:LLM_ENABLED="false"; .\.venv\Scripts\python.exe -m evals.run_eval --require-llm
# 期望：退出码 2，提示 OPENAI_API_KEY，不执行任何 case
```

5. 成本闸门：

```powershell
.\.venv\Scripts\python.exe -m evals.run_eval --require-llm --max-cost-usd 0.0001
# 期望：退出码 3，报告 aborted="cost_cap"，results 只含已执行 case
# 无 key 时该命令会先触发退出 2，而不是 3。
```

报告字段：`mode`、`model`、`require_llm`、`cases`、`passed`、`failed`、`pass_rate`、`llm_calls`、`tokens{prompt,completion,total}`、`cost_usd`、`duration_sec`、`aborted`、`results[]`（每 case 含 `llm_calls` / `tokens` / `cost_usd` / `latency_sec` / `failures`）。`mode` 按实际调用判定：`llm_calls > 0` 才是 `llm`，否则 `fallback`。

`--limit N` 只跑前 N 条；`--report PATH` 指定报告位置。若 provider 不返回 usage 元数据，会出现 `llm_calls > 0` 但 `tokens.total=0`、`cost_usd=0`，此时 AC-2 视为未达成，换支持 usage 的端点或模型。

`evals/report.json` 与 `evals/llm_report.json` 都被 gitignore；报告不含 key、完整 prompt 或完整响应。确定性检查：

```powershell
.\.venv\Scripts\python.exe -m scripts.verify_llm_eval
# 期望：LLM_EVAL_VERIFY_OK
```

## 4. UI 验收（有界面时必填）

T-004 已完成中文 UI 改版（`SPEC-004-ui-redesign.md`）。UI 逻辑用 AppTest 验证：

```powershell
# 需先启动 API（:8000）
.\.venv\Scripts\python.exe -m scripts.verify_ui
# 期望：UI_VERIFY_OK tabs=7 awaiting_approval=ok approve=5_dry_run reject=1_skip errors=0
```

浏览器验收（2026-11-24，`ego-browser`）：

- 截图：`.scratch/ui/T-004/`；1440 下 `empty-1440.png` / `awaiting-1440.png` / `completed-1440.png` / `error-1440.png`，以及 `empty|completed-{1024,768,390}.png` 和六个 tab 截图。`.scratch/ui/` 已 gitignore。
- 视口：1440 / 1024 / 768 / 390 实测 `innerWidth == docScrollWidth == bodyScrollWidth`，无越界元素；768 / 390 侧栏折叠为抽屉。
- 控制台：CDP `Runtime` / `Log` 事件为 0 条报错；无破图。
- 对比度：墨色 15.31:1、次级 6.49:1、弱化 4.65:1（纸白）/ 5.02:1（表面）、黄铜 4.54:1、奶油/黄铜 4.75:1；正文均 ≥ 4.5:1。
- 键盘：Tab 可达 skip link、侧栏折叠、展开器、SKU / 模式、运行、七个 tab；focus 为 `solid 2px #9C631C`。
- 动效：`prefers-reduced-motion: reduce` 下 `transition-duration` / `animation-duration` 均为 `0s`，信息不依赖动画。
- 只使用 `AGENTS.md` 声明的 `unslop`（已安装到 `.claude/skills/unslop`，CC BY 4.0，署名保留在 `SKILL.md`）。
- 注：Streamlit 固定侧栏在 full-page 截图中会错位，因此状态截图用视口截图；页面级横向滚动仍按 `scrollWidth` 实测为 0。

## 5. 结论

输出四行，缺一不可：

```
改动是否生效：是 / 否
证据：<贴关键输出或截图路径>
边缘情况：<列出没覆盖的，或写「已覆盖 X/Y/Z」>
风险：<可能影响到的其他功能>
```

## 禁止

- 只贴 diff 就说「已完成」
- 用「应该可以」「理论上」代替实际运行
- 为了让验证通过而放宽测试
