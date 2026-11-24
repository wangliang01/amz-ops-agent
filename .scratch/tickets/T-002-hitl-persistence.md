# [T-002] HITL 待审批状态跨 API 重启持久化

- **Status**: Done
- **Depends On**: 无
- **对应 SPEC**: `SPEC-002-hitl-persistence.md` AC-1..AC-8
- **预估轮数**: 8
- **预估 diff 行数**: < 220
- **Target Files**:
  - `agent/graph.py`
  - `api/main.py`
  - `core/config.py`
  - `requirements.txt`
  - `scripts/verify_hitl_restart.py`
  - `docs/verify.md`

## 要解决的问题

`agent/graph.py` 用 `MemorySaver()` 保存 checkpoint。run 停在 `interrupt_before=["executor"]` 时状态只在 API 进程内；API 重启后 `GET /runs/{id}` 只能回退 `runs` 表的 JSON（`next` 丢失），`POST /approve` 返回 404。HITL 闸门因此不可靠。

## 范围

- 做：官方 `SqliteSaver` + `data/checkpoints.sqlite`；`build_graph` 支持注入；API lifespan 持有连接；`Settings` 支持 `CHECKPOINT_DB_PATH` / `RUNS_DB_PATH` 覆盖以便隔离测试；新增重启回归脚本；更新 `docs/verify.md`。
- 不做：HTTP 响应结构、UI、多 worker、checkpoint GC、旧 run 迁移、审批语义、真实 Amazon API。

## Stop conditions（遇到就停，不要硬做）

- 需要新增依赖 / 改数据模型 / 改外部接口
- 需要动 Target Files 之外的文件，或 diff 预计 > 200 行
- 同一处改 3 次不过
- AC 与 SPEC 冲突，或 AC 无法验证

## 验收标准（必须可执行）

- [x] AC-1：创建 run → `awaiting_approval`；停/起 API；`GET /runs/{id}` → `status: "awaiting_approval"`、`next: ["executor"]`，`sku_id` / `mode` / `draft_listing.title` / `ads_report.last_30d.acos` 与重启前一致。
- [x] AC-2：接 AC-1，`POST /approve {"decision":"approved"}` → `completed`；`execution_log` 5 条且全为 `dry_run_success`；`audit` 有 1 条 `approval_decision` + 5 条 `execute_dry_run`；`runs` 表该 run 为 `completed`。
- [x] AC-3：新建 run → 停/起 API → `POST /approve {"decision":"rejected"}` → `completed`；`execution_log` 只有 1 条 `action: "skip"` / `status: "rejected"`，没有 `dry_run_success`；`audit` 有 `approval_decision` 与 `execute_skipped`，没有 `execute_dry_run`。
- [x] AC-4：AC-2 完成后停/起 API，再 `POST /approve` → 仍 `completed`；`execution_log` 仍 5 条；`audit` 中 `approval_decision` 与 `execute_dry_run` 计数不变（1 / 5）。
- [x] AC-5：`data/checkpoints.sqlite` 被创建；`git status` 不出现；`.gitignore` 的 `*.sqlite` + `*.sqlite-*` 覆盖主文件与 `-wal` / `-shm`。
- [x] AC-6：`-m evals.run_eval` → 10/10；`-m scripts.smoke_test` → 5 条 dry-run；`AppTest` → 6 tabs、run→awaiting_approval、approve→completed；`-m scripts.run_demo --sku SKU-003 --approve` 可跑。
- [x] AC-7：`uv pip install --python .venv\Scripts\python.exe -r requirements.txt` 成功；`from langgraph.checkpoint.sqlite import SqliteSaver` 无报错；`langgraph>=1.2.24,<2`、`langgraph-checkpoint-sqlite==3.1.3`。
- [x] AC-8：`/health`、`/skus`、`/runs`、`/runs/{id}`、`/approve`、`/metrics` 响应键不变。

## 验证方式

```powershell
# 1. 依赖
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
.\.venv\Scripts\python.exe -c "from langgraph.checkpoint.sqlite import SqliteSaver; print('OK')"

# 2. 重启回归（脚本内部用临时 runs / checkpoint 库，起停 API 三次）
.\.venv\Scripts\python.exe scripts\verify_hitl_restart.py
# 期望：HITL_RESTART_OK <run_id>

# 3. 原有回归
.\.venv\Scripts\python.exe -m evals.run_eval
.\.venv\Scripts\python.exe -m scripts.smoke_test
```

## 完成记录

- 提交：待提交
- 证据（输出 / 截图 / 响应）：
  - 重启脚本：`HITL_RESTART_OK run-58e788c6 run-ac9280bf`；`checkpoints` 表存在，`checkpoint_db.stat().st_size > 0`。
  - 回归：`evals.run_eval` → `10/10 passed`；`scripts.smoke_test` → `execution_actions: 5`；AppTest → 6 tabs、`completed`、5 条动作；CLI → `Saved run ... (status=completed)`。
  - 依赖：`uv pip install` 新增 `aiosqlite 0.22.1`、`langgraph-checkpoint-sqlite 3.1.3`、`sqlite-vec 0.1.9`；`SqliteSaver` import OK。
  - 文件：`data/checkpoints.sqlite` 及 `-wal` / `-shm` 均被 `git check-ignore` 命中。

## 裁判记录

| AC | 判定（达成 / 未达成 / 无法验证） | 证据 |
|---|---|---|
| AC-1 | 达成 | `scripts/verify_hitl_restart.py:136-147` 断言 status / next / sku_id / mode / draft title / acos；实跑 `HITL_RESTART_OK` |
| AC-2 | 达成 | 同脚本 `:154-160` 断言 completed、5 条 `dry_run_success`、audit 1 + 5、`run_status == completed`；脚本通过 |
| AC-3 | 达成 | 同脚本 `:180-188`：rejected → completed，log 仅 1 条 `skip/rejected`，audit `execute_skipped=1`、`execute_dry_run=0` |
| AC-4 | 达成 | 同脚本 `:165-173`：二次重启后再 approve，仍 completed、log 5、audit 1/5 |
| AC-5 | 达成 | `data/checkpoints.sqlite` 含 `checkpoints` / `writes` 表；`git check-ignore` 命中 `*.sqlite` 与 `*.sqlite-*`；`git status` 无 sqlite |
| AC-6 | 达成 | eval 10/10；smoke `execution_actions: 5`；AppTest 6 tabs / awaiting_approval / completed 5；CLI `status=completed` |
| AC-7 | 达成 | `langgraph 1.2.24`、`langgraph-checkpoint 4.3.2`、`langgraph-checkpoint-sqlite 3.1.3`；`SqliteSaver` import OK；`uv pip install --dry-run` 无变化 |
| AC-8 | 达成 | `api/main.py` 仅 lifespan hunk；`/health`、`/skus`、`/runs`、`/runs/{id}`、`/approve`、`/metrics` 键实测不变 |
