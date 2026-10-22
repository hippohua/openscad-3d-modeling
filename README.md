# openscad-3d-modeling

让 AI 编程助手（WorkBuddy / Claude Code 等支持 MCP 的智能体）通过自然语言描述、
手绘图或照片制作精确的参数化 3D 模型，多轮对话确认关键尺寸，最终导出可直接
3D 打印的 STL / 3MF 文件。底层由 [OpenSCAD](https://openscad.org) 命令行驱动。

## 它是怎么工作的

```
你的描述 / 草图 / 照片
        |
        v
  AI 识别形状特征，追问关键尺寸（长宽高 / 壁厚 / 孔径 / 角度 / 配合间隙）
        |
        v
  生成 .scad 代码 --> MCP render_preview 渲染 PNG --> AI 看图自检
        |                                                  |
        |<-------------- 不满意就改参数重渲（2~4 轮收敛）------|
        v
  多轮对话修改（"孔再大 2mm"、"加个耳朵"）→ 重渲确认
        |
        v
  export_model 导出 STL / 3MF / OFF / AMF / DXF / SVG（含面数统计）
```

OpenSCAD 是"程序化 3D 编译器"：脚本经过词法/语法解析、CSG 布尔树归约、
CGAL 精确布尔运算生成网格。这套 skill 把它的命令行模式包成 MCP 工具，
让 AI 形成"生成 → 看图 → 追问 → 修改 → 导出"的完整闭环。

## MCP 工具

| 工具 | 功能 |
|---|---|
| `render_preview` | 编译 .scad 渲染 PNG（等轴/顶/前/侧视角），图片内联返回供 AI 查看 |
| `export_model` | 导出 STL / 3MF / OFF / AMF / DXF / SVG / CSG / PNG，返回路径与面数 |
| `validate_scad` | 编译检查，报错精确到行号 |
| `openscad_reference` | 内置语法 / 变换 / 布尔 / 打印工艺速查 |

## 安装

### 前置要求

- OpenSCAD 2021.01 或更高版本，[官网下载](https://openscad.org/downloads/)，
  Windows 默认安装到 `C:\Program Files\OpenSCAD`（本项目实测路径为
  `D:\Program Files\OpenSCAD`，可用环境变量 `OPENSCAD_PATH` 指向你的
  `openscad.com`）
- Python 3.11+（MCP 服务器只用标准库，**无需 pip 安装任何包**）

### 1. 放置文件

```
~/.workbuddy/tools/openscad-mcp/openscad_mcp.py     <- 本仓库 mcp/openscad_mcp.py
~/.workbuddy/skills/openscad-3d-modeling/SKILL.md   <- 本仓库 skill/SKILL.md
~/.workbuddy/skills/openscad-3d-modeling/references/*.md
```

其他智能体（Claude Code 等）把 skill 复制到对应的 skills 目录即可，
MCP 服务器本身与客户端无关。

### 2. 注册 MCP

在客户端的 `mcp.json` 中加入（Windows 示例，路径按实际修改）：

```json
{
  "mcpServers": {
    "openscad": {
      "command": "C:/path/to/python.exe",
      "args": ["C:/Users/<you>/.workbuddy/tools/openscad-mcp/openscad_mcp.py"]
    }
  }
}
```

非默认安装路径时加环境变量：

```json
"env": { "OPENSCAD_PATH": "D:/Program Files/OpenSCAD/openscad.com" }
```

### 3. 重启客户端，开始使用

直接说："帮我建一个 60x40 带四个 M3 孔的面板"、"照这张手绘图做一个外壳"，
或丢一张实物照片。

## 能力边界

- 照片/手绘的工作方式是"AI 视觉分解 + 多轮问答逼近尺寸"，不是一键逆向 CAD。
- 参数化零件（盒子、支架、外壳、齿轮、夹具、旋钮）效果最佳；
  自由曲面、艺术雕塑、真螺纹不是 OpenSCAD 的赛道。
- 输出模型单位为 mm。

## 许可与声明

- 本仓库代码与文档：[MIT License](LICENSE)
- [OpenSCAD](https://github.com/openscad/openscad) 由其作者以 GNU GPL v2
  授权，需单独安装；本仓库通过命令行调用独立安装的 OpenSCAD，
  不包含、不修改、不再分发其任何代码或二进制。
- 本项目与 OpenSCAD 官方无关联、未获背书。
- 内置速查文档为原创撰写，未复制 OpenSCAD 官方手册内容。
