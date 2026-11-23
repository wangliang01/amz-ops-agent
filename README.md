# amz-ops-agent

> Multi-Agent Operations Copilot for Amazon Sellers — LangGraph · RAG · FastAPI

一个面向亚马逊运营的 Multi-Agent Demo：把「评论洞察 → Listing 生成 → 合规审查 → 广告诊断 → 人工审批 → dry-run 执行」串成一条可演示、可回测、可量化的业务链路。

> 所有数据均为合成数据，不包含真实 Amazon 数据；接口形状模仿 SP-API / Ads API，便于后续替换。合规规则为演示摘要，不构成法律建议。本项目与 Amazon 无关联。

---

## 这个 Demo 证明了什么

| JD 信号 | Demo 证据 |
|---|---|
| 流程自动化 | 一条命令/一个 API 跑完整链路；节点级耗时、token、成本、审计日志 |
| AIGC 内容生产 | Listing 标题/五点/描述/关键词生成 + 21 条规则审查 + 人工抽检入口 |
| 数据链路 | 90 天广告数据、30 天关键词数据、评论数据；建议可回测 |
| Multi-Agent 编排 | LangGraph 状态图、Supervisor 路由、HITL 断点、失败降级 |
| RAG | Chroma/BM25 混合检索、RRF、metadata 过滤、引用、10 条 golden case |
| 量化 | 合规通过率、修复数、ACOS 变化、预计花费变化、单次成本 |

---

## 快速开始

```powershell
# 1. 创建环境（Python 3.11）
uv venv .venv --python 3.11
uv pip install --python .venv\Scripts\python.exe -r requirements.txt

# 2. 生成合成数据
.\.venv\Scripts\python.exe data\generate_seed.py

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

- **数据层**：`core/store.py` 读取合成数据；`rag/ingest.py` 构建检索语料。
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
| Executor | HITL 审批后 dry-run，写审计日志和指标 | 拒绝/未审批时跳过 |

模式：

- `full_chain`：Insight → Listing → Compliance → Ads → Approval → Executor
- `listing_only`：Insight → Listing → Compliance → Approval → Executor
- `ads_only`：Ads → Approval → Executor
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

## 验证状态

本机已验证（无 LLM key，规则兜底）：

- CLI：`scripts/run_demo.py` 全链路通过，审批后 5 条 dry-run 动作。
- API：`/runs` → `awaiting_approval` → `/approve` → `completed`。
- UI：Streamlit 页面渲染、运行、审批、审计、指标均通过。
- 评测：10/10 golden case 通过。
- Docker：`docker compose config` 校验通过；镜像构建未执行（本机 Docker daemon 未启动）。

未验证：真实 LLM 生成路径（需要填入 `OPENAI_API_KEY` 后重跑评测）；真实 SP-API / Ads API。

---

## 目录结构

```
amz-ops-agent/
├── agent/
│   ├── graph.py              # LangGraph 状态图
│   ├── state.py              # AgentState
│   ├── services.py           # LLM / Store / Retriever 装配
│   └── nodes/                # supervisor / insight / listing / compliance / ads / executor
├── api/main.py               # FastAPI
├── app/streamlit_app.py      # 演示台
├── core/
│   ├── config.py             # 环境变量
│   ├── llm.py                # OpenAI 兼容客户端 + JSON 解析 + 兜底
│   ├── db.py                 # SQLite runs / audit / metrics
│   └── store.py              # 合成数据访问
├── rag/
│   ├── ingest.py             # 语料构建
│   └── retriever.py          # BM25 + Chroma + RRF
├── data/
│   ├── generate_seed.py      # 确定性合成数据生成器
│   └── seed/                 # SKU / 评论 / Listing / 广告 / 规则 / 政策
├── evals/                    # golden set + 评测脚本
├── scripts/                  # CLI demo + smoke test
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

- 全部数据由 `data/generate_seed.py` 以固定随机种子生成，可复现。
- 5 个 SKU、20 条历史 Listing、150 条评论、450 行广告日报、30 条关键词数据、21 条合规规则、5 份政策摘要。
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

1. 选 `SKU-003`：评分 3.8、ACOS 97%、评论里集中抱怨电池/搅拌力/漏水。
2. 点 **Run pipeline**，四个 Agent 依次跑完。
3. **Insight**：3 个痛点 + 原文引用。
4. **Listing**：新标题/五点，引用历史高转化 Listing。
5. **Compliance**：当前 Listing 6 个问题，新草稿 0 个，修复 6 个。
6. **Ads**：ACOS 97%、花费上涨、5 条降价建议、30 天回测。
7. 侧边栏 **Approve**：执行器写 dry-run 审计日志。
8. **Metrics**：耗时、token、成本、合规通过率。

---

## License / Disclaimer

Demo only. Synthetic data. Not affiliated with Amazon.com, Inc. "Amazon" is a trademark of Amazon.com, Inc. or its affiliates.
