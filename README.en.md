# openscad-3d-modeling

[English](README.en.md) | [简体中文](README.md)

Let AI coding assistants (WorkBuddy, Claude Code, or any MCP-capable agent)
turn natural-language descriptions, hand-drawn sketches, or photos into
precise, parametric 3D models — with multi-turn dimension interviews — and
export 3D-printable STL / 3MF files. Powered by the
[OpenSCAD](https://openscad.org) command line.

## How it works

```
Your description / sketch / photo
        |
        v
  AI identifies shape features, asks for key dimensions
  (L x W x H / wall thickness / hole diameter / angles / fit clearances)
        |
        v
  Generate .scad code --> MCP render_preview (PNG) --> AI inspects the image
        |                                                  |
        |<-------- refine parameters and re-render (2~4 rounds) ---->|
        v
  Multi-turn edits ("make the hole 2mm bigger", "add an ear") -> re-render
        |
        v
  export_model -> STL / 3MF / OFF / AMF / DXF / SVG (with facet counts)
```

OpenSCAD is a "programmatic 3D compiler": scripts are parsed into an AST,
reduced to a CSG boolean tree, and turned into meshes via exact CGAL boolean
operations. This project wraps its CLI into MCP tools so the agent can run a
full "generate -> inspect -> ask -> refine -> export" loop.

## MCP tools

| Tool | Purpose |
|---|---|
| `render_preview` | Compile .scad and render a PNG (isometric/top/front/side); image returned inline for the agent to inspect |
| `export_model` | Export STL / 3MF / OFF / AMF / DXF / SVG / CSG / PNG with facet statistics |
| `validate_scad` | Compile check with line-numbered error messages |
| `openscad_reference` | Built-in quick reference: syntax / transforms / boolean / printing |

## Installation

### Prerequisites

- OpenSCAD 2021.01 or later — [download](https://openscad.org/downloads/).
  On Windows the default install path is `C:\Program Files\OpenSCAD`; if yours
  differs, set the `OPENSCAD_PATH` environment variable to your
  `openscad.com`.
- Python 3.11+ — the MCP server uses **only the standard library**, no pip
  packages required.

### 1. Place the files

```
~/.workbuddy/tools/openscad-mcp/openscad_mcp.py     <- from mcp/openscad_mcp.py
~/.workbuddy/skills/openscad-3d-modeling/SKILL.md   <- from skill/SKILL.md
~/.workbuddy/skills/openscad-3d-modeling/references/*.md
```

For other agents (e.g. Claude Code), copy the skill folder into the agent's
own skills directory. The MCP server itself is client-agnostic.

### 2. Register the MCP server

Add to your client's `mcp.json` (Windows example; adjust paths):

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

For a non-default OpenSCAD location, add:

```json
"env": { "OPENSCAD_PATH": "D:/Program Files/OpenSCAD/openscad.com" }
```

### 3. Restart your client and start modeling

Just say: "build me a 60x40 panel with four M3 holes", "make a case from this
sketch", or drop a photo of a real object.

## Limitations (read before expecting magic)

- Photos and sketches work via "AI visual decomposition + multi-turn Q&A",
  not one-click reverse CAD.
- Parametric parts (boxes, brackets, cases, gears, jigs, knobs) work best;
  free-form sculpting and true threads are not OpenSCAD's strength.
- Model units are millimeters.

## License & notices

- Code and docs in this repo: [MIT License](LICENSE)
- [OpenSCAD](https://github.com/openscad/openscad) is licensed by its authors
  under the GNU GPL v2 and must be installed separately. This repo invokes a
  separately installed OpenSCAD from the command line; it does not include,
  modify, or redistribute any OpenSCAD code or binaries.
- This project is not affiliated with or endorsed by the OpenSCAD project.
- The bundled quick-reference docs are original work; no text was copied from
  the OpenSCAD manual.
