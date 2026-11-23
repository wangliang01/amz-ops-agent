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

```powershell
$env:LLM_ENABLED="false"; $env:EMBEDDING_ENABLED="false"
.\.venv\Scripts\python.exe -m evals.run_eval
.\.venv\Scripts\python.exe -m scripts.smoke_test
```

`evals.run_eval` 期望（2026-11-23 实测）：

```
G-001    SKU-001  PASS    -
...
G-010    SKU-005  PASS    -
10/10 passed (100.0%). Report: ...\evals\report.json
```

`scripts.smoke_test` 期望（2026-11-23 实测，节选）：

```json
{
  "errors": [],
  "compliance": {"passed": true, "score": 100, "draft_issues": 0, "current_issues": 6, "fixed_count": 6},
  "execution_actions": 5,
  "metrics": {"llm_calls": 0}
}
```

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
curl.exe -s -X POST http://127.0.0.1:8000/runs -H "Content-Type: application/json" -d '{"sku_id":"SKU-003","mode":"full_chain"}'
```

期望：

```
{"ok":true,"llm_enabled":false,"vector_index":false}
```

- `/skus` 返回 5 个 SKU。
- `/runs` 返回 `"status":"awaiting_approval"`、`"next":["executor"]`；记下 `run_id`。

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

1. 侧栏选 `SKU-003` + `full_chain`，点 **Run pipeline**。
2. 期望：状态 `awaiting_approval`；主区出现 `Insight` / `Listing` / `Compliance` / `Ads` / `Audit` / `Metrics` 六个 tab。
3. 侧栏点 **Approve**。期望：状态 `completed`；`Audit` 出现 5 条 dry-run 记录；`Metrics` 显示 `llm_calls: 0`（无 LLM 时）。
4. 停掉 API 再刷新。期望：侧栏 `API not reachable` + 启动命令，不白屏。

UI 逻辑可用 `streamlit.testing.v1.AppTest` 复现。2026-11-24 实测输出：

```
title: ['amz-ops-agent']
tabs: ['Insight', 'Listing', 'Compliance', 'Ads', 'Audit', 'Metrics']
after run: awaiting_approval ['executor']
after approve: completed exec_actions: 5
compliance: True 100
errors: []
```

## 4. UI 验收（有界面时必填）

本轮（文档回填）**没有 UI 改动**，因此未做 4 视口截图。任何 UI 改动必须补齐：

- 视口：1440 / 1024 / 768 / 390，截图存 `.scratch/ui/<ticket>/`
- 必须为 0：横向滚动、控制台报错、破图 / 空图、正文对比度 < 4.5:1
- 三种状态各一张截图：空 / 加载 / 错误
- 键盘：Tab 可达所有可操作元素，focus 可见
- 动效：`prefers-reduced-motion` 下不丢信息
- 只调用 `AGENTS.md` 声明的 `unslop`。当前未安装：先运行 `/agent-harness:extras --declared`，不要临时换另一个 UI 技能。

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
