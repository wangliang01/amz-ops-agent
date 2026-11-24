# [T-003] 真实 LLM 回归入口

- **Status**: Blocked（AC-1 / AC-5 / AC-6 / AC-7 已验；AC-2 / AC-3 / AC-4 / AC-8 需真实 key）
- **Depends On**: 无
- **对应 SPEC**: `SPEC-003-llm-regression.md` AC-1..AC-8
- **预估轮数**: 6
- **预估 diff 行数**: < 220
- **Target Files**:
  - `evals/run_eval.py`
  - `scripts/verify_llm_eval.py`
  - `.gitignore`
  - `docs/verify.md`
  - `PROGRESS.md`
  - `.scratch/decisions.tsv`

## 要解决的问题

`evals/run_eval.py` 在 `llm_ready=False` 时静默走规则兜底，仍报 10/10；报告里没有模型、调用次数、token、成本，无法区分真实 LLM 与兜底。真实调用又涉及费用与密钥，不能默认开启。

## 范围

- 做：`--require-llm` / `--case` / `--limit` / `--max-cost-usd` / `--report`；无 key 退出码 2；成本超限退出码 3；报告记录 `mode` / `model` / `llm_calls` / `tokens` / `cost_usd` / `duration_sec` / `aborted` 与每 case 指标；`llm_not_used` / `llm_calls_below_expected` 失败；文档与 gitignore。
- 不做：业务 prompt、provider、node、graph、API、CI 密钥、保存完整 prompt / 响应。

## Stop conditions（遇到就停，不要硬做）

- 需要新增依赖 / 改业务节点 / 改 HTTP 接口
- 需要读取或打印 `.env` / key
- 同一处改 3 次不过
- AC 与 SPEC 冲突，或 AC 无法验证

## 验收标准（必须可执行）

- [x] AC-1：`LLM_ENABLED=false` 或 key 为空时，`-m evals.run_eval --require-llm` 退出码 2，输出含 `OPENAI_API_KEY`，不执行任何 case；默认 `-m evals.run_eval` 仍 10/10。
- [ ] AC-2（需 key）：配置 key 后，`--require-llm --case G-001 --max-cost-usd 0.10` 执行 1 条；报告 `mode="llm"`、`llm_calls > 0`、`tokens.total > 0`、`cost_usd > 0`、`model` 非空。
- [ ] AC-3（需 key）：`--require-llm --max-cost-usd 0.50` 执行 10 条；每 case 有 `llm_calls` / `tokens` / `cost_usd` / `latency_sec`；失败时退出码 1 且 `failures` 列原因，全过退出码 0。
- [ ] AC-4（确定性路径已验，真实成本需 key）：`--max-cost-usd 0.0001` 时首个 case 后停止，退出码 3，报告 `aborted="cost_cap"`，`results` 只含已执行 case。
- [x] AC-5：`evals/llm_report.json` 被 gitignore；报告 / stdout 不含 key 值、完整 prompt、完整响应；`git status` 不出现报告。
- [x] AC-6：默认 `-m evals.run_eval` 仍 10/10；`evals/report.json` 原有键不变，新键只增不减。
- [x] AC-7：`docs/verify.md` 有「LLM 回归」段：配置（不打印 key）、单 case、全量、成本上限、无 key 预期、报告路径与字段。
- [ ] AC-8（确定性路径已验，真实失败需 key）：真实调用失败 / 非法 JSON 走兜底时，该 case 记 `llm_not_used` 或 `llm_calls_below_expected` 失败，不静默通过。

## 验证方式

```powershell
# 确定性验证：无 key 退出码、成本闸门、失败注入、兜底回归、gitignore
.\.venv\Scripts\python.exe -m scripts.verify_llm_eval

# 默认兜底回归
.\.venv\Scripts\python.exe -m evals.run_eval

# 有 key 后（不要把 key 贴到聊天里）
.\.venv\Scripts\python.exe -m evals.run_eval --require-llm --case G-001 --max-cost-usd 0.10
.\.venv\Scripts\python.exe -m evals.run_eval --require-llm --max-cost-usd 0.50
```

