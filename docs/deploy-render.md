# 部署到 Render

仓库根目录的 `render.yaml` 定义两个 Docker Web Service：

| Service | 作用 | 端口 | 健康检查 |
|---|---|---|---|
| `amz-ops-api` | FastAPI + LangGraph | `8000` | `/health` |
| `amz-ops-web` | Streamlit 演示台 | `8501` | `/_stcore/health` |

## 第一次部署

1. 把仓库推到 GitHub（当前 `main` 已包含 `render.yaml`）。
2. 点击 [Deploy to Render](https://render.com/deploy?repo=https://github.com/wangliang01/amz-ops-agent)，或在 Render Dashboard → **New → Blueprint** 选择本仓库。
3. Render 读取 `render.yaml`，创建两个服务；`OPENAI_API_KEY` 会提示输入。
   - 填 Agnes AI key：走 `agnes-3.0-flash` 真实 LLM。
   - 用其他 OpenAI 兼容 provider：同时改 `OPENAI_BASE_URL`、`CHAT_MODEL`、`CHEAP_MODEL` 和 `MODEL_PRICE_*`。
   - 留空：`LLM_ENABLED=true` 但 key 为空，自动走规则兜底。
4. 等待 API 健康检查通过，再等 Web 服务启动。
5. 打开 `amz-ops-web` 的 URL，例如 `https://amz-ops-web.onrender.com`。

`API_BASE_URL` 默认写死为 `https://amz-ops-api.onrender.com`。如果 Render 给你的 API 服务分配了别的名字，同步修改 `render.yaml` 里的这一项。

## GitHub Actions 触发部署

`render.yaml` 里两个服务都设置了 `autoDeployTrigger: off`，由 `.github/workflows/deploy-render.yml` 通过 Render Deploy Hook 触发，避免 Render 和 Actions 双重部署。

首次创建服务后：

1. Render Dashboard → 进入 `amz-ops-api` → **Settings → Deploy Hook**，复制 hook URL。
2. Render Dashboard → 进入 `amz-ops-web` → **Settings → Deploy Hook**，复制 hook URL。
3. 在 GitHub 仓库添加 Actions secrets（不要发到聊天或写进文件）：

```powershell
gh secret set RENDER_API_DEPLOY_HOOK
gh secret set RENDER_WEB_DEPLOY_HOOK
```

4. 手动触发一次，或下次推 `main` 自动触发：

```powershell
gh workflow run "Deploy to Render"
gh run watch
```

未配置 secrets 时工作流会给出 warning 并跳过部署，不会失败；配置后每次推 `main` 都会触发两个服务的重新部署。

## 免费实例的限制

- 两个服务都是 `free` plan，空闲后会休眠，首次访问需要冷启动。
- 没有持久盘：`data/runs.sqlite`、`data/checkpoints.sqlite` 在重启 / 重新部署后清空；`data/seed/` 来自仓库，不受影响。
- 需要保留审批与审计记录时：把 API 服务升级到付费实例，按 `render.yaml` 中注释加 `disk`，并把 `RUNS_DB_PATH` / `CHECKPOINT_DB_PATH` 指到挂载目录。

## 安全提醒

当前配置按“公开演示”使用：服务没有鉴权、限流或多租户隔离。项目只使用合成数据，`executor` 只做 dry-run，但仍建议：

- 只是展示界面时，把 API 的 `LLM_ENABLED` 设为 `false`，或不要在 Render 填 `OPENAI_API_KEY`；
- 需要真实 LLM 时，在 Render 前面加访问控制（反向代理 / Basic Auth / Cloudflare Access）；
- 不要把 `.env` 或 key 提交到仓库；key 只放 Render 环境变量。

如果你不想公开暴露，请不要直接使用本 Blueprint，先加访问控制再部署。

## 本地校验

```powershell
# YAML 语法
.\.venv\Scripts\python.exe -c "import yaml, pathlib; d=yaml.safe_load(pathlib.Path('render.yaml').read_text(encoding='utf-8')); print([s['name'] for s in d['services']])"
# 期望：['amz-ops-api', 'amz-ops-web']
```
