# 部署到 Streamlit Community Cloud

Streamlit Community Cloud 免费、公开、无需绑定银行卡。它只运行 Streamlit 进程，不会同时启动 FastAPI；因此仓库提供单进程入口：

| 文件 | 作用 |
|---|---|
| `app/streamlit_cloud.py` | Streamlit Cloud 入口；设置 `API_BASE_URL=local`，在进程内启动演示台 |
| `app/local_backend.py` | 复用现有 `build_services` / `build_graph` / SQLite，提供 SKU、运行、审批、指标 |
| `app/streamlit_app.py` | 原有 UI；local 模式不显示 API 连接错误，远程 API 模式保持不变 |

审批闸门仍是 LangGraph 的 `interrupt_before=["executor"]`；批准后执行器只写 dry-run 审计，不接真实店铺写接口。

## 在线实例

- 公开地址：<https://amz-ops-agent-g9pckbqru2xenyystgiaas.streamlit.app/>
- 构建日志（2026-11-24）：`Starting up repository: 'amz-ops-agent', branch: 'main', main module: 'app/streamlit_cloud.py'`；运行时 `LLM disabled`、`Embeddings disabled`。
- 浏览器实测：运行流水线 → `等待审批`；批准 → `已完成`；审计 5 条 `dry-run 成功`；指标模型调用 0。
- 2026-11-24 更新：线上已有「选品」tab、补货/预算/定价与 ROI；批准后仍为 5 条 dry-run。
- **模块缓存**：push 新增或重命名 Python 模块后，线上可能只做热重载并保留旧模块缓存（表现为新页面引用旧类）。到 <https://share.streamlit.io/> 的 app 菜单点 **Reboot**，再在确认框点一次 **Reboot**；重启后才会加载完整新版本。

## 第一次部署

1. 把 `main` 推到 GitHub（仓库公开即可）：
   <https://github.com/wangliang01/amz-ops-agent>
2. 打开 <https://share.streamlit.io/>，用 GitHub 或 Google 登录。
3. 点 **Create app** → **Deploy a public app from GitHub**。
4. 填写：
   - Repository：`wangliang01/amz-ops-agent`
   - Branch：`main`
   - Main file path：`app/streamlit_cloud.py`
   - App URL：可自定义，例如 `amz-ops-agent`
5. 点 **Deploy**。首次构建会安装 `requirements.txt`，通常需要几分钟。

部署成功后，Streamlit Cloud 会给出 `https://<app-url>.streamlit.app` 的公开地址。

## 可选：启用真实 LLM

默认不填 key 时走规则兜底，演示链路完整，`llm_calls=0`。需要真实模型时，在 Streamlit Cloud 的 **App settings → Secrets** 里填写（不要提交到仓库）：

```toml
OPENAI_API_KEY = "你的 key"
OPENAI_BASE_URL = "https://apihub.agnes-ai.com/v1"
CHAT_MODEL = "agnes-3.0-flash"
CHEAP_MODEL = "agnes-3.0-flash"
MODEL_PRICE_INPUT = "0.05"
MODEL_PRICE_OUTPUT = "0.15"
```

`app/streamlit_cloud.py` 会把这些 secrets 转成环境变量，再初始化 `core.config`。其他 OpenAI 兼容 provider 同理，改 `OPENAI_BASE_URL` / `CHAT_MODEL` / `CHEAP_MODEL` / `MODEL_PRICE_*`。

不要把 `.env`、key、token 或 `secrets.toml` 提交到 GitHub。

## 免费实例的限制

- App 空闲后会休眠，首次访问需要冷启动。
- 文件系统是临时的：`data/runs.sqlite`、`data/checkpoints.sqlite` 在重启 / 重新部署后清空；`data/seed/` 来自仓库，不受影响。
- 演示台没有鉴权、限流或多租户隔离；评论与商品为公开数据样本（品牌匿名），广告为模拟，`executor` 只做 dry-run。
- 如果需要保留审批与审计记录，后续应把 SQLite 换成托管数据库，并加访问控制。

## 本地验证

```powershell
# 单进程后端：awaiting_approval -> approve -> completed，5 条 dry-run
$env:LLM_ENABLED='false'; $env:EMBEDDING_ENABLED='false'
.\.venv\Scripts\python.exe -m scripts.verify_local_backend

# UI local 模式
$env:API_BASE_URL='local'
.\.venv\Scripts\python.exe -m scripts.verify_ui

# 评测 / 冒烟
.\.venv\Scripts\python.exe -m evals.run_eval
.\.venv\Scripts\python.exe -m scripts.smoke_test
```

期望：`LOCAL_BACKEND_OK`、`UI_VERIFY_OK`、`10/10 passed`、5 条 dry-run。
