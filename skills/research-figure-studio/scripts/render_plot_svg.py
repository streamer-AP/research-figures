#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import html
import math
import sys
from pathlib import Path

import yaml


def esc(text: str) -> str:
    return html.escape(str(text), quote=True)


def fmt(value: float) -> str:
    return f"{value:.3f}".rstrip("0").rstrip(".")


def axis_max(values: list[float]) -> float:
    maximum = max(values) if values else 1.0
    if maximum <= 0:
        return 1.0
    raw = maximum * 1.1
    magnitude = 10 ** math.floor(math.log10(raw))
    normalized = raw / magnitude
    if normalized <= 1:
        nice = 1
    elif normalized <= 2:
        nice = 2
    elif normalized <= 5:
        nice = 5
    else:
        nice = 10
    return nice * magnitude


def build_svg(spec: dict) -> str:
    width = 1120
    height = 720
    left = 100
    right = 60
    top = 90
    bottom = 180
    plot_w = width - left - right
    plot_h = height - top - bottom

    categories = spec.get("categories", [])
    series = spec.get("series", [])
    title = spec.get("title", "Scientific Plot")
    x_label = spec.get("x_label", "")
    y_label = spec.get("y_label", "Value")
    chart_type = spec.get("chart_type", "grouped-bar")
    values = [value for item in series for value in item.get("values", []) if value is not None]
    ymax = axis_max(values)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="{width / 2}" y="44" font-family="Helvetica, Arial, sans-serif" font-size="28" font-weight="700" text-anchor="middle" fill="#1a202c">{esc(title)}</text>',
    ]

    for tick in range(6):
        value = ymax * tick / 5
        y = top + plot_h - plot_h * tick / 5
        parts.append(f'<line x1="{left}" y1="{y:.2f}" x2="{left + plot_w}" y2="{y:.2f}" stroke="#e2e8f0" stroke-width="1"/>')
        parts.append(f'<text x="{left - 14}" y="{y + 5:.2f}" font-family="Helvetica, Arial, sans-serif" font-size="14" text-anchor="end" fill="#4a5568">{esc(fmt(value))}</text>')

    parts.append(f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}" stroke="#1a202c" stroke-width="2"/>')
    parts.append(f'<line x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" y2="{top + plot_h}" stroke="#1a202c" stroke-width="2"/>')

    if chart_type == "line":
        numeric_x = all(_is_number(label) for label in categories)
        if numeric_x and len(categories) > 1:
            x_vals = [float(label) for label in categories]
            xmin = min(x_vals)
            xmax = max(x_vals)

            def x_pos(index: int) -> float:
                if xmax == xmin:
                    return left + plot_w / 2
                return left + (x_vals[index] - xmin) / (xmax - xmin) * plot_w
        else:
            step = plot_w / max(1, len(categories) - 1)

            def x_pos(index: int) -> float:
                return left + step * index

        for item in series:
            points = []
            for idx, value in enumerate(item["values"]):
                x = x_pos(idx)
                y = top + plot_h - (value / ymax) * plot_h
                points.append((x, y))
            point_str = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
            parts.append(f'<polyline fill="none" stroke="{item["color"]}" stroke-width="3" points="{point_str}"/>')
            for x, y in points:
                parts.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="4.5" fill="{item["color"]}" stroke="#ffffff" stroke-width="1.5"/>')

        for idx, label in enumerate(categories):
            x = x_pos(idx)
            parts.append(f'<text x="{x:.2f}" y="{top + plot_h + 28}" font-family="Helvetica, Arial, sans-serif" font-size="14" text-anchor="middle" fill="#2d3748">{esc(label)}</text>')
    else:
        group_count = max(1, len(categories))
        series_count = max(1, len(series))
        step = plot_w / group_count
        group_width = step * 0.72
        bar_width = group_width / series_count * 0.82
        rotate_labels = any(len(str(label)) > 12 for label in categories) or len(categories) > 6

        for cat_idx, label in enumerate(categories):
            group_left = left + step * cat_idx + (step - group_width) / 2
            for series_idx, item in enumerate(series):
                value = item["values"][cat_idx]
                bar_left = group_left + series_idx * (group_width / series_count)
                bar_height = (value / ymax) * plot_h
                bar_top = top + plot_h - bar_height
                parts.append(
                    f'<rect x="{bar_left:.2f}" y="{bar_top:.2f}" width="{bar_width:.2f}" height="{bar_height:.2f}" '
                    f'rx="2" fill="{item["color"]}"/>'
                )
            anchor_x = left + step * cat_idx + step / 2
            if rotate_labels:
                parts.append(
                    f'<g transform="translate({anchor_x:.2f},{top + plot_h + 28}) rotate(35)">'
                    f'<text font-family="Helvetica, Arial, sans-serif" font-size="14" text-anchor="start" fill="#2d3748">{esc(label)}</text>'
                    "</g>"
                )
            else:
                parts.append(f'<text x="{anchor_x:.2f}" y="{top + plot_h + 28}" font-family="Helvetica, Arial, sans-serif" font-size="14" text-anchor="middle" fill="#2d3748">{esc(label)}</text>')

    legend_x = width - right - 240
    legend_y = 72
    for idx, item in enumerate(series):
        y = legend_y + idx * 24
        parts.append(f'<rect x="{legend_x}" y="{y - 11}" width="16" height="16" rx="3" fill="{item["color"]}"/>')
        parts.append(f'<text x="{legend_x + 24}" y="{y + 2}" font-family="Helvetica, Arial, sans-serif" font-size="14" fill="#2d3748">{esc(item["name"])}</text>')

    parts.append(
        f'<text x="{left + plot_w / 2}" y="{height - 44}" font-family="Helvetica, Arial, sans-serif" font-size="16" text-anchor="middle" fill="#4a5568">{esc(x_label)}</text>'
    )
    parts.append(
        f'<g transform="translate(28,{top + plot_h / 2}) rotate(-90)">'
        f'<text font-family="Helvetica, Arial, sans-serif" font-size="16" text-anchor="middle" fill="#4a5568">{esc(y_label)}</text>'
        "</g>"
    )
    parts.append("</svg>")
    return "\n".join(parts)


def _is_number(value: str) -> bool:
    try:
        float(str(value))
        return True
    except ValueError:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a YAML plot spec to SVG.")
    parser.add_argument("spec")
    parser.add_argument("-o", "--output")
    args = parser.parse_args()

    spec = yaml.safe_load(Path(args.spec).read_text(encoding="utf-8"))
    payload = build_svg(spec)
    if args.output:
        Path(args.output).write_text(payload, encoding="utf-8")
    else:
        sys.stdout.write(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
