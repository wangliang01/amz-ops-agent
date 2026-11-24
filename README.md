# amz-ops-agent

> Multi-Agent Operations Copilot for Amazon Sellers — LangGraph · RAG · FastAPI

一个面向亚马逊运营的 Multi-Agent Demo：把「评论洞察 → Listing 生成 → 合规审查 → 广告诊断 → 人工审批 → dry-run 执行」串成一条可演示、可回测、可量化的业务链路。

> 商品与评论来自公开研究数据集 Amazon Reviews 2023（All Beauty），品牌名已匿名化；广告、库存、成本、转化率为模拟数据。接口形状模仿 SP-API / Ads API，便于后续替换。合规规则为演示摘要，不构成法律建议。本项目与 Amazon 无关联。

---

## 这个 Demo 证明了什么

| JD 信号 | Demo 证据 |
|---|---|
| 流程自动化 | 一条命令/一个 API 跑完整链路；节点级耗时、token、成本、审计日志 |
| AIGC 内容生产 | Listing 标题/五点/描述/关键词生成 + 21 条规则审查 + 人工抽检入口 |
| 数据链路 | 真实 Amazon 公开评论与商品元数据（品牌匿名）+ 模拟 90 天广告数据；建议可回测 |
| Multi-Agent 编排 | LangGraph 状态图、Supervisor 路由、HITL 断点、失败降级 |
| RAG | Chroma/BM25 混合检索、RRF、metadata 过滤、引用、10 条 golden case |
| 选品机会 | 5 个真实 SKU 的加权机会分：需求、评分、痛点密度、竞争密度、毛利空间 + 评论证据 |
| 库存 / 预算 / 定价 | 可售天数、补货点与补货量、日预算调整、毛利底价护栏（模拟假设逐项标注） |
| 量化 / ROI | 合规通过率、修复数、ACOS 变化、预计花费变化、单次成本、人工分钟节省与净收益 |

---

## 快速开始

```powershell
# 1. 创建环境（Python 3.11）
uv venv .venv --python 3.11
uv pip install --python .venv\Scripts\python.exe -r requirements.txt

# 2. 种子数据已随仓库提供；如需从公开数据集重建（约 540MB 下载）
.\.venv\Scripts\python.exe data\fetch_real_seed.py

# 3. 配置 LLM（可选）
Copy-Item .env.example .env
# 编辑 .env，填入 OPENAI_API_KEY / OPENAI_BASE_URL / CHAT_MODEL

# 4. CLI 跑通（无 key 时自动走规则兜底）
.\.venv\Scripts\python.exe -m scripts.run_demo --sku SKU-003 --approve

# 5. 启动 API 和演示台
.\.venv\Scripts\python.exe -m uvicorn api.main:app --reload
.\.venv\Scripts\python.exe -m streamlit run app\streamlit_app.py
```

- API 文档：<http://127.0.0.1:8000/docs>
- 演示台：<http://127.0.0.1:8501>
- 也可以直接运行 `.\run.ps1` 同时启动两个进程。

### Docker（可选）

```powershell
Copy-Item .env.example .env
docker compose up --build
```

> 本机 Docker daemon 未启动，镜像构建未验证；`docker compose config` 已通过。

### Streamlit Community Cloud（推荐，免费）

在线 Demo：<https://amz-ops-agent-g9pckbqru2xenyystgiaas.streamlit.app/>

无需绑卡、无需单独启动 FastAPI：

- 入口文件：`app/streamlit_cloud.py`
- 单进程后端：`app/local_backend.py`（复用现有 LangGraph、审批闸门和 SQLite）
- 部署步骤与可选 LLM secrets 见 [`docs/deploy-streamlit-cloud.md`](docs/deploy-streamlit-cloud.md)

在 <https://share.streamlit.io/> 创建 app，仓库选 `wangliang01/amz-ops-agent`，分支 `main`，主文件路径填 `app/streamlit_cloud.py`。不填 key 时走规则兜底；填 key 才调用真实 LLM。

### Render（备选）

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/wangliang01/amz-ops-agent)

仓库根目录提供 `render.yaml`，可在 Render 一次创建两个 **Python Web Service**（原生运行时，不依赖 Docker 免费额度）：

- `amz-ops-api`：FastAPI / LangGraph，健康检查 `/health`
- `amz-ops-web`：Streamlit 演示台，健康检查 `/_stcore/health`

