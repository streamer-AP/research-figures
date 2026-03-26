#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import html
import sys
from pathlib import Path

import yaml

from plot_render_utils import axis_bounds, axis_ticks, fmt, is_number_label, numeric_x_positions, value_to_ratio


def esc(text: str) -> str:
    return html.escape(str(text), quote=True)


def value_extent(series: list[dict]) -> list[float]:
    values: list[float] = []
    for item in series:
        errs = item.get("error_values") or []
        for idx, value in enumerate(item.get("values", [])):
            if value is None:
                continue
            values.append(value)
            error = errs[idx] if idx < len(errs) else None
            if error is not None:
                values.extend([value - error, value + error])
    return values


def build_svg(spec: dict) -> str:
    width = 1260
    height = 780
    left = 118
    right = 120 if spec.get("axis_mode") == "left-right" else 72
    top = 102
    bottom = 210 if spec.get("rotate_ticks") else 158
    plot_w = width - left - right
    plot_h = height - top - bottom

    categories = spec.get("categories", [])
    series = spec.get("series", [])
    left_series = [item for item in series if item.get("axis", "left") != "right"]
    right_series = [item for item in series if item.get("axis") == "right"]

    title = spec.get("title", "Scientific Plot")
    x_label = spec.get("x_label", "")
    y_label = spec.get("y_label", "Value")
    secondary_y_label = spec.get("secondary_y_label")
    chart_type = spec.get("chart_type", "grouped-bar")
    tick_indices = spec.get("tick_indices") or list(range(len(categories)))
    tick_labels = spec.get("tick_labels") or [str(categories[idx]) for idx in tick_indices]
    rotate_ticks = bool(spec.get("rotate_ticks", False))
    x_scale = spec.get("x_scale", "linear")
    y_scale = spec.get("y_scale", "linear")

    left_lower, left_upper = axis_bounds(value_extent(left_series or series), scale=y_scale)
    right_lower, right_upper = axis_bounds(value_extent(right_series), scale=y_scale) if right_series else (None, None)

    def y_to_px(value: float, axis: str = "left") -> float:
        lower, upper = (right_lower, right_upper) if axis == "right" and right_lower is not None else (left_lower, left_upper)
        ratio = value_to_ratio(value, lower, upper, scale=y_scale)
        return top + plot_h - ratio * plot_h

    left_baseline_value = left_lower if y_scale == "log" else (0.0 if left_lower < 0 < left_upper else left_lower)
    baseline_y = y_to_px(left_baseline_value, axis="left")

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#f7f8fb"/>',
        f'<rect x="34" y="34" width="{width - 68}" height="{height - 68}" rx="26" fill="#ffffff"/>',
        f'<text x="70" y="88" font-family="Helvetica, Arial, sans-serif" font-size="30" font-weight="700" fill="#111827">{esc(title)}</text>',
    ]

    for tick in axis_ticks(left_lower, left_upper, scale=y_scale):
        y = y_to_px(tick)
        parts.append(f'<line x1="{left}" y1="{y:.2f}" x2="{left + plot_w}" y2="{y:.2f}" stroke="#e5e7eb" stroke-width="1"/>')
        parts.append(f'<text x="{left - 16}" y="{y + 5:.2f}" font-family="Helvetica, Arial, sans-serif" font-size="14" text-anchor="end" fill="#6b7280">{esc(fmt(tick))}</text>')

    parts.append(f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}" stroke="#111827" stroke-width="2"/>')
    parts.append(f'<line x1="{left}" y1="{baseline_y:.2f}" x2="{left + plot_w}" y2="{baseline_y:.2f}" stroke="#111827" stroke-width="2"/>')

    if right_series and right_lower is not None and right_upper is not None:
        parts.append(f'<line x1="{left + plot_w}" y1="{top}" x2="{left + plot_w}" y2="{top + plot_h}" stroke="#111827" stroke-width="2"/>')
        for tick in axis_ticks(right_lower, right_upper, scale=y_scale):
            y = y_to_px(tick, axis="right")
            parts.append(f'<text x="{left + plot_w + 14}" y="{y + 5:.2f}" font-family="Helvetica, Arial, sans-serif" font-size="14" text-anchor="start" fill="#6b7280">{esc(fmt(tick))}</text>')

    if chart_type in {"line", "scatter"}:
        numeric_x = all(is_number_label(label) for label in categories)
        if numeric_x and len(categories) > 1:
            x_pos = numeric_x_positions(categories, left, plot_w, scale=x_scale)
        else:
            step = plot_w / max(1, len(categories) - 1)

            def x_pos(index: int) -> float:
                return left + step * index

        for item in series:
            axis = item.get("axis", "left")
            points = [(x_pos(idx), y_to_px(value, axis=axis)) for idx, value in enumerate(item["values"]) if value is not None]
            if chart_type == "line" and len(points) > 1:
                point_str = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
                parts.append(f'<polyline fill="none" stroke="{item["color"]}" stroke-width="3" points="{point_str}"/>')
            for idx, value in enumerate(item["values"]):
                if value is None:
                    continue
                x = x_pos(idx)
                y = y_to_px(value, axis=axis)
                error_values = item.get("error_values") or []
                error = error_values[idx] if idx < len(error_values) else None
                if error is not None:
                    y_low = y_to_px(value - error, axis=axis)
                    y_high = y_to_px(value + error, axis=axis)
                    parts.append(f'<line x1="{x:.2f}" y1="{y_low:.2f}" x2="{x:.2f}" y2="{y_high:.2f}" stroke="{item["color"]}" stroke-width="1.5"/>')
                    parts.append(f'<line x1="{x - 6:.2f}" y1="{y_low:.2f}" x2="{x + 6:.2f}" y2="{y_low:.2f}" stroke="{item["color"]}" stroke-width="1.5"/>')
                    parts.append(f'<line x1="{x - 6:.2f}" y1="{y_high:.2f}" x2="{x + 6:.2f}" y2="{y_high:.2f}" stroke="{item["color"]}" stroke-width="1.5"/>')
                parts.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="4.5" fill="{item["color"]}" stroke="#ffffff" stroke-width="1.5"/>')
        tick_x = x_pos
    elif chart_type == "stacked-bar":
        step = plot_w / max(1, len(categories))
        group_width = step * 0.64
        for cat_idx, _ in enumerate(categories):
            left_edge = left + step * cat_idx + (step - group_width) / 2
            acc = 0.0
            for item in left_series or series:
                value = item["values"][cat_idx]
                top_y = y_to_px(acc + value)
                bottom_y = y_to_px(acc)
                y = min(top_y, bottom_y)
                height_px = abs(bottom_y - top_y)
                parts.append(f'<rect x="{left_edge:.2f}" y="{y:.2f}" width="{group_width:.2f}" height="{height_px:.2f}" rx="4" fill="{item["color"]}"/>')
                acc += value

        def tick_x(index: int) -> float:
            return left + step * index + step / 2
    else:
        step = plot_w / max(1, len(categories))
        group_width = step * 0.72
        series_count = max(1, len(series))
        bar_span = group_width / series_count
        for cat_idx, _ in enumerate(categories):
            group_left = left + step * cat_idx + (step - group_width) / 2
            for s_idx, item in enumerate(series):
                value = item["values"][cat_idx]
                axis = item.get("axis", "left")
                bar_left = group_left + s_idx * bar_span
                bar_width = bar_span * 0.82
                value_y = y_to_px(value, axis=axis)
                bar_top = min(value_y, baseline_y)
                bar_height = abs(baseline_y - value_y)
                parts.append(f'<rect x="{bar_left:.2f}" y="{bar_top:.2f}" width="{bar_width:.2f}" height="{bar_height:.2f}" rx="4" fill="{item["color"]}"/>')
                error_values = item.get("error_values") or []
                error = error_values[cat_idx] if cat_idx < len(error_values) else None
                if error is not None:
                    anchor_x = bar_left + bar_width / 2
                    y_low = y_to_px(value - error, axis=axis)
                    y_high = y_to_px(value + error, axis=axis)
                    parts.append(f'<line x1="{anchor_x:.2f}" y1="{y_low:.2f}" x2="{anchor_x:.2f}" y2="{y_high:.2f}" stroke="{item["color"]}" stroke-width="1.5"/>')
                    parts.append(f'<line x1="{anchor_x - 6:.2f}" y1="{y_low:.2f}" x2="{anchor_x + 6:.2f}" y2="{y_low:.2f}" stroke="{item["color"]}" stroke-width="1.5"/>')
                    parts.append(f'<line x1="{anchor_x - 6:.2f}" y1="{y_high:.2f}" x2="{anchor_x + 6:.2f}" y2="{y_high:.2f}" stroke="{item["color"]}" stroke-width="1.5"/>')

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

    legend_x = width - right - 220
    legend_y = 116
    for idx, item in enumerate(series):
        y = legend_y + idx * 24
        axis_suffix = " (R)" if item.get("axis") == "right" else ""
        parts.append(f'<rect x="{legend_x}" y="{y - 11}" width="16" height="16" rx="3" fill="{item["color"]}"/>')
        parts.append(f'<text x="{legend_x + 24}" y="{y + 2}" font-family="Helvetica, Arial, sans-serif" font-size="14" fill="#2d3748">{esc(item["name"] + axis_suffix)}</text>')

    if chart_type in {"line", "scatter"}:
        for annotation in spec.get("annotations", [])[:4]:
            item = next((candidate for candidate in series if candidate.get("name") == annotation.get("series")), None)
            if item is None:
                continue
            idx = annotation.get("index", 0)
            x = tick_x(idx)
            y = y_to_px(item["values"][idx], axis=item.get("axis", "left"))
            label = annotation.get("label") or f"{annotation.get('type', 'peak')} {fmt(annotation.get('value', 0.0))}"
            box_x = min(max(x + 10, left + 8), left + plot_w - 110)
            box_y = y - 34 if y > top + 52 else y + 12
            parts.append(f'<rect x="{box_x:.2f}" y="{box_y:.2f}" width="100" height="26" rx="8" fill="#111827"/>')
            parts.append(f'<text x="{box_x + 50:.2f}" y="{box_y + 17:.2f}" font-family="Helvetica, Arial, sans-serif" font-size="14" text-anchor="middle" fill="#ffffff">{esc(label)}</text>')

    parts.append(f'<text x="{left + plot_w / 2}" y="{height - 48}" font-family="Helvetica, Arial, sans-serif" font-size="16" text-anchor="middle" fill="#6b7280">{esc(x_label)}</text>')
    parts.append(f'<g transform="translate(34,{top + plot_h / 2}) rotate(-90)"><text font-family="Helvetica, Arial, sans-serif" font-size="16" text-anchor="middle" fill="#6b7280">{esc(y_label)}</text></g>')
    if right_series and secondary_y_label:
        parts.append(f'<g transform="translate({width - 28},{top + plot_h / 2}) rotate(90)"><text font-family="Helvetica, Arial, sans-serif" font-size="16" text-anchor="middle" fill="#6b7280">{esc(secondary_y_label)}</text></g>')

    parts.append("</svg>")
    return "\n".join(parts)


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
