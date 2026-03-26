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


def axis_bounds(values: list[float]) -> tuple[float, float]:
    if not values:
        return 0.0, 1.0
    minimum = min(values)
    maximum = max(values)
    if minimum >= 0:
        minimum = 0.0
    span = maximum - minimum
    if span <= 0:
        span = abs(maximum) if maximum else 1.0
    padding = span * 0.12
    upper = maximum + padding
    lower = minimum - (padding * 0.35 if minimum < 0 else 0.0)
    if upper == lower:
        upper = lower + 1.0
    return lower, upper


def build_svg(spec: dict) -> str:
    width = 1200
    height = 760
    left = 110
    right = 60
    top = 96
    bottom = 200 if spec.get("rotate_ticks") else 150
    plot_w = width - left - right
    plot_h = height - top - bottom

    categories = spec.get("categories", [])
    series = spec.get("series", [])
    title = spec.get("title", "Scientific Plot")
    x_label = spec.get("x_label", "")
    y_label = spec.get("y_label", "Value")
    chart_type = spec.get("chart_type", "grouped-bar")
    tick_indices = spec.get("tick_indices") or list(range(len(categories)))
    tick_labels = spec.get("tick_labels") or [str(categories[idx]) for idx in tick_indices]
    rotate_ticks = bool(spec.get("rotate_ticks", False))
    values = [value for item in series for value in item.get("values", []) if value is not None]
    ymin, ymax = axis_bounds(values)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#f7f8fb"/>',
        '<rect x="32" y="32" width="1136" height="696" rx="26" fill="#ffffff"/>',
        f'<text x="64" y="86" font-family="Helvetica, Arial, sans-serif" font-size="30" font-weight="700" text-anchor="start" fill="#111827">{esc(title)}</text>',
    ]

    def y_to_px(value: float) -> float:
        return top + plot_h - (value - ymin) / (ymax - ymin) * plot_h

    baseline_value = 0.0 if ymin < 0 < ymax else ymin
    baseline_y = y_to_px(baseline_value)

    for tick in range(6):
        frac = tick / 5
        value = ymin + (ymax - ymin) * frac
        y = top + plot_h - plot_h * frac
        parts.append(f'<line x1="{left}" y1="{y:.2f}" x2="{left + plot_w}" y2="{y:.2f}" stroke="#e2e8f0" stroke-width="1"/>')
        parts.append(f'<text x="{left - 14}" y="{y + 5:.2f}" font-family="Helvetica, Arial, sans-serif" font-size="14" text-anchor="end" fill="#4a5568">{esc(fmt(value))}</text>')

    parts.append(f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}" stroke="#1a202c" stroke-width="2"/>')
    parts.append(f'<line x1="{left}" y1="{baseline_y:.2f}" x2="{left + plot_w}" y2="{baseline_y:.2f}" stroke="#1a202c" stroke-width="2"/>')

    if chart_type in {"line", "scatter"}:
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
                y = y_to_px(value)
                points.append((x, y))
            if chart_type == "line" and len(points) > 1:
                point_str = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
                parts.append(f'<polyline fill="none" stroke="{item["color"]}" stroke-width="3" points="{point_str}"/>')
            for x, y in points:
                parts.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="4.5" fill="{item["color"]}" stroke="#ffffff" stroke-width="1.5"/>')
        tick_x = x_pos
    elif chart_type == "stacked-bar":
        group_count = max(1, len(categories))
        step = plot_w / group_count
        group_width = step * 0.64
        for cat_idx, _label in enumerate(categories):
            left_edge = left + step * cat_idx + (step - group_width) / 2
            acc = 0.0
            for item in series:
                value = item["values"][cat_idx]
                top_y = y_to_px(acc + value)
                bottom_y = y_to_px(acc)
                y = min(top_y, bottom_y)
                height_px = abs(bottom_y - top_y)
                parts.append(
                    f'<rect x="{left_edge:.2f}" y="{y:.2f}" width="{group_width:.2f}" height="{height_px:.2f}" '
                    f'rx="4" fill="{item["color"]}"/>'
                )
                acc += value

        def tick_x(index: int) -> float:
            return left + step * index + step / 2
    else:
        group_count = max(1, len(categories))
        series_count = max(1, len(series))
        step = plot_w / group_count
        group_width = step * 0.72
        bar_width = group_width / series_count * 0.82 if series_count else group_width

        for cat_idx, _label in enumerate(categories):
            group_left = left + step * cat_idx + (step - group_width) / 2
            for series_idx, item in enumerate(series):
                value = item["values"][cat_idx]
                bar_left = group_left + series_idx * (group_width / series_count)
                value_y = y_to_px(value)
                bar_top = min(value_y, baseline_y)
                bar_height = abs(baseline_y - value_y)
                parts.append(
                    f'<rect x="{bar_left:.2f}" y="{bar_top:.2f}" width="{bar_width:.2f}" height="{bar_height:.2f}" '
                    f'rx="4" fill="{item["color"]}"/>'
                )

        def tick_x(index: int) -> float:
            return left + step * index + step / 2

    for index, label in zip(tick_indices, tick_labels):
        x = tick_x(index)
        parts.append(f'<line x1="{x:.2f}" y1="{baseline_y:.2f}" x2="{x:.2f}" y2="{baseline_y + 6:.2f}" stroke="#9ca3af" stroke-width="1"/>')
        if rotate_ticks:
            parts.append(
                f'<g transform="translate({x:.2f},{top + plot_h + 28}) rotate(35)">'
                f'<text font-family="Helvetica, Arial, sans-serif" font-size="14" text-anchor="start" fill="#6b7280">{esc(label)}</text>'
                "</g>"
            )
        else:
            parts.append(f'<text x="{x:.2f}" y="{top + plot_h + 30}" font-family="Helvetica, Arial, sans-serif" font-size="14" text-anchor="middle" fill="#6b7280">{esc(label)}</text>')

    legend_x = width - right - 240
    legend_y = 116
    for idx, item in enumerate(series):
        y = legend_y + idx * 24
        parts.append(f'<rect x="{legend_x}" y="{y - 11}" width="16" height="16" rx="3" fill="{item["color"]}"/>')
        parts.append(f'<text x="{legend_x + 24}" y="{y + 2}" font-family="Helvetica, Arial, sans-serif" font-size="14" fill="#2d3748">{esc(item["name"])}</text>')

    if chart_type in {"line", "scatter"}:
        for annotation in spec.get("annotations", [])[:4]:
            series_name = annotation.get("series")
            item = next((candidate for candidate in series if candidate.get("name") == series_name), None)
            if item is None:
                continue
            idx = annotation.get("index", 0)
            x = tick_x(idx)
            y = y_to_px(item["values"][idx])
            label = annotation.get("label") or f"{annotation.get('type', 'peak')} {fmt(annotation.get('value', 0.0))}"
            box_x = min(max(x + 10, left + 8), left + plot_w - 110)
            box_y = y - 34 if y > top + 52 else y + 12
            parts.append(f'<rect x="{box_x:.2f}" y="{box_y:.2f}" width="100" height="26" rx="8" fill="#111827"/>')
            parts.append(f'<text x="{box_x + 50:.2f}" y="{box_y + 17:.2f}" font-family="Helvetica, Arial, sans-serif" font-size="14" text-anchor="middle" fill="#ffffff">{esc(label)}</text>')

    parts.append(
        f'<text x="{left + plot_w / 2}" y="{height - 48}" font-family="Helvetica, Arial, sans-serif" font-size="16" text-anchor="middle" fill="#6b7280">{esc(x_label)}</text>'
    )
    parts.append(
        f'<g transform="translate(34,{top + plot_h / 2}) rotate(-90)">'
        f'<text font-family="Helvetica, Arial, sans-serif" font-size="16" text-anchor="middle" fill="#6b7280">{esc(y_label)}</text>'
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
