#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import html
import math
import sys
import uuid
import xml.etree.ElementTree as ET
from collections import defaultdict, deque
from pathlib import Path

import yaml


NODE_STYLES = {
    "input": "rounded=1;whiteSpace=wrap;html=1;fillColor=#DAE8FC;strokeColor=#6C8EBF;",
    "module": "rounded=1;whiteSpace=wrap;html=1;fillColor=#FFF2CC;strokeColor=#D6B656;",
    "output": "rounded=1;whiteSpace=wrap;html=1;fillColor=#D5E8D4;strokeColor=#82B366;",
    "storage": "shape=cylinder3;whiteSpace=wrap;html=1;boundedLbl=1;fillColor=#E1D5E7;strokeColor=#9673A6;",
    "decision": "rhombus;whiteSpace=wrap;html=1;fillColor=#F8CECC;strokeColor=#B85450;",
    "group-anchor": "rounded=1;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;dashed=1;",
}

GROUP_STYLE = "rounded=1;whiteSpace=wrap;html=1;fillColor=none;strokeColor=#666666;dashed=1;container=1;collapsible=0;"
EDGE_STYLE = "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;endArrow=block;endFill=1;"


def extract_yaml_from_markdown(text: str) -> str:
    import re

    match = re.search(r"```ya?ml\s*\n(.*?)\n```", text, re.S)
    if not match:
        raise ValueError("No fenced ```yaml code block found in the Markdown source.")
    return match.group(1).strip() + "\n"


def read_spec(path_str: str, from_markdown: bool | None) -> tuple[dict, str]:
    if path_str == "-":
        text = sys.stdin.read()
        source_name = "stdin"
        suffix = ".md" if from_markdown else ".yaml"
    else:
        path = Path(path_str)
        text = path.read_text(encoding="utf-8")
        source_name = str(path)
        suffix = path.suffix.lower()

    md_mode = from_markdown if from_markdown is not None else suffix in {".md", ".markdown"}
    yaml_text = extract_yaml_from_markdown(text) if md_mode else text
    data = yaml.safe_load(yaml_text)
    if not isinstance(data, dict):
        raise ValueError("Diagram spec must decode to a mapping/object.")
    return data, source_name


def topological_levels(nodes: list[dict], edges: list[dict]) -> dict[str, int]:
    node_ids = [n["id"] for n in nodes]
    indeg = {nid: 0 for nid in node_ids}
    outgoing: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        src = edge.get("from")
        dst = edge.get("to")
        if src in indeg and dst in indeg:
            outgoing[src].append(dst)
            indeg[dst] += 1

    q = deque([nid for nid, d in indeg.items() if d == 0])
    level = {nid: 0 for nid in node_ids}
    visited: set[str] = set()

    while q or len(visited) < len(node_ids):
        if not q:
            remaining = [nid for nid in node_ids if nid not in visited]
            if not remaining:
                break
            # Break feedback loops conservatively: keep the partially built
            # backbone layout and release the remaining lowest-indegree node.
            fallback = min(remaining, key=lambda nid: (indeg[nid], level.get(nid, 0), node_ids.index(nid)))
            q.append(fallback)

        cur = q.popleft()
        if cur in visited:
            continue
        visited.add(cur)
        for nxt in outgoing[cur]:
            level[nxt] = max(level[nxt], level[cur] + 1)
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                q.append(nxt)

    return level


