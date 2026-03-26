#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
from collections import defaultdict, deque
from pathlib import Path

import yaml
from PIL import Image, ImageDraw, ImageFont


WIDTH = 1640
HEIGHT = 920
BG = "#0F172A"
PANEL = "#FFFFFF"
PANEL_ALT = "#F8FAFC"
TEXT = "#111827"
SUBTLE = "#64748B"
ACCENT = "#38BDF8"

NODE_COLORS = {
    "input": ("#DAE8FC", "#6C8EBF"),
    "module": ("#FFF2CC", "#D6B656"),
    "output": ("#D5E8D4", "#82B366"),
    "storage": ("#E1D5E7", "#9673A6"),
    "decision": ("#F8CECC", "#B85450"),
    "group-anchor": ("#F5F5F5", "#666666"),
}


def load_font(size: int):
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/SFNS.ttf",
        "/Library/Fonts/Arial.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


FONT_TITLE = load_font(48)
FONT_SUB = load_font(22)
FONT_NODE = load_font(18)
FONT_GROUP = load_font(16)


def topological_levels(nodes: list[dict], edges: list[dict]) -> dict[str, int]:
    node_ids = [node["id"] for node in nodes]
    indeg = {node_id: 0 for node_id in node_ids}
    outgoing: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        src = edge.get("from")
        dst = edge.get("to")
        if src in indeg and dst in indeg:
            outgoing[src].append(dst)
            indeg[dst] += 1

    q = deque([node_id for node_id, degree in indeg.items() if degree == 0])
    levels = {node_id: 0 for node_id in node_ids}
    visited: set[str] = set()
    while q or len(visited) < len(node_ids):
        if not q:
            remaining = [node_id for node_id in node_ids if node_id not in visited]
            if not remaining:
                break
            q.append(remaining[0])
        current = q.popleft()
        if current in visited:
            continue
        visited.add(current)
        for nxt in outgoing[current]:
            levels[nxt] = max(levels[nxt], levels[current] + 1)
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                q.append(nxt)
    return levels


def layout_nodes(spec: dict) -> dict[str, tuple[float, float, float, float]]:
    nodes = spec.get("nodes", [])
    edges = spec.get("edges", [])
    box_w = 180.0
    box_h = 78.0
    hgap = 74.0
    vgap = 42.0
    margin_x = 48.0
    margin_y = 54.0

    levels = topological_levels(nodes, edges)
    cols: dict[int, list[dict]] = defaultdict(list)
    for node in nodes:
        cols[levels.get(node["id"], 0)].append(node)

    positions: dict[str, tuple[float, float, float, float]] = {}
    max_height = 0.0
    for members in cols.values():
        col_height = len(members) * box_h + max(0, len(members) - 1) * vgap
        max_height = max(max_height, col_height)

    for col_idx, members in cols.items():
        start_x = margin_x + col_idx * (box_w + hgap)
        col_height = len(members) * box_h + max(0, len(members) - 1) * vgap
        start_y = margin_y + max(0.0, (max_height - col_height) / 2.0)
        for row_idx, node in enumerate(members):
            positions[node["id"]] = (start_x, start_y + row_idx * (box_h + vgap), box_w, box_h)
    return positions


def draw_centered_text(draw: ImageDraw.ImageDraw, box, text: str, font, fill) -> None:
    x0, y0, x1, y1 = box
    bbox = draw.multiline_textbbox((0, 0), text, font=font, spacing=4, align="center")
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    draw.multiline_text(
        ((x0 + x1 - text_w) / 2, (y0 + y1 - text_h) / 2),
        text,
        font=font,
        fill=fill,
        spacing=4,
        align="center",
    )


def wrap_label(text: str, max_chars: int) -> str:
    words = str(text).split()
    if not words:
        return str(text)
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if len(candidate) <= max_chars:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return "\n".join(lines[:3])