点击上方按钮，在 Render Dashboard 授权仓库即可创建。之后由 GitHub Actions（`.github/workflows/deploy-render.yml`）通过 Render Deploy Hook 触发部署；`OPENAI_API_KEY` 只在 Render 环境变量中填写，不要提交到仓库；留空时走规则兜底。免费实例会休眠且 SQLite 不持久，公开部署的鉴权与配额风险见 [`docs/deploy-render.md`](docs/deploy-render.md)。

---

## LLM 配置

任何 OpenAI 兼容接口都可以。示例（以各厂商文档为准）：

| 厂商 | `OPENAI_BASE_URL` | `CHAT_MODEL` |
|---|---|---|
| OpenAI | `https://api.openai.com/v1` | `gpt-4o-mini` |
| DeepSeek | `https://api.deepseek.com/v1` | `deepseek-chat` |
| Qwen | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-plus` |
| Kimi | `https://api.moonshot.cn/v1` | `moonshot-v1-8k` |
| GLM | `https://open.bigmodel.cn/api/paas/v4` | `glm-4-flash` |

没有 LLM key 时：

- `LLM_ENABLED=false` 或 `OPENAI_API_KEY` 为空，所有 Agent 自动走规则/模板兜底，链路仍然完整。
- 如果厂商没有 embeddings 接口，设置 `EMBEDDING_ENABLED=false`，检索退化为 BM25 + RRF。
- 有 embeddings 时，Chroma 会建立持久化索引，检索走 BM25 + dense 混合。

---

## 架构

```
Streamlit 单页 ──HTTP──> FastAPI ──> LangGraph
                                      │
        ┌─────────────┬───────────────┼──────────────┐
        ▼             ▼               ▼              ▼
     Insight       Listing        Compliance        Ads
        └─────────────┴───────┬───────┴──────────────┘
                              ▼
                        Approval Gate (interrupt)
                              ▼
                          Executor (dry-run + 审计)
                              ▼
                     SQLite: runs / audit / metrics
```

分层：

- **数据层**：`core/store.py` 读取真实公开评论（品牌匿名）+ 模拟广告；`rag/ingest.py` 构建检索语料。
- **检索层**：`rag/retriever.py`，BM25 + Chroma dense + RRF + metadata 过滤。
- **编排层**：`agent/graph.py`，LangGraph `StateGraph` + `MemorySaver` + `interrupt_before`。
- **执行层**：`agent/nodes/executor.py`，只做 dry-run，写审计日志。
- **接口层**：`api/main.py`，FastAPI；`app/streamlit_app.py`，演示台。
- **评测层**：`evals/run_eval.py`，10 条 golden case。

---

## Agent 流程

| 节点 | 职责 | 兜底策略 |
|---|---|---|
| Supervisor | 校验 SKU、选择模式；`auto` 时用 LLM 路由 | 默认 `full_chain` |
| Insight | 评论痛点聚类、正负主题、竞品差距、原文引用 | 关键词规则 |
| Listing | 检索历史高转化 Listing + 政策，生成标题/五点/描述/关键词 | 模板 + 关键词库 |
| Compliance | 21 条规则 + LLM 复核；同时检查当前 Listing 和新草稿 | 仅规则检查 |
| Ads | 90 天趋势、异常检测、关键词出价建议、30 天回测 | 规则降价/加价 |
| Ops | 可售天数、补货点/补货量、日预算调整、价格护栏、ROI | 固定公式 + 显式模拟假设 |
| Executor | HITL 审批后 dry-run，写审计日志和指标 | 拒绝/未审批时跳过 |

模式：

- `full_chain`：Insight → Listing → Compliance → Ads → Ops → Approval → Executor
- `listing_only`：Insight → Listing → Compliance → Approval → Executor
- `ads_only`：Ads → Ops → Approval → Executor
- `auto`：由 Supervisor 选择

---

## RAG 设计

- **语料**：20 条历史 Listing、5 份政策文档（按 `##` 切分）、21 条合规规则。
- **混合检索**：BM25 top-20 + dense top-20，RRF 融合，metadata 过滤（如 `subcategory`）。
- **引用**：Listing 和合规报告都返回 `doc_id`；演示台可展开查看证据。
- **降级**：没有 embeddings 时只用 BM25；没有 LLM 时用模板。
- **评测**：`evals/golden.jsonl` 覆盖 5 个 SKU，检查标题长度、五点数量、必备词、违禁词、引用、合规结果。

