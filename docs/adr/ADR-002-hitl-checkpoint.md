# ADR-002 用官方 SqliteSaver 持久化 HITL 检查点

- **日期**: 2026-11-24
- **状态**: proposed（随 SPEC-002 一起等待批准）
- **关联**: `SPEC-002-hitl-persistence.md`

## 背景

当前 `agent/graph.py` 用 `MemorySaver()` 保存 LangGraph checkpoint。run 停在 `interrupt_before=["executor"]` 时，状态只在 API 进程内；进程重启后 `GET /runs/{id}` 只能回退 `runs` 表的 JSON，`POST /approve` 因拿不到 checkpoint 返回 404。演示时重启 API 就丢掉待审批任务，HITL 闸门不可靠。

## 备选方案

| 方案 | 优点 | 代价 | 结论 |
|---|---|---|---|
| A 官方 `SqliteSaver` | 官方维护、schema 与 LangGraph 同步、改动小 | 新增 `langgraph-checkpoint-sqlite` 及传递依赖 | **采用** |
| B 自写 `BaseCheckpointSaver` | 不新增依赖 | 追内部 schema / writes / 版本迁移，风险高 | 拒绝 |
| C 从 `runs.state_json` 用 `update_state` 重建 | 不新增依赖 | 依赖 `as_node` 与 interrupt 隐含语义，可能跳过/重复 executor | 拒绝 |
| D Postgres / Redis | 多 worker | demo 过重，增加运维与密钥 | 拒绝 |

## 决定

使用 `langgraph-checkpoint-sqlite==3.1.3` 的 `SqliteSaver`，checkpoint 存独立文件 `data/checkpoints.sqlite`；`build_graph` 接受注入，API lifespan 持有连接，CLI / 测试默认继续 `MemorySaver`。

## 理由

- HITL 的核心是「审批闸门可靠」，不能用脆弱的状态重建去模拟。
- 官方 saver 负责 checkpoint schema、序列化与版本兼容；业务代码只改装配点。
- 独立库避免 LangGraph 表与 `runs` / `audit` 混用，降低锁竞争与迁移风险。
- 单文件 SQLite 与当前 demo 的零运维定位一致。

**何时重评**：需要多 worker / 多机、checkpoint 量级增长到需要 GC、或 LangGraph 升级导致 saver 不兼容时。

## 影响

- 代码 / 目录：`agent/graph.py`、`api/main.py`、`core/config.py`、`requirements.txt`；新增 `data/checkpoints.sqlite`（gitignored）。
- 依赖 / 运维：新增 `langgraph-checkpoint-sqlite==3.1.3`，传递 `aiosqlite`、`sqlite-vec`；`langgraph` 收紧到 `>=1.2.24,<2`。
- 迁移 / 回滚：旧内存 run 不迁移；回滚只需恢复 `MemorySaver` 装配并移除依赖，`runs.sqlite` 不受影响。
