#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OpenSCAD MCP server (stdio, newline-delimited JSON-RPC).

纯 Python 标准库实现，无第三方依赖。
把本机 OpenSCAD 2021.01 命令行封装成 MCP 工具：
  render_preview  - 编译 .scad 代码并渲染 PNG 预览（返回图片 + 路径）
  export_model    - 导出 STL / 3MF / OFF / AMF / DXF / SVG / CSG / PNG
  validate_scad   - 编译检查，返回报错信息
  openscad_reference - 内置语法/打印速查

可用环境变量 OPENSCAD_PATH 覆盖 openscad.com 的默认路径。
"""

import base64
import json
import os
import re
import subprocess
import sys
import tempfile
import time

SERVER_NAME = "openscad-mcp"
SERVER_VERSION = "1.0.0"
PROTOCOL_VERSION = "2024-11-05"

DEFAULT_OPENSCAD = r"D:\Program Files\OpenSCAD\openscad.com"
OPENSCAD = os.environ.get("OPENSCAD_PATH") or DEFAULT_OPENSCAD

VIEW_ARGS = {
    "isometric": ["--camera=0,0,0,55,0,25,0", "--autocenter", "--viewall", "--projection=p"],
    "top":       ["--camera=0,0,0,0,0,0,0",  "--autocenter", "--viewall", "--projection=p"],
    "front":     ["--camera=0,0,0,90,0,0,0", "--autocenter", "--viewall", "--projection=p"],
    "side":      ["--camera=0,0,0,90,0,90,0", "--autocenter", "--viewall", "--projection=p"],
}

EXPORT_FORMATS = ("stl", "3mf", "off", "amf", "dxf", "svg", "csg", "png")

MAX_INLINE_IMAGE_BYTES = 2 * 1024 * 1024

TOOLS = [
    {
        "name": "render_preview",
        "description": (
            "Compile OpenSCAD .scad code and render a PNG preview image. "
            "Returns the image (base64 PNG content) and the file path, so the caller "
            "can visually inspect the model and iterate. Views: isometric/top/front/side."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "scad_code": {"type": "string", "description": "OpenSCAD source code (.scad). Units are mm."},
                "view": {"type": "string", "enum": ["isometric", "top", "front", "side"],
                         "description": "Camera view, default isometric."},
                "imgsize": {"type": "array", "items": {"type": "integer"}, "minItems": 2, "maxItems": 2,
                            "description": "Image size [width,height], default [800,600]."},
                "colorscheme": {"type": "string",
                                "description": "OpenSCAD colorscheme, default Cornfield."},
            },
            "required": ["scad_code"],
        },
    },
    {
        "name": "export_model",
        "description": (
            "Compile OpenSCAD .scad code and export model files. "
            "Formats: stl (3D print), 3mf (3D print, units+color), off, amf, "
            "dxf/svg (2D profiles), csg (source), png (image). "
            "Returns per-format file path, byte size and facet count where available."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "scad_code": {"type": "string"},
                "formats": {"type": "array", "items": {"type": "string",
                            "enum": list(EXPORT_FORMATS)},
                            "description": "Export formats, default ['stl']."},
                "output_dir": {"type": "string",
                               "description": "Absolute output directory; created if missing. Default: a temp dir."},
                "basename": {"type": "string", "description": "Output base filename without extension, default 'model'."},
            },
            "required": ["scad_code"],
        },
    },
    {
        "name": "validate_scad",
        "description": (
            "Syntax/geometry check of .scad code without saving artifacts. "
            "Runs a tiny full-pipeline render; returns ok=true or the compiler error text."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"scad_code": {"type": "string"}},
            "required": ["scad_code"],
        },
    },
    {
        "name": "openscad_reference",
        "description": "Compact OpenSCAD quick reference. Topics: syntax, transforms, boolean, printing.",
        "inputSchema": {
            "type": "object",
            "properties": {"topic": {"type": "string", "enum": ["syntax", "transforms", "boolean", "printing"]}},
            "required": ["topic"],
        },
    },
]

REFERENCE = {
"syntax": """OpenSCAD quick reference - primitives & language
- cube([w,d,h], center=false)          box, mm
- sphere(r=|d=, $fn=)                  ball
- cylinder(h, r1, r2, r=|d=, center, $fn=)  cone/cylinder (r1 bottom, r2 top)
- square([w,d], center) / circle(r) / polygon(points)   2D shapes
- text("txt", size=, font=, halign=, valign=)           2D text outline
- linear_extrude(h, center, twist, scale)               2D -> 3D slab
- rotate_extrude(angle=)                                2D profile -> ring
- import("file.stl")                                    import mesh
- surface("heightmap.png")                              heightmap -> terrain
Control: for(i=[0:step:n]) / for(a=[x,y,z]) | if(cond) | let(i=..) | each
Module: module name(args){...} then name(arg=..); children() inside module
Function: function f(x)=expression; recursion allowed
Variables are immutable per scope (last assignment wins); use lists + concat/list comprehension to accumulate
Special: $fn (fragments, e.g. 64-128 for print), $fa/$fs, $t, $vpr/$vpt
Modifiers: # debug(highlight) / ! show only this / % transparent(background) / * disable
echo() prints to console; assert(cond,msg) guards parameters
""",

"transforms": """OpenSCAD quick reference - transforms
- translate([x,y,z])         move
- rotate([rx,ry,rz])         rotate degrees around axes; rotate(a, v=[x,y,z]) axis form
- scale([sx,sy,sz])          scale; resize([w,d,h], auto=true) fit to size
- mirror([nx,ny,nz])         mirror across plane normal
- multmatrix(m)              raw 4x4 matrix
- color("red") / color([r,g,b,a])   color a subtree (preview only)
- offset(r=|delta=, chamfer) 2D outline grow/shrink (great for shells)
- hull()                     convex hull of children (fillet trick: hull of two cylinders)
- minkowski(){...}           sweep child over child (slow; rounding: cube + sphere)
- union/difference/intersection: boolean ops, first child = base
Order matters: transforms apply to their immediate children block.
""",

"boolean": """OpenSCAD quick reference - boolean workflow
- difference(){ base(); tool1(); tool2(); }   subtract tools 2..n from child 1
- union(){ a(); b(); }                        merge
- intersection(){ a(); b(); }                 common volume
Tips:
- Make cutting tools slightly oversized and protruding to avoid coincident faces:
  cylinder(h+2, r=hole_d/2, center=true)
