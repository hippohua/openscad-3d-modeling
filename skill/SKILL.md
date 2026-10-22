---
name: openscad-3d-modeling
description: >
  Programmatic 3D modeling with OpenSCAD: turn natural-language descriptions,
  hand-drawn sketches, or photos into precise, parametric 3D models through
  multi-turn dimension interviews, then export STL/3MF/OFF/AMF/DXF/SVG for
  3D printing or laser cutting. Use when the user wants to create, modify, or
  3D-print a model (盒子/支架/外壳/齿轮/夹具/旋钮/底座, model, part, case,
  bracket, gear), or asks to convert an image or idea into a printable 3D file.
metadata:
  version: "1.0.0"
  backend: "OpenSCAD 2021.01 CLI via openscad-mcp"
---

# OpenSCAD 3D 建模

通过 `openscad-mcp` MCP 服务器驱动本机 OpenSCAD 2021.01，把描述/草图/照片变成
精确的参数化 3D 模型。单位一律是毫米（mm）。

## 核心工作流（五步闭环）

### 1. 理解输入
- **自然语言**：提取物体类型、大致形状、用途（打印？装配？外观件？）。
- **手绘图/照片**：用视觉把目标**分解为基本体的组合**（ box / cylinder / 挖孔 /
  圆角 / 拉伸体 ），在回复中先口述你的分解理解，让用户确认。
- 判断复杂度：规则几何（≥90% 的实用零件）直接建模；自由曲面类明确告知
  OpenSCAD 不擅长，给出可实现的近似方案。

### 2. 尺寸追问（关键一步，不要跳过）
首次建模前，按 `references/measure-interview.md` 的清单**最多挑 3 个最关键的
未知量**用选择题/带默认值的问题问用户（推荐 AskUserQuestion 工具）。用户说
"随便/你定"时按人体工学和打印工艺默认值处理并声明。
典型必问：整体长宽高、壁厚、孔径与深度（通孔/盲孔）、圆角半径、配合间隙。

### 3. 编写 .scad 代码
- 语法速查：`references/openscad-cheatsheet.md`（也可调 MCP 工具
  `openscad_reference`）。
- 用 `module` + 参数组织代码，参数集中在文件顶部，方便后续多轮修改。
- 切削体故意加长/放大避免共面；打印件孔径做 0.2~0.4mm 补偿。

### 4. 渲染自检 + 多轮迭代（必做）
- 调 `render_preview`（等轴视角），**必须查看返回的图片**：
  比例是否失调？孔位对不对？结构是否符合描述？
- 需要核对某个面时再渲染 top/front/side 视角。
- 不满意就改代码重渲，通常 2~4 轮收敛。每轮改动向用户说明。
- 多轮对话中用户提出修改（"孔再大 2mm"、"左边加个耳朵"）：改参数重渲即可，
  不要推翻重写。

### 5. 导出交付
- 3D 打印：`export_model` 导出 **STL**（通用）或 **3MF**（带单位），返回的
  facets 数量一并报告。打印工艺注意事项见 `references/print-export.md`。
- 激光切割/2D：DXF / SVG。
- 最终回复中列出全部交付文件的绝对路径。

## 工具速查

| MCP 工具 | 用途 |
|---|---|
| `render_preview(scad_code, view, imgsize)` | 渲染 PNG 预览图，返回图片+路径 |
| `export_model(scad_code, formats, output_dir, basename)` | 导出 stl/3mf/off/amf/dxf/svg/csg/png |
| `validate_scad(scad_code)` | 只查编译错误（报错含行号） |
| `openscad_reference(topic)` | syntax/transforms/boolean/printing 速查 |

注意：`output_dir` 传用户可见的绝对路径（如工作区目录），不要留在临时目录里。

## 能力边界（如实告知用户）
- 照片/手绘是"视觉分解 + 多轮问答逼近尺寸"，不是一键逆向 CAD。
- 参数化零件效果最佳；复杂曲面、艺术雕塑、装配体运动仿真不是本技能赛道。
- 螺纹用简化近似（无真螺旋扫描），高精度螺纹件建议后续在切片软件或
  专业 CAD 中处理。
