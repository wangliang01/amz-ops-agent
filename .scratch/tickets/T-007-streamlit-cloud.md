# [T-007] Streamlit Community Cloud 免费部署

- **Status**: In Progress
- **Depends On**: T-005, T-006
- **对应 SPEC**: `SPEC.md` 的部署边界（不接真实店铺；演示数据）
- **预估轮数**: 2
- **预估 diff 行数**: < 260

## 要解决的问题

Render 免费 Web Service 在创建时仍要求绑定银行卡；Hugging Face 免费账号只能建 Static Space，Docker/Gradio Space 需要付费 PRO。项目的演示台是 Streamlit，后端是 FastAPI；Streamlit Community Cloud 可以免费托管 Streamlit，但不会同时启动 FastAPI。

## 范围

- 做：增加 `app/streamlit_cloud.py` 单进程入口；增加 `app/local_backend.py`，在 Streamlit 进程内复用现有 `build_services` / `build_graph` / SQLite，提供 skus / runs / approve / metrics；UI 在 `API_BASE_URL=local` 时走本地后端，远程 API 模式保持不变；README / 部署文档。
- 不做：新增依赖；改图 / 节点 / prompt / golden / 合规语义；引入鉴权；接真实 SP-API；写真实店铺；把 key 写进仓库。
- 边界：公开演示，合成数据，`executor` 仍只 dry-run，审批闸门仍为 `interrupt_before`。

## Stop conditions

- 需要读取或打印 `.env` / key
- 需要提交报告或凭据
- 需要改业务逻辑才能部署
- 同一处改 3 次不过

## 验收标准

- [x] AC-1：`app/streamlit_cloud.py` 设置 `API_BASE_URL=local`，从同一进程启动 UI，不要求外部 API 进程。
- [x] AC-2：`app/local_backend.py` 复用现有服务装配与 LangGraph，支持 SKU 列表、创建运行、查询运行、审批、聚合指标；审批后仍只产生 dry-run 审计。
- [x] AC-3：`app/streamlit_app.py` 在 local 模式不显示“API 不可达/启动 API”提示；远程 API 模式行为不变。
- [x] AC-4：无 LLM key 时规则兜底可运行；不新增依赖；不修改 `interrupt_before` 或真实店铺写接口。
- [x] AC-5：本地验证：local backend 完成一次 `awaiting_approval` → approve → `completed`，审计为 dry-run；现有 eval 10/10；UI 冒烟通过。
- [x] AC-6：README / `docs/deploy-streamlit-cloud.md` 给出 Streamlit Community Cloud 的入口文件、公开仓库、可选 secrets 和限制。
- [x] AC-7：仓库不包含 `.env`、key、token 或 Streamlit secrets；`git status` 无未预期的凭据文件。

## 完成记录

- 代码：
  - `app/streamlit_cloud.py`：单进程入口；bridges `st.secrets` 到环境变量；只读仓库时把 SQLite 放到临时目录。
  - `app/local_backend.py`：复用 `build_services` / `build_graph` / `SqliteSaver` / `core.db`；保留 `interrupt_before=["executor"]`。
  - `app/streamlit_app.py`：`API_BASE_URL=local` 时走本地后端；远程 API 模式保持原逻辑。
  - `scripts/verify_local_backend.py`：可重复的本地后端验收。
  - `scripts/verify_ui.py`：支持 local 模式和自定义 `UI_APP`。
- 证据（2026-11-24 实测）：
  - `scripts.verify_local_backend` → `LOCAL_BACKEND_OK skus=5 awaiting_approval=ok approve=5_dry_run audit=6`，退出 0。
  - `API_BASE_URL=local scripts.verify_ui` → `UI_VERIFY_OK tabs=6 awaiting_approval=ok approve=5_dry_run reject=1_skip errors=0`，退出 0。
  - `UI_APP=app/streamlit_cloud.py scripts.verify_ui` → 同上，退出 0（云端入口验证）。
  - `evals.run_eval`（`LLM_ENABLED=false`）→ 10/10 passed，`llm_calls=0`，退出 0。
  - `scripts.smoke_test` → 5 条 dry-run；`compileall` 退出 0。
- 部署状态：Streamlit Community Cloud 账号已通过 Google 登录；应用创建待 `main` 推送后执行。实际公网 URL 待回填。
- 未验证：Streamlit Cloud 实际构建/运行态；免费实例休眠与临时文件系统清空。

## 裁判记录

- 待独立裁判。

