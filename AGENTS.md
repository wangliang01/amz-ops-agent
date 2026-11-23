# amz-ops-agent
Amazon 卖家多智能体运营副驾驶演示：洞察 → Listing → 合规 → 广告 → 人工审批 → dry-run。合成数据，不接真实店铺。

## 背景入口
- `SPEC.md`：范围 / Non-goals / 验收；`PROGRESS.md`：当前状态 / 下一步
- `.scratch/tickets/`：任务；`docs/adr/`：架构决策；`docs/verify.md`：唯一验证说明

## 技术栈
- 语言/运行时：Python 3.11.8 | 框架：FastAPI + LangGraph + Streamlit | 包管理器：pip | 存储：SQLite + 本地 Chroma
- UI 技能：`unslop`（只此一个，见 SPEC.md；本轮未安装）

## 命令
| 用途 | 命令 |
|---|---|
| 装依赖 | `.\.venv\Scripts\python.exe -m pip install -r requirements.txt` |
| 启动全部 | `.\run.ps1` |
| 启动 API | `.\.venv\Scripts\python.exe -m uvicorn api.main:app --reload` |
| 启动 UI | `.\.venv\Scripts\python.exe -m streamlit run app/streamlit_app.py` |
| 评测闸门 | `.\.venv\Scripts\python.exe -m evals.run_eval` |
| 全链路冒烟 | `.\.venv\Scripts\python.exe -m scripts.smoke_test` |
| CLI 演示 | `.\.venv\Scripts\python.exe -m scripts.run_demo --sku SKU-003 --approve` |
| 类型检查 / Lint | 未配置（无 mypy / ruff；不要假装跑过） |
| 全部验证 | 按 `docs/verify.md` |

## 工作流
1. 改完先跑本次相关命令 + 评测，全绿再继续；完成 = 贴出真实输出。
2. 一次只做一个最小改动，做完停下说明。
3. 不许为过测试改测试；要改先说明理由并获同意。
4. 提交前跑评测；一个任务一个提交。
5. 用户还在讨论范围/设计时，NEVER 写实现代码；明确说「开始/批准」才实现。

## 红线
- NEVER 提交 `.env` / key / 凭据；只提交 `.env.example`。
- `executor` 只能 dry-run：NEVER 删除 `interrupt_before` 或增加真实店铺写接口。
- `data/seed/**` 只读；改数据只改 `data/generate_seed.py` 后重新生成。
- 合规 `block` / `warn` 语义改动必须同步 golden eval。
- 不新增依赖，除非明确同意；NEVER 未经确认 `push --force` / `reset --hard` / 删数据。

## 验收
见 `SPEC.md` 的 AC-1..AC-7；任务验收见 `.scratch/tickets/`。