def render_structure_panel(spec: dict, width: int, height: int) -> Image.Image:
    panel = Image.new("RGB", (width, height), PANEL)
    draw = ImageDraw.Draw(panel)
    raw_positions = layout_nodes(spec)
    groups = spec.get("groups", [])
    node_map = {node["id"]: node for node in spec.get("nodes", [])}

    if not raw_positions:
        return panel

    min_x = min(pos[0] for pos in raw_positions.values())
    min_y = min(pos[1] for pos in raw_positions.values())
    max_x = max(pos[0] + pos[2] for pos in raw_positions.values())
    max_y = max(pos[1] + pos[3] for pos in raw_positions.values())
    avail_w = width - 44
    avail_h = height - 44
    scale = min(avail_w / max(1.0, max_x - min_x), avail_h / max(1.0, max_y - min_y))
    scale = min(scale, 1.0)

    positions: dict[str, tuple[float, float, float, float]] = {}
    for node_id, (x, y, w, h) in raw_positions.items():
        positions[node_id] = (
            22 + (x - min_x) * scale,
            22 + (y - min_y) * scale,
            w * scale,
            h * scale,
        )

    for group in groups:
        members = [member for member in group.get("members", []) if member in positions]
        if not members:
            continue
        xs = [positions[member][0] for member in members]
        ys = [positions[member][1] for member in members]
        ws = [positions[member][2] for member in members]
        hs = [positions[member][3] for member in members]
        left = min(xs) - 18
        top = min(ys) - 30
        right = max(x + w for x, w in zip(xs, ws)) + 18
        bottom = max(y + h for y, h in zip(ys, hs)) + 20
        draw.rounded_rectangle((left, top, right, bottom), radius=max(10, int(18 * scale)), outline="#CBD5E1", width=2)
        draw.text((left + 12, top + 8), str(group.get("label", "Group")), font=FONT_GROUP, fill=SUBTLE)

    for edge in spec.get("edges", []):
        src = positions.get(edge.get("from"))
        dst = positions.get(edge.get("to"))
        if not src or not dst:
            continue
        sx = src[0] + src[2]
        sy = src[1] + src[3] / 2
        dx = dst[0]
        dy = dst[1] + dst[3] / 2
        mid_x = (sx + dx) / 2
        draw.line((sx, sy, mid_x, sy, mid_x, dy, dx, dy), fill="#94A3B8", width=3)
        draw.polygon([(dx, dy), (dx - 10, dy - 5), (dx - 10, dy + 5)], fill="#94A3B8")

    for node_id, (x, y, w, h) in positions.items():
        node = node_map[node_id]
        fill, stroke = NODE_COLORS.get(node.get("type", "module"), NODE_COLORS["module"])
        draw.rounded_rectangle((x, y, x + w, y + h), radius=max(10, int(16 * scale)), fill=fill, outline=stroke, width=3)
        node_font = FONT_NODE if scale >= 0.9 else load_font(16 if scale >= 0.72 else 14)
        max_chars = max(10, int(w / 10))
        draw_centered_text(draw, (x + 10, y + 8, x + w - 10, y + h - 8), wrap_label(str(node.get("label", node_id)), max_chars), node_font, TEXT)

    return panel


def render_preview(drawio_spec: dict, plot_image_path: Path, output_path: Path) -> None:
    canvas = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(canvas)

    draw.text((68, 54), drawio_spec.get("title", "Hybrid Figure"), font=FONT_TITLE, fill="#F8FAFC")
    draw.text((70, 118), "Hybrid backend: editable structure plus quantitative panel", font=FONT_SUB, fill="#94A3B8")
    draw.rounded_rectangle((68, 162, 264, 198), radius=18, fill=ACCENT)
    draw.text((88, 168), "drawio + plot + preview", font=FONT_GROUP, fill="#083344")

    left_box = (56, 238, 920, 842)
    right_box = (956, 238, 1584, 842)
    draw.rounded_rectangle(left_box, radius=24, fill=PANEL_ALT)
    draw.rounded_rectangle(right_box, radius=24, fill=PANEL_ALT)
    draw.text((78, 254), "Editable Structure", font=FONT_SUB, fill=TEXT)
    draw.text((978, 254), "Quantitative Panel", font=FONT_SUB, fill=TEXT)

    structure = render_structure_panel(drawio_spec, left_box[2] - left_box[0] - 32, left_box[3] - left_box[1] - 70)
    canvas.paste(structure, (left_box[0] + 16, left_box[1] + 52))

    plot = Image.open(plot_image_path).convert("RGB")
    plot.thumbnail((right_box[2] - right_box[0] - 24, right_box[3] - right_box[1] - 80), Image.Resampling.LANCZOS)
    plot_x = right_box[0] + (right_box[2] - right_box[0] - plot.width) // 2
    plot_y = right_box[1] + 54
    canvas.paste(plot, (plot_x, plot_y))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a hybrid figure preview from drawio spec and plot image.")
    parser.add_argument("--drawio-spec", required=True)
    parser.add_argument("--plot-image", required=True)
    parser.add_argument("-o", "--output", required=True)
    args = parser.parse_args()

    drawio_spec = yaml.safe_load(Path(args.drawio_spec).read_text(encoding="utf-8"))
    render_preview(drawio_spec, Path(args.plot_image), Path(args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
