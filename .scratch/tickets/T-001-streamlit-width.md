# [T-001] 替换 Streamlit 已弃用的 `use_container_width`

- **Status**: Pending
- **Depends On**: 无
- **对应 SPEC**: AC-4（回归）
- **预估轮数**: 3
- **预估 diff 行数**: < 50
- **Target Files**:
  - `app/streamlit_app.py`

## 要解决的问题

Streamlit 1.67 对 `use_container_width` 发出弃用警告：提示 2025-12-31 后移除，当前仍可用。继续留着会在未来升级时直接报错。该参数在 `app/streamlit_app.py` 中出现 9 次。

## 范围

- 做：把 `use_container_width=True` 换成 `width="stretch"`，`False` 换成 `width="content"`；不改布局与文案。
- 不做：不调整页面结构、不引入 UI 技能、不改其他文件。

## Stop conditions（遇到就停，不要硬做）

- 需要新增依赖 / 改数据模型 / 改外部接口
- 需要动 Target Files 之外的文件，或 diff 预计 > 200 行
- 同一处改 3 次不过
- AC 与 SPEC 冲突，或 AC 无法验证

## 验收标准（必须可执行）

- [ ] AC-1：启动 UI 时终端不再出现 `Please replace use_container_width with width`。
- [ ] AC-2：`Insight` / `Listing` / `Compliance` / `Ads` / `Audit` / `Metrics` 六个 tab 仍在；run → `awaiting_approval`，approve → `completed`，5 条 dry-run 动作不变。
- [ ] AC-3：`.\.venv\Scripts\python.exe -m compileall -q app` 退出码 0。

## 验证方式

```powershell
.\.venv\Scripts\python.exe -m compileall -q app
.\run.ps1
# 观察终端无弃用警告；按 docs/verify.md §3.2 走一遍主流程
```

## 完成记录

- 提交：
- 证据（输出 / 截图 / 响应）：

## 裁判记录

| AC | 判定（达成 / 未达成 / 无法验证） | 证据 |
|---|---|---|
| AC-1 | | |
| AC-2 | | |
| AC-3 | | |