def layout_nodes(spec: dict) -> tuple[dict[str, tuple[float, float, float, float]], float, float]:
    nodes = spec.get("nodes", [])
    edges = spec.get("edges", [])
    layout = spec.get("layout", "left-to-right")

    box_w = 170.0
    box_h = 70.0
    hgap = 90.0
    vgap = 50.0
    margin_x = 60.0
    margin_y = 60.0

    positions: dict[str, tuple[float, float, float, float]] = {}

    if layout in {"left-to-right", "architecture", "pipeline", "patent-architecture"}:
        levels = topological_levels(nodes, edges)
        cols: dict[int, list[dict]] = defaultdict(list)
        for node in nodes:
            cols[levels.get(node["id"], 0)].append(node)

        max_height = 0.0
        max_col = 0
        for col_idx, members in cols.items():
            max_col = max(max_col, col_idx)
            col_height = len(members) * box_h + max(0, len(members) - 1) * vgap
            max_height = max(max_height, col_height)

        for col_idx, members in cols.items():
            col_x = margin_x + col_idx * (box_w + hgap)
            col_height = len(members) * box_h + max(0, len(members) - 1) * vgap
            start_y = margin_y + max(0.0, (max_height - col_height) / 2.0)
            for idx, node in enumerate(members):
                x = col_x
                y = start_y + idx * (box_h + vgap)
                positions[node["id"]] = (x, y, box_w, box_h)

        width = margin_x * 2 + (max_col + 1) * box_w + max_col * hgap
        height = margin_y * 2 + max_height
        return positions, width, height

    if layout == "top-to-bottom":
        levels = topological_levels(nodes, edges)
        rows: dict[int, list[dict]] = defaultdict(list)
        for node in nodes:
            rows[levels.get(node["id"], 0)].append(node)

        max_width = 0.0
        max_row = 0
        for row_idx, members in rows.items():
            max_row = max(max_row, row_idx)
            row_width = len(members) * box_w + max(0, len(members) - 1) * hgap
            max_width = max(max_width, row_width)

        for row_idx, members in rows.items():
            row_y = margin_y + row_idx * (box_h + vgap)
            row_width = len(members) * box_w + max(0, len(members) - 1) * hgap
            start_x = margin_x + max(0.0, (max_width - row_width) / 2.0)
            for idx, node in enumerate(members):
                x = start_x + idx * (box_w + hgap)
                y = row_y
                positions[node["id"]] = (x, y, box_w, box_h)

        width = margin_x * 2 + max_width
        height = margin_y * 2 + (max_row + 1) * box_h + max_row * vgap
        return positions, width, height

    if layout == "hub-and-spoke":
        width = 980.0
        height = 700.0
        center_x = width / 2.0 - box_w / 2.0
        center_y = height / 2.0 - box_h / 2.0
        modules = nodes[:]
        if not modules:
            return positions, width, height
        hub = modules[0]
        positions[hub["id"]] = (center_x, center_y, box_w, box_h)
        others = modules[1:]
        radius_x = 320.0
        radius_y = 220.0
        for idx, node in enumerate(others):
            angle = (2 * math.pi * idx) / max(1, len(others))
            x = center_x + radius_x * math.cos(angle)
            y = center_y + radius_y * math.sin(angle)
            positions[node["id"]] = (x, y, box_w, box_h)
        return positions, width, height

    # fallback
    for idx, node in enumerate(nodes):
        positions[node["id"]] = (60.0, 60.0 + idx * 110.0, box_w, box_h)
    return positions, 900.0, 120.0 + len(nodes) * 110.0


def derive_output_path(source: str) -> Path:
    if source == "stdin":
        return Path("diagram.drawio")
    source_path = Path(source)
    if source_path.suffix.lower() in {".md", ".markdown", ".yaml", ".yml"}:
        return source_path.with_suffix(".drawio")
    return Path(f"{source_path}.drawio")


def add_cell(root_element: ET.Element, **attrs) -> ET.Element:
    return ET.SubElement(root_element, "mxCell", {k: str(v) for k, v in attrs.items()})