- Use $fn on cutting tools explicitly, not globally, to keep export fast
- Hole compensation for FDM printing: hole_d/2 + 0.2 (approx, tune per printer)
- Rounded vertical edges: minkowski(){cube([w-2r,d-2r,h]); cylinder(r=r,$fn=64);} or hull of cylinders
- Shells: difference(){ offset(r=+t) shape; shape; } in 2D before extrude
""",

"printing": """OpenSCAD quick reference - 3D printing exports
Formats:
- STL: universal, no units/color; slicer assumes mm. Use for most slicers.
- 3MF: units + color + multiple bodies; preferred when supported.
- OFF/AMF: legacy; AMF supports color. DXF/SVG: 2D profiles for laser cutting.
Resolution: $fn=64..128 for curved print surfaces; 32 enough for preview.
Design rules (FDM):
- min wall ~1.2mm (3 perimeters); min feature ~0.4mm
- overhang <= 45 deg or add support; avoid large flat overhangs
- holes print ~0.2-0.4mm small: add compensation
- flat side down for stability; chamfer bottom edges 0.4mm to avoid elephant foot
- clearance for moving/fitting parts: 0.2-0.4mm gap (loose fit 0.5)
CLI: openscad.com -o out.stl model.scad ; -o out.png --imgsize=800,600 --autocenter --viewall
""",
}


def _run_openscad(args, timeout):
    """Run openscad.com, return (returncode, stdout, stderr)."""
    try:
        proc = subprocess.run(
            [OPENSCAD] + args,
            capture_output=True, timeout=timeout,
        )
        out = proc.stdout.decode("utf-8", "replace")
        err = proc.stderr.decode("utf-8", "replace")
        return proc.returncode, out, err
    except FileNotFoundError:
        return 127, "", "OpenSCAD not found at: %s (set OPENSCAD_PATH)" % OPENSCAD
    except subprocess.TimeoutExpired:
        return 124, "", "OpenSCAD timed out after %ss" % timeout


def _err_tail(text, limit=800):
    text = (text or "").strip()
    return text[-limit:] if len(text) > limit else text


def _write_scad(scad_code, workdir, basename="model"):
    path = os.path.join(workdir, basename + ".scad")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(scad_code)
    return path


def _new_workdir():
    base = os.path.join(tempfile.gettempdir(), "openscad-mcp")
    workdir = os.path.join(base, time.strftime("%Y%m%d-%H%M%S") + "-" + str(os.getpid()))
    os.makedirs(workdir, exist_ok=True)
    return workdir


def _facets_from_log(log):
    m = re.search(r"Facets:\s*(\d+)", log)
    return int(m.group(1)) if m else None


def tool_render_preview(args):
    scad_code = args.get("scad_code", "")
    if not scad_code.strip():
        raise ValueError("scad_code is empty")
    view = args.get("view", "isometric")
    if view not in VIEW_ARGS:
        raise ValueError("view must be one of %s" % ", ".join(VIEW_ARGS))
    imgsize = args.get("imgsize") or [800, 600]
    colorscheme = args.get("colorscheme", "Cornfield")
    workdir = _new_workdir()
    scad_path = _write_scad(scad_code, workdir)
    png_path = os.path.join(workdir, "preview.png")
    cmd = ["-o", png_path,
           "--imgsize=%d,%d" % (int(imgsize[0]), int(imgsize[1])),
           "--colorscheme=" + colorscheme,
           "--render"] + VIEW_ARGS[view] + [scad_path]
    code, out, err = _run_openscad(cmd, timeout=600)
    if code != 0 or not os.path.exists(png_path):
        return {"ok": False, "error": _err_tail(err) or _err_tail(out) or "render failed"}
    with open(png_path, "rb") as fh:
        data = fh.read()
    result = {
        "ok": True,
        "png_path": png_path,
        "scad_path": scad_path,
        "bytes": len(data),
        "note": "Inspect the image, then refine scad_code and render again.",
    }
    content = [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]
    if len(data) <= MAX_INLINE_IMAGE_BYTES:
        content.append({"type": "image", "data": base64.b64encode(data).decode("ascii"),
                        "mimeType": "image/png"})
    else:
        content.append({"type": "text", "text": "Image too large to inline; open: " + png_path})
    return {"content": content}


def tool_export_model(args):
    scad_code = args.get("scad_code", "")
    if not scad_code.strip():
        raise ValueError("scad_code is empty")
    formats = args.get("formats") or ["stl"]
    for fmt in formats:
        if fmt not in EXPORT_FORMATS:
            raise ValueError("unsupported format: %s (supported: %s)" % (fmt, ", ".join(EXPORT_FORMATS)))
    output_dir = args.get("output_dir") or _new_workdir()
    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    basename = re.sub(r"[^A-Za-z0-9_.-]", "_", args.get("basename") or "model") or "model"
    scad_path = _write_scad(scad_code, output_dir, basename=basename)
    results = []
    for fmt in formats:
        out_path = os.path.join(output_dir, basename + "." + fmt)
        cmd = ["-o", out_path]
        if fmt == "png":
            cmd += ["--imgsize=800,600", "--autocenter", "--viewall"]
        cmd.append(scad_path)
        code, out, err = _run_openscad(cmd, timeout=1800)
        item = {"format": fmt, "ok": code == 0 and os.path.exists(out_path)}
        if item["ok"]:
            item["path"] = out_path
            item["bytes"] = os.path.getsize(out_path)
            facets = _facets_from_log(out + err)
            if facets is not None:
                item["facets"] = facets
        else:
            item["error"] = _err_tail(err) or _err_tail(out) or ("exit code %d" % code)
        results.append(item)
    ok = all(r.get("ok") for r in results)
    body = {"ok": ok, "results": results, "scad_path": scad_path}
    return {"content": [{"type": "text", "text": json.dumps(body, ensure_ascii=False)}]}


def tool_validate_scad(args):
    scad_code = args.get("scad_code", "")
    if not scad_code.strip():
        raise ValueError("scad_code is empty")
    workdir = _new_workdir()
    scad_path = _write_scad(scad_code, workdir, basename="check")
    cmd = ["-o", os.path.join(workdir, "check.png"),
           "--imgsize=240,180", "--autocenter", "--viewall", scad_path]
    code, out, err = _run_openscad(cmd, timeout=600)
    if code == 0:
        return {"content": [{"type": "text",
                "text": json.dumps({"ok": True, "note": "compile+render pipeline passed"},
                                   ensure_ascii=False)}]}
    msg = _err_tail(err) or _err_tail(out)
    return {"content": [{"type": "text",
            "text": json.dumps({"ok": False, "error": msg}, ensure_ascii=False)}],
            "isError": True}


def tool_openscad_reference(args):
    topic = args.get("topic", "syntax")
    text = REFERENCE.get(topic, "")
    return {"content": [{"type": "text", "text": text}]}


TOOL_HANDLERS = {
    "render_preview": tool_render_preview,
    "export_model": tool_export_model,
    "validate_scad": tool_validate_scad,
    "openscad_reference": tool_openscad_reference,
}


def handle_request(msg):
    method = msg.get("method")
    msg_id = msg.get("id")
    is_notification = msg_id is None
    try:
        if method == "initialize":
            result = {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            }
        elif method == "tools/list":
            result = {"tools": TOOLS}
        elif method == "tools/call":
            params = msg.get("params") or {}
            name = params.get("name")
            handler = TOOL_HANDLERS.get(name)
            if handler is None:
                raise KeyError("unknown tool: %s" % name)
            result = handler(params.get("arguments") or {})
        elif method == "ping":
            result = {}
        elif is_notification:
            return None
        else:
            if is_notification:
                return None
            return {"jsonrpc": "2.0", "id": msg_id,
                    "error": {"code": -32601, "message": "method not found: %s" % method}}
    except Exception as exc:  # noqa: BLE001
        if is_notification:
            return None
        return {"jsonrpc": "2.0", "id": msg_id,
                "error": {"code": -32000, "message": "server error: %s" % exc}}
    if is_notification:
        return None
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}


def main():
    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue
        try:
            msg = json.loads(raw)
        except ValueError:
            continue
        reply = handle_request(msg)
        if reply is not None:
            sys.stdout.write(json.dumps(reply, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
