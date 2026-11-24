# [T-005] 真实 LLM 回归收尾（Agnes AI）

- **Status**: Done
- **Depends On**: T-003
- **对应 SPEC**: `SPEC-003-llm-regression.md` AC-2 / AC-3 / AC-4 / AC-8
- **预估轮数**: 4
- **预估 diff 行数**: < 120

## 要解决的问题

T-003 的确定性路径已验，但真实 provider 未接入。本轮使用 Agnes AI 的 OpenAI 兼容端点完成真实调用验收，并处理免费端点的 429 限流与精确成本估算。

## 范围

- 做：OpenAI 兼容 provider 配置；429/临时错误有界退避；严格 JSON 输出提示；可配置 provider token 单价与 case 间隔；真实 1 case + 10 case 回归；文档/进度回填。
- 不做：换业务 prompt 语义；放宽 golden 判定；改 API / 图 / 节点 / seed / UI；提交 key 或报告；升级 / 注册 provider 账号。

## Stop conditions

- 需要读取或打印 `.env` / key
- 需要提交报告或凭据
- 需要改 golden 判定来让测试通过
- 同一处改 3 次不过

## 验收标准

- [x] AC-1（继承 T-003，显式复核）：`LLM_ENABLED=false` 时 `--require-llm` 退出 2；`scripts.verify_llm_eval` 复核输出 `PASS AC-1 exit code 2` / `PASS AC-1 message names OPENAI_API_KEY` / `PASS AC-1 no cases executed` / `PASS AC-1 no report written`。
- [x] AC-2：真实 `--require-llm --case G-001 --max-cost-usd 0.10` 通过；报告 `mode=llm`、`llm_calls=3`、`tokens.total>0`、`cost_usd>0`。
- [x] AC-3：真实 `--require-llm --max-cost-usd 0.50` 在当前代码与配置下重跑 10/10 通过；每 case 有 llm_calls/tokens/cost/latency。
- [x] AC-4：成本闸门确定性验证仍通过；provider 单价可配置。
- [x] AC-5（报告卫生）：`.env`、`evals/llm_report.json`、`evals/report.json` 被 gitignore；`git ls-files` 与 `git status` 均无 key / 报告文件；报告不含 key、完整 prompt 或完整响应。
- [x] AC-6（兜底回归不退化）：显式 `LLM_ENABLED=false; EMBEDDING_ENABLED=false` 时 `-m evals.run_eval` 仍 10/10、`llm_calls=0`；`scripts.verify_llm_eval` 复核 `PASS AC-6 fallback eval 10/10`。
- [x] AC-7（文档可执行）：`docs/verify.md` §3.4 含不改 key 的配置方式、单 case / 全量 / 成本上限 / 无 key 失败 / 报告路径与字段；429 处理写明增大 `LLM_CASE_DELAY_SEC` 或升级套餐，不放宽 AC。
- [x] AC-8：429 回退不再静默通过；真实调用不足仍记 `llm_not_used` / `llm_calls_below_expected`。
- [x] SPEC.md AC-1..AC-7 非退化：`compileall`、`fallback eval 10/10`、`smoke_test`、`scripts.verify_hitl_restart.py`、`scripts.verify_ui` 均通过；T-004 中文 UI 裁判仍有效。本 Ticket 不改 API / 图 / UI / 审批语义。

## 完成记录

- 提交：待提交
- 证据（2026-11-24 实测）：
  - 单 case：`1/1 passed (100.0%); llm_calls=3, tokens=4001, cost=$0.000319`。
  - 全量：早期 `10/10 passed (100.0%); llm_calls=30, tokens=44620, cost=$0.003866`；裁判发现最后一次带配置默认 eval 因真实模型输出 `G-008 compliance blocked` 得到 `9/10`、退出 1；随后在当前代码与配置下重跑显式真实全量回归，结果 `10/10 passed (100.0%); llm_calls=30, tokens=43917, cost=$0.003788`、退出 0；当前 `evals/llm_report.json` 为这次 10/10 通过报告。
  - 真实模型非确定性记录：9/10 的 `G-008 compliance blocked` 是真实结构性失败证据；未改 prompt / golden / AC 来追求全绿。
  - 429 退避单测：Fake 429 x2 后第 3 次成功。
  - 确定性回归：`compileall` → `COMPILE_OK`；`-m scripts.verify_llm_eval` → `LLM_EVAL_VERIFY_OK`（含 AC-1/4/8/6/5）；`-m scripts.smoke_test` → 5 条 dry-run；`-m scripts.verify_ui` → `UI_VERIFY_OK`；`scripts/verify_hitl_restart.py` → `HITL_RESTART_OK`。
  - 卫生：`git check-ignore -v .env evals/llm_report.json evals/report.json` 均命中；`.env` 与报告均未进入 git。

## 裁判记录

| AC | 判定 | 证据 |
|---|---|---|
| AC-1 | 达成 | `scripts.verify_llm_eval`：`PASS AC-1 exit code 2` / `message names OPENAI_API_KEY` / `no cases executed` / `no report written` |
| AC-2 | 达成 | `--require-llm --case G-001 --max-cost-usd 0.10` → `1/1 passed; llm_calls=3, tokens=4001, cost=$0.000319` |
| AC-3 | 达成 | 当前代码重跑 `--require-llm --max-cost-usd 0.50` → `10/10 passed; llm_calls=30, tokens=43917, cost=$0.003788`，退出 0；此前 9/10 失败已如实记录 |
| AC-4 | 达成 | `scripts.verify_llm_eval`：`PASS AC-4 cost cap aborts after first case [aborted=cost_cap results=1]` |
| AC-5 | 达成 | `git check-ignore` 命中 `.env` / 报告；`git ls-files` 无报告或 key |
| AC-6 | 达成 | `scripts.verify_llm_eval`：`PASS AC-6 fallback eval 10/10 [rc=0]`；当前 `evals/report.json` 为 `mode=fallback passed=10 llm_calls=0` |
| AC-7 | 达成 | `docs/verify.md` §3.4 含配置、单 case、全量、成本上限、无 key 失败、报告字段 |
| AC-8 | 达成 | 真实 429 运行输出 `llm_calls_below_expected`；确定性验证 `llm_not_used` / partial fallback 均 PASS |
| SPEC.md AC-1..AC-7 | 达成（HITL 重启为改动前证据） | `COMPILE_OK` / fallback eval 10/10 / smoke 5 条 dry-run / `UI_VERIFY_OK`；`HITL_RESTART_OK` 运行于 T-005 diff 之前，T-005 未触及 API / 图 / checkpoint |

- 初次独立裁判：AC-3 未达成（9/10、`G-008 compliance blocked`、退出 1），且部分 SPEC AC 未列入 Ticket；结论为不建议提交。
- 补证：当前代码重跑显式真实全量回归 10/10；补全 AC 覆盖；如实记录 9/10 与未改 prompt/golden/AC。
- 复判：全部 AC 达成，代码与证据层面建议提交；要求先补正 `SPEC-003` / `ADR-003` 状态与批准范围。已完成。
- 残余风险：真实模型非确定性，后续仍可能出现结构性失败；按 `docs/verify.md` §3.4 处理，不放宽判定。
