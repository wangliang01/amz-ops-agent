# [T-001] 替换 Streamlit 已弃用的 `use_container_width`

- **Status**: Done
- **Depends On**: 无
- **对应 SPEC**: AC-4（全部 5 个子项）
- **预估轮数**: 3
- **预估 diff 行数**: < 50
- **Target Files**:
  - `app/streamlit_app.py`

## 要解决的问题

Streamlit 1.67 对 `use_container_width` 发出弃用警告：提示 2025-12-31 后移除，当前仍可用。继续留着会在未来升级时直接报错。该参数在 `app/streamlit_app.py` 中出现 4 次（47 / 105 / 123 / 134 行）。

## 范围

- 做：把 `use_container_width=True` 换成 `width="stretch"`，`False` 换成 `width="content"`；不改布局与文案。
- 不做：不调整页面结构、不引入 UI 技能、不改其他文件。

## Stop conditions（遇到就停，不要硬做）

- 需要新增依赖 / 改数据模型 / 改外部接口
- 需要动 Target Files 之外的文件，或 diff 预计 > 200 行
- 同一处改 3 次不过
- AC 与 SPEC 冲突，或 AC 无法验证

## 验收标准（必须可执行）

- [x] AC-1：Streamlit 在 8501 可启动并返回 200；启动日志不再出现 `Please replace use_container_width with width`。
- [x] AC-2：选 `SKU-003` + `full_chain` 运行 → `awaiting_approval`；`Insight` / `Listing` / `Compliance` / `Ads` / `Audit` / `Metrics` 六个 tab 均渲染；Approve → `completed`；`Audit` 对应的 `execution_log` 有 5 条 dry-run 记录。
- [x] AC-3：API 不可达（如 `API_BASE_URL=http://127.0.0.1:8099`）时，侧栏出现 `API not reachable` 与启动命令，页面不白屏。
- [x] AC-4：`.\.venv\Scripts\python.exe -m compileall -q app` 退出码 0。

## 验证方式

```powershell
.\.venv\Scripts\python.exe -m compileall -q app

# AC-1：8501 启动 + 无弃用警告
.\.venv\Scripts\python.exe -m streamlit run app/streamlit_app.py --server.headless true --server.port 8501
# 另开终端：curl.exe -s -o NUL -w "%{http_code}" http://127.0.0.1:8501

# AC-2 / AC-3：AppTest 驱动主流程与 API 不可达分支
# 期望：SKU-003 + full_chain；6 tabs；awaiting_approval → completed；5 条动作；
#       API_BASE_URL=8099 时 errors 含 "API not reachable" 且有启动命令，无 exception
```

## 完成记录

- 提交：`6c3900e`
- 证据（输出 / 截图 / 响应）：
  - AC-1：`streamlit run ... --server.port 8501` → HTTP 200；8501 与 AppTest 日志均无 `use_container_width` 文案。
  - AC-2：AppTest `MAIN_FLOW_OK`；`tabs: ['Insight', 'Listing', 'Compliance', 'Ads', 'Audit', 'Metrics']`；`status: completed actions: 5 all_dry_run: True`。
  - AC-3：`API_BASE_URL=http://127.0.0.1:8099` → `errors: ['API not reachable: ...']`、`codes: ['uvicorn api.main:app --reload']`、`exceptions: []`。
  - AC-4：`compileall -q app` → exit 0。

## 裁判记录

| AC | 判定（达成 / 未达成 / 无法验证） | 证据 |
|---|---|---|
| AC-1 | 达成 | 8501 HTTP 200；真实会话与 AppTest 均无弃用文案；4 处已替换（47 / 105 / 123 / 134 行） |
| AC-2 | 达成 | 真实 8501 会话 6 tabs；`run-1811c310` 为 SKU-003 / full_chain / completed / 5 动作；AppTest 复跑一致 |
| AC-3 | 达成 | 8099 场景 `errors` 含 `API not reachable`，`code` 含启动命令，`exceptions` 空，Run 按钮 disabled |
| AC-4 | 达成 | `compileall -q app` 退出码 0 |
