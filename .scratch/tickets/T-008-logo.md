# [T-008] 重做品牌 mark 与 favicon

- **Status**: In Progress
- **Depends On**: T-004
- **对应 SPEC**: `SPEC-004-ui-redesign.md`（纸白 / 墨色 / 黄铜；扁平、单色、无渐变）
- **预估轮数**: 1
- **预估 diff 行数**: < 120

## 要解决的问题

当前 logo 是「方框套黄铜方块」的占位图形（`app/assets/mark.png` + CSS `.brand-mark::after`），与产品的审批闸门形态无关，视觉上也弱。

## 范围

- 做：按「审批闸门」方向重画 mark：墨色门框 + 底部立柱 + 黄铜节点；同步页头、侧栏与 favicon；`scripts/make_mark.py` 可重复生成 PNG。
- 不做：改配色 / 字体 / 布局；新增依赖；重命名产品；引入位图插画。

## Stop conditions

- 需要新增依赖
- 需要改业务逻辑
- 同一处改 3 次不过

## 验收标准

- [x] AC-1：mark 为扁平矢量形态，只用墨色 + 黄铜一个节点，不含渐变、发光、emoji、文字。
- [x] AC-2：页头与侧栏使用同一 mark，尺寸随位置调整；`aria-hidden` 保留。
- [x] AC-3：favicon 使用新 `app/assets/mark.png`，PNG 由 `scripts/make_mark.py` 生成且可重复。
- [x] AC-4：`scripts.verify_ui`（remote / local 两种入口）仍通过，无新增 error。
- [x] AC-5：`compileall` 退出 0；浏览器截图确认页头、侧栏、favicon 渲染正常。

## 完成记录

- 完成时间：2026-11-24。
- 形态：开口闸门（`M4 22V4h16v18`，墨色 2.4 stroke）+ 中心黄铜节点（`r=2.2`）；页头 20px、侧栏 18px，SVG 带 `aria-hidden="true"` 与 `focusable="false"`。
- `app/assets/mark.png`：256×256 RGBA，由 `scripts/make_mark.py` 按同一几何生成；重复运行输出一致。
- `scripts.verify_ui`：`app/streamlit_app.py` 与 `app/streamlit_cloud.py` 两个入口均为 `UI_VERIFY_OK tabs=6 ... errors=0`。
- 浏览器实测（ego-browser，1440 / 390）：页头 `.brand-mark` 计算尺寸 `20×20`、knob `r=2.2` / `#9C631C`；侧栏 18px；`innerWidth == documentElement.scrollWidth`（1440/1440、390/390），无横向滚动；favicon 由 `/media/...png` 正常加载。
- 截图：`.scratch/ui/T-008/brand-1440.png`、`.scratch/ui/T-008/brand-390.png`。
- `compileall -q agent api app core rag evals scripts data` 退出 0。
- 提交：见 `PROGRESS.md`。