后续可加：cross-encoder 重排（`bge-reranker`）、query rewrite、按站点/语言过滤。

---

## 合规与 HITL

- 规则分 `block` / `warn`：`block` 会阻止通过，`warn` 只扣分。
- 当前 Listing 和生成草稿分别检查，报告里给出 `fixed_count`。
- 图在 `executor` 前中断：API 返回 `awaiting_approval`。
- 审批后 `graph.update_state` + `graph.invoke(None, config)` 恢复。
- 所有动作只做 dry-run，写入 SQLite `audit` 表；不接真实店铺写接口。

---

## 广告诊断与回测

- 指标：spend、sales、ACOS、CTR、CVR、orders。
- 异常：ACOS 超目标、花费上涨但销售不涨、CTR 低、CVR 低。
- 建议：按关键词降价/加价，限制在 `-25% ~ +10%`。
- 回测假设：点击对出价的弹性 0.6，CPC 弹性 0.5，CVR/AOV 不变。
- 明确区分：**回测是估算，不是线上实测**。

---

## 评测

```powershell
.\.venv\Scripts\python.exe -m evals.run_eval
```

当前无 LLM 兜底路径：10/10 通过。接入 LLM 后结果会变化，建议把评测作为回归闸门，而不是追求固定分数。

输出：`evals/report.json`。

## 指标口径

- `pipeline_sec`：各节点耗时之和，代表 AI 处理时间。
- `wall_clock_sec`：从 run 创建到执行结束，包含人工审批等待。
- `approval_wait_sec`：人工审批等待时间。
- `cost_usd`：按模型价格表估算，不是账单金额。
- `compliance_pass_rate`：没有 `block` 级问题的运行占比。
- 广告回测：基于弹性假设的估算，不是线上实测。
- 机会分：需求 / 评分 / 痛点密度 / 竞争密度 / 毛利空间的固定权重加权分（30/20/25/15/10），不是销量预测。
- 补货 / 预算 / 定价：库存、日销、提前期、安全库存、成本、广告预算均为模拟；输出里逐项标注。
- ROI：人工分钟节省按节点固定估算，时薪与 ACOS 变化都是假设，不是工时或线上实测。

## 验证状态

本机已验证：

- CLI：`scripts/run_demo.py` 全链路通过，审批后 5 条 dry-run 动作。
- API：`/runs` → `awaiting_approval` → `/approve` → `completed`。
- UI：Streamlit 页面渲染、运行、审批、审计、指标均通过；选品排名与 ROI 面板已浏览器实测。
- 运营计划：`scripts/verify_ops` 通过（5 个 SKU 确定性排名、补货/预算/定价字段、5 条 dry-run）。
- 评测：无 LLM 兜底 10/10；真实 LLM `--require-llm` 9/10（`G-003` 草稿未包含精确短语 `nail art drill`，其余 9 条通过；未为过测放宽 golden）。
- 数据：5 个真实商品 + 250 条真实评论 + 20 条真实历史 Listing；广告/库存/成本为模拟。
- 部署：Streamlit Community Cloud 在线 Demo 已跑通审批与 dry-run。
- Docker：`docker compose config` 校验通过；镜像构建未执行（本机 Docker daemon 未启动）。

未验证：真实 SP-API / Ads API 接入；多站点/多店铺；图像/视频素材生成。

---

## 目录结构

```
amz-ops-agent/
├── agent/
│   ├── graph.py              # LangGraph 状态图
│   ├── state.py              # AgentState
│   ├── services.py           # LLM / Store / Retriever 装配
│   ├── opportunity.py        # 选品机会排名（确定性加权分 + 评论证据）
│   ├── ops_plan.py           # 补货 / 预算 / 定价 / ROI（模拟假设）
│   └── nodes/                # supervisor / insight / listing / compliance / ads / ops / executor
├── api/main.py               # FastAPI
├── app/streamlit_app.py      # 演示台
├── core/
│   ├── config.py             # 环境变量
│   ├── llm.py                # OpenAI 兼容客户端 + JSON 解析 + 兜底
│   ├── db.py                 # SQLite runs / audit / metrics
│   └── store.py              # 种子数据访问（真实评论 + 模拟广告）
├── rag/
│   ├── ingest.py             # 语料构建
│   └── retriever.py          # BM25 + Chroma + RRF
├── data/
│   ├── fetch_real_seed.py    # 从公开数据集重建种子（固定快照 + sha256）
│   ├── generate_seed.py      # 合成数据兜底（默认拒绝覆盖真实种子）
│   └── seed/                 # SKU / 评论 / Listing / 广告 / 规则 / 政策 / PROVENANCE
├── evals/                    # golden set + 评测脚本
├── scripts/                  # CLI demo + smoke test + verify_ops / verify_ui
├── requirements.txt
├── run.ps1
└── .env.example
```