## 当前阻塞

本机 `llm_ready=False`，AC-2 / AC-3 的真实调用与 AC-4 的真实成本闸门需要用户在 `.env` 配置 `OPENAI_API_KEY` 后执行；本轮先完成并验证 AC-1 / AC-5 / AC-6 / AC-7 与 AC-4 / AC-8 的确定性路径。

## 完成记录

- 提交：待提交
- 证据（2026-11-24 实测）：
  - `-m scripts.verify_llm_eval` → 8 项全 PASS，`LLM_EVAL_VERIFY_OK`。
  - `-m evals.run_eval` → `10/10 passed (100.0%); llm_calls=0, tokens=0, cost=$0.000000`；报告键含 `mode=fallback`、`aborted=null`。
  - `-m evals.run_eval --require-llm`（无 key）→ 退出码 2，输出 `OPENAI_API_KEY` 提示，未执行 case。
  - `-m evals.run_eval --case G-001` → `1/1 passed`。
  - `-m compileall -q agent api app core rag evals scripts` → 退出码 0。
  - `git check-ignore evals/llm_report.json` 命中；`git status` 不出现报告文件。
  - AC-4 / AC-8 由 `scripts/verify_llm_eval.py` 的 fake runner 确定性验证：成本 0.001 > 0.0001 → `aborted=cost_cap`、只 1 条结果；`calls=0` → `llm_not_used`；`calls=2/3` → `llm_calls_below_expected`。

## 裁判记录

| AC | 判定 | 证据 |
|---|---|---|
| AC-1 | 达成 | `run_eval.py:219-225` 在 `_load_cases` / `db.init_db` 前返回 2；两种无 key 组合实跑均 `EXIT=2`，stderr 含 `OPENAI_API_KEY`，无 case 输出；默认跑 10/10 |
| AC-2 | 无法验证（需 key） | fake runner 端到端报告字段齐全，但非真实 provider；真实 `llm_calls/tokens/cost` 待 key |
| AC-3 | 无法验证（需 key） | 真实 10 条未跑；确定性契约与退出码 0/1 已由 fake 端到端验证 |
| AC-4 | 达成（确定性路径） | `run_eval.py:118-121` 累计超限即 `break` + `aborted="cost_cap"`，`:284-285` 优先返回 3；`verify_llm_eval` 与 fake `main()` 均验证 results=1；真实成本待 key |
| AC-5 | 达成 | `.gitignore:14-15` 同时忽略两份报告；`git check-ignore -v` 命中；报告 grep 无 key/prompt/响应；`git status` 无报告 |
| AC-6 | 达成 | 默认 10/10、`llm_calls=0`；顶层与 results 原有键全在，新增键纯追加 |
| AC-7 | 达成 | `docs/verify.md:125-175` 覆盖配置、单 case、全量、无 key、成本闸门、报告字段与 `verify_llm_eval` |
| AC-8 | 达成（确定性路径） | `run_eval.py:105-115` 对 `calls=0` / `calls<3` 追加失败并 `passed=False`；脚本两条 PASS；真实 provider 失败待 key |

### 裁判发现与处理

- **中**：provider 不返回 usage 时会出现 `llm_calls > 0` 但 `tokens.total=0`、`cost_usd=0`；已写入 `docs/verify.md` §3.4，配 key 后确认。
- **低**：有 key 且默认跑时报告落 `llm_report.json` 未说明 → 已补 §2。
- **低**：`mode` 只看配置 → 改为按实际 `llm_calls > 0` 判定。
- **低**：无 key「未执行 case」断言偏弱 → `verify_llm_eval` 改为断言 `--report` 文件未生成。
- **低**：文档缺 `--limit` / `--report` 与无 key 成本闸门说明 → 已补。
- **信息**：`EXPECTED_LLM_CALLS` 硬编码 3；当前 `listing_only` 正确，未来新增 mode 需同步维护。
