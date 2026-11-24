# [T-006] Render 部署配置

- **Status**: Done
- **Depends On**: T-005
- **对应 SPEC**: `SPEC.md` 的部署边界（不接真实店铺；演示数据）
- **预估轮数**: 2
- **预估 diff 行数**: < 120

## 要解决的问题

仓库已有 `Dockerfile` / `docker-compose.yml`，但没有可直接导入 Render 的 Blueprint。补一份 `render.yaml`，让 API 与 Streamlit 两个服务可以一键创建，密钥只通过 Render 环境变量注入。

## 范围

- 做：Render Blueprint（API + Web）；健康检查、端口、环境变量、`OPENAI_API_KEY sync: false`；GitHub Actions 通过 Render Deploy Hook 触发部署；免费实例与持久盘限制说明；README / `docs/deploy-render.md` 回填。
- 不做：新增依赖；改业务代码 / 图 / UI；把 key 写入仓库；接真实 SP-API；增加鉴权或反向代理。
- 边界：用户明确要求公开体验；本配置只面向演示，仍无鉴权/限流，`executor` 只做 dry-run。

## Stop conditions

- 需要读取或打印 `.env` / key
- 需要提交报告或凭据
- 需要改业务代码才能部署
- 同一处改 3 次不过

## 验收标准

- [ ] AC-1：`render.yaml` 定义 `amz-ops-api` 与 `amz-ops-web` 两个 Render Python Web Service；API 健康检查 `/health`，Web 健康检查 `/_stcore/health`。
- [ ] AC-2：两个服务均用 Render `$PORT` 启动；API `uvicorn api.main:app`，Web `streamlit run app/streamlit_app.py`；`API_BASE_URL` 指向 API 服务 URL。Render 不使用 Docker（本地 Dockerfile 保留）。
- [ ] AC-3：`OPENAI_API_KEY` 使用 `sync: false`，`render.yaml` / 工作流 / 文档不含任何真实 key / `.env` 内容。
- [ ] AC-4：文档说明免费实例会休眠、SQLite 不持久，以及公开部署的鉴权 / 配额风险；记录用户明确要求公开体验的边界。
- [ ] AC-5：YAML 可被 `yaml.safe_load` 解析，服务名与设置符合预期；现有测试与编译不受影响。
- [ ] AC-6：`.github/workflows/deploy-render.yml` 在 `push main` / 手动触发时调用两个 Render Deploy Hook；secrets 缺失时 warning 跳过，不打印 hook URL。
- [ ] AC-7：`render.yaml` 设置 `autoDeployTrigger: off`，避免 Render 与 Actions 双重部署。
- [ ] AC-8：README / `docs/deploy-render.md` 给出 Blueprint 一键入口、Deploy Hook 与 GitHub secrets 配置步骤。

## 完成记录

- 提交：`49fbc32`
- 证据（2026-11-24 实测）：
  - `yaml.safe_load`：服务 `['amz-ops-api','amz-ops-web']`；`runtime=python`、`plan=free`、`autoDeployTrigger="off"`；API `/health`、Web `/_stcore/health`。
  - 启动：两个服务均绑定 Render `$PORT`；API `uvicorn api.main:app`，Web `streamlit run app/streamlit_app.py`。
  - `OPENAI_API_KEY` 为 `sync: false`；对 render / workflow / docs / README / ticket 扫描未发现 key 或 `srv-` hook。
  - 35 个 `.py` 语法 `ast.parse` 通过；本次 diff 无业务代码。
  - `.dockerignore` 补 `.env.*`、`.scratch/`、`evals/llm_report.json`。
- 运行态待验证（非配置阻塞）：Render Blueprint 首次创建、免费实例内存、实际 Actions 触发（需 Render 服务与 secrets）。
- Render 现场发现：Docker 运行时在免费计划下触发付款信息弹窗；已改为原生 Python runtime。

## 裁判记录

| AC | 判定 | 证据 |
|---|---|---|
| AC-1 | 达成 | `yaml.safe_load`：两个 `web/python/free`；健康检查 `/health`、`/_stcore/health` |
| AC-2 | 达成 | 两个服务均用 Render `$PORT`；API `uvicorn api.main:app`，Web `streamlit run app/streamlit_app.py`；`API_BASE_URL` 指向 API |
| AC-3 | 达成 | `OPENAI_API_KEY` `sync: false`；密钥/`srv-` hook 扫描无命中；`.env` 未跟踪 |
| AC-4 | 达成 | `docs/deploy-render.md` 写明休眠、SQLite 不持久、无鉴权/配额风险；SPEC 风险 5 已记录用户批准的公开演示例外 |
| AC-5 | 达成 | YAML 解析成功；35 个 `.py` 语法通过；无 `.py` 改动 |
| AC-6 | 达成 | workflow 静态审查：push main / workflow_dispatch；两个 hook；缺失时 warning 跳过；不打印 hook |
| AC-7 | 达成 | 两个服务 `autoDeployTrigger: "off"`，避免与 Actions 双部署 |
| AC-8 | 达成 | README Deploy to Render 按钮；docs 含 Deploy Hook 与 `gh secret set` 步骤 |

- 初次裁判：AC-1..AC-5 达成；提出公开无鉴权与 SPEC 风险 5 冲突、`.env.*` 未忽略、provider 耦合等。
- 复判：AC-1..AC-8 全部达成，建议提交/推送；SPEC 例外已同步。
- 运行态未验证：Docker 构建、Render free 内存、实际 Actions 触发（需外部账号与 secrets）。