---

## API

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/health` | 健康检查、LLM/向量索引状态 |
| `GET` | `/skus` | 可选 SKU 列表 |
| `GET` | `/opportunities` | 选品机会排名（加权分、驱动因素、评论证据） |
| `POST` | `/runs` | 创建并运行，返回 `awaiting_approval` 或 `completed` |
| `GET` | `/runs/{id}` | 查询运行状态和状态快照 |
| `POST` | `/runs/{id}/approve` | `approved` / `rejected`，恢复图执行 |
| `GET` | `/runs` | 最近运行列表 |
| `GET` | `/metrics` | 聚合指标 |

示例：

```powershell
$run = Invoke-RestMethod http://127.0.0.1:8000/runs -Method Post `
  -ContentType 'application/json' `
  -Body '{"sku_id":"SKU-003","mode":"full_chain"}'

Invoke-RestMethod "http://127.0.0.1:8000/runs/$($run.run_id)/approve" -Method Post `
  -ContentType 'application/json' `
  -Body '{"decision":"approved","actor":"operator"}'
```

---

## 数据说明

- **真实数据**：5 个主 SKU 的商品标题、五点、描述、价格、评分、评论数和评论正文，来自 Amazon Reviews 2023（All Beauty）固定快照；20 条历史 Listing 同样来自该数据集的真实商品。品牌名替换为 Brand A–E，评论去除了用户 ID、图片和点赞数。
- **模拟数据**：90 天广告日报、关键词出价、库存、成本、目标 ACOS、关键词搜索量、历史 Listing 转化率。公开渠道没有卖家私有的广告与库存数据。
- 数据重建：`data/fetch_real_seed.py`，固定 URL + sha256 校验；来源、许可、匿名化与模拟字段见 [`data/seed/PROVENANCE.md`](data/seed/PROVENANCE.md)。
- 接口形状模仿 SP-API / Ads API；`core/store.py` 是 mock 层，替换为真实客户端时保持节点接口不变。
- 合规规则是演示用摘要，不是 Amazon 官方政策全文，也不构成法律建议。

---

## 设计取舍

- **Workflow 优先，Agent 只做判断类任务**：数据清洗、规则命中用确定性代码；文案、诊断、建议才交给 LLM。
- **规则 + LLM 双通道**：规则保证下限，LLM 补充语义判断；任何一路失败都不会让链路中断。
- **HITL + dry-run**：不接真实写接口，审批后只写审计日志；演示安全，也符合企业落地方式。
- **可量化优先**：每次运行都记录耗时、token、成本、合规结果；广告建议带回测。
- **2 天 MVP 边界**：真实 SP-API/Ads API、图片/视频生成、MCP/A2A、完整评测集不在关键路径；Docker 配置已提供，但未做镜像构建验证。

---

## 5 分钟演示脚本

1. 选 `SKU-003`：真实颈膜商品，3.4 星、2945 条评论，评论集中在效果不足、粘不住、扯皮肤。
2. 点 **运行流水线**，四个 Agent 依次跑完。
3. **Insight**：痛点来自真实评论原文与引用。
4. **Listing**：新标题/五点，引用真实历史高转化 Listing。
5. **Compliance**：当前 Listing 的真实宣称（medical grade、Made in USA、Guarantee）被规则命中，新草稿通过。
6. **Ads**：ACOS 偏高、花费上涨、5 条降价建议、30 天回测（广告为模拟数据）。
7. **选品**：5 个 SKU 的机会排名、驱动因素与真实评论证据；下方是补货、日预算、价格护栏。
8. 侧边栏 **Approve**：执行器写 dry-run 审计日志。
9. **Metrics**：耗时、token、成本、合规通过率、ROI（人工分钟节省、净收益）。

---

## License / Disclaimer

Demo only. Product metadata and review text come from the public Amazon Reviews 2023 research dataset (brand names anonymized). Ads, inventory, cost and conversion data are simulated. Not affiliated with Amazon.com, Inc. "Amazon" is a trademark of Amazon.com, Inc. or its affiliates.
