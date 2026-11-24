# ADR-003 真实 LLM 回归：显式开启、成本封顶、不存密钥

- **日期**: 2026-11-24
- **状态**: accepted（随 `SPEC-003` 于 2026-11-24 批准；T-005 扩展 429 退避与单价配置）
- **关联**: `SPEC-003-llm-regression.md`

## 背景

现有 `evals/run_eval.py` 在 `LLMClient` 未启用或调用失败时静默走规则兜底，仍然报告 10/10。没有 key 的机器无法区分「LLM 真的生成了」和「兜底生成的」，这让「LLM 回归」名不副实。真实调用又涉及费用、非确定性与密钥安全，不能默认开启。

## 备选方案

| 方案 | 优点 | 代价 | 结论 |
|---|---|---|---|
| A 扩展 `run_eval.py`，`--require-llm` 显式开启 + 成本闸门 | 复用断言、默认无 key 可跑、报告可审计 | 需要维护一个开关与成本估算 | **采用** |
| B 独立 `run_llm_eval.py` | 互不影响 | 断言与 golden 读取漂移 | 拒绝 |
| C pytest 参数化 | 生态好 | 新增依赖、CI 变重 | 拒绝 |
| D 只手工跑一次 | 零改动 | 不可重复、无成本记录 | 拒绝 |

## 决定

在现有评测入口增加 `--require-llm`、`--case`、`--limit`、`--max-cost-usd`、`--report`；真实调用必须显式开启，报告独立落 `evals/llm_report.json`，默认兜底评测保持 10/10。

T-005 追加：真实 provider（Agnes AI）接入时，对 408 / 409 / 425 / 429 / 5xx 做有界指数退避；`MODEL_PRICE_INPUT` / `MODEL_PRICE_OUTPUT` 覆盖 token 单价；`LLM_CASE_DELAY_SEC` 控制 case 间隔，适配免费端点 RPM。退避只影响传输层，不改业务 prompt、golden 判定或报告语义。

## 理由

- 「无 key 也 10/10」是当前最大的误报来源，必须让开关和报告说清楚。
- 成本封顶让第一次真实回归可以从单 case 开始，几分钱验证连通性。
- 不把真实 LLM 设成默认 / CI 强制项，避免密钥进入 CI、费用失控与 flaky 阻塞。

**何时重评**：有稳定预算与专用测试 key 后，可把 `--require-llm` 接入夜间任务；provider 更换或价格表变化时重评成本闸门。

## 影响

- 代码 / 目录：`evals/run_eval.py`、`core/llm.py`、`core/config.py`、`core/llm_retry.py`、`docs/verify.md`、`.gitignore`；新增 `evals/llm_report.json`（gitignored）。
- 依赖 / 运维：无新增依赖；需要用户自行在 `.env` 配置 `OPENAI_API_KEY`，不得提交。
- 迁移 / 回滚：默认评测行为不变；回滚只需移除新参数与报告字段，`evals/report.json` 不受影响。