def build_xml(spec: dict) -> ET.ElementTree:
    nodes = spec.get("nodes", [])
    edges = spec.get("edges", [])
    groups = spec.get("groups", [])
    title = spec.get("title", "Diagram")

    node_map = {node["id"]: node for node in nodes}
    positions, width, height = layout_nodes(spec)

    mxfile = ET.Element("mxfile", host="app.diagrams.net")
    diagram = ET.SubElement(mxfile, "diagram", id=str(uuid.uuid4())[:8], name="Page-1")
    model = ET.SubElement(
        diagram,
        "mxGraphModel",
        dx="1386",
        dy="791",
        grid="1",
        gridSize="10",
        guides="1",
        tooltips="1",
        connect="1",
        arrows="1",
        fold="1",
        page="1",
        pageScale="1",
        pageWidth=str(max(850, int(width + 120))),
        pageHeight=str(max(1100, int(height + 120))),
        math="0",
        shadow="0",
    )
    root = ET.SubElement(model, "root")
    add_cell(root, id="0")
    add_cell(root, id="1", parent="0")

    # Diagram title
    title_id = "title"
    title_cell = add_cell(
        root,
        id=title_id,
        value=html.escape(title),
        style="text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;fontStyle=1;fontSize=18;",
        vertex="1",
        parent="1",
    )
    ET.SubElement(title_cell, "mxGeometry", {"x": "40", "y": "10", "width": "800", "height": "30", "as": "geometry"})

    # Nodes
    node_cell_ids: dict[str, str] = {}
    for index, node in enumerate(nodes, start=2):
        node_id = node["id"]
        cell_id = f"n{index}"
        node_cell_ids[node_id] = cell_id
        x, y, w, h = positions[node_id]
        style = NODE_STYLES.get(node.get("type", "module"), NODE_STYLES["module"])
        cell = add_cell(
            root,
            id=cell_id,
            value=html.escape(str(node.get("label", node_id))),
            style=style,
            vertex="1",
            parent="1",
        )
        ET.SubElement(
            cell,
            "mxGeometry",
            {
                "x": str(round(x, 2)),
                "y": str(round(y, 2)),
                "width": str(round(w, 2)),
                "height": str(round(h, 2)),
                "as": "geometry",
            },
        )

    # Group boxes behind nodes
    for gidx, group in enumerate(groups, start=1):
        members = [m for m in group.get("members", []) if m in positions]
        if not members:
            continue
        xs = [positions[m][0] for m in members]
        ys = [positions[m][1] for m in members]
        ws = [positions[m][2] for m in members]
        hs = [positions[m][3] for m in members]
        gx = min(xs) - 25
        gy = min(ys) - 35
        gw = max(x + w for x, w in zip(xs, ws)) - gx + 25
        gh = max(y + h for y, h in zip(ys, hs)) - gy + 25
        gcell = add_cell(
            root,
            id=f"g{gidx}",
            value=html.escape(str(group.get("label", f"Group {gidx}"))),
            style=GROUP_STYLE,
            vertex="1",
            parent="1",
        )
        ET.SubElement(
            gcell,
            "mxGeometry",
            {
                "x": str(round(gx, 2)),
                "y": str(round(gy, 2)),
                "width": str(round(gw, 2)),
                "height": str(round(gh, 2)),
                "as": "geometry",
            },
        )

    # Edges
    for eidx, edge in enumerate(edges, start=1):
        src = edge.get("from")
        dst = edge.get("to")
        if src not in node_cell_ids or dst not in node_cell_ids:
            raise ValueError(f"Edge references missing node: {src} -> {dst}")
        ecell = add_cell(
            root,
            id=f"e{eidx}",
            value=html.escape(str(edge.get("label", ""))),
            style=EDGE_STYLE,
            edge="1",
            parent="1",
            source=node_cell_ids[src],
            target=node_cell_ids[dst],
        )
        ET.SubElement(ecell, "mxGeometry", {"relative": "1", "as": "geometry"})

    return ET.ElementTree(mxfile)


def indent(elem: ET.Element, level: int = 0) -> None:
    i = "\n" + level * "  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        for child in elem:
            indent(child, level + 1)
        if not child.tail or not child.tail.strip():
            child.tail = i
    if level and (not elem.tail or not elem.tail.strip()):
        elem.tail = i


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert a diagram spec into an editable .drawio XML file.")
    parser.add_argument("source", help="Path to a YAML spec file, a Markdown file, or '-' for stdin.")
    parser.add_argument("-o", "--output", help="Output .drawio file path.")
    parser.add_argument("--from-markdown", action="store_true", help="Force Markdown mode and extract the first fenced YAML block.")
    parser.add_argument("--from-yaml", action="store_true", help="Force raw YAML mode even if the input file ends with .md.")
    args = parser.parse_args()

    if args.from_markdown and args.from_yaml:
        parser.error("Choose only one of --from-markdown or --from-yaml.")
    from_markdown = True if args.from_markdown else False if args.from_yaml else None

    try:
        spec, source_name = read_spec(args.source, from_markdown)
        tree = build_xml(spec)
    except (FileNotFoundError, ValueError, yaml.YAMLError) as exc:
        print(f"[spec_to_drawio] {exc}", file=sys.stderr)
        return 1

    output_path = Path(args.output) if args.output else derive_output_path(source_name)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    indent(tree.getroot())
    tree.write(output_path, encoding="utf-8", xml_declaration=True)
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
