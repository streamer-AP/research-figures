#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import math
from pathlib import Path

import yaml
from PIL import Image, ImageDraw, ImageFont


WIDTH = 1280
HEIGHT = 820
MARGIN_LEFT = 120
MARGIN_RIGHT = 70
MARGIN_TOP = 120
MARGIN_BOTTOM = 190
BG = "#F7F8FB"
CARD = "#FFFFFF"
GRID = "#E5E7EB"
AXIS = "#111827"
SUBTLE = "#6B7280"


def load_font(size: int, bold: bool = False):
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


FONT_TITLE = load_font(34, bold=True)
FONT_LABEL = load_font(18)
FONT_TICK = load_font(14)
FONT_LEGEND = load_font(16)
FONT_ANNOT = load_font(15)


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


def draw_text_center(draw, xy, text, font, fill):
    bbox = draw.textbbox((0, 0), text, font=font)
    x = xy[0] - (bbox[2] - bbox[0]) / 2
    y = xy[1] - (bbox[3] - bbox[1]) / 2
    draw.text((x, y), text, font=font, fill=fill)


def render(spec: dict, output_path: Path) -> None:
    image = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(image)

    plot_x0 = MARGIN_LEFT
    plot_y0 = MARGIN_TOP
    plot_x1 = WIDTH - MARGIN_RIGHT
    plot_y1 = HEIGHT - MARGIN_BOTTOM
    plot_w = plot_x1 - plot_x0
    plot_h = plot_y1 - plot_y0

    draw.rounded_rectangle((40, 40, WIDTH - 40, HEIGHT - 40), radius=28, fill=CARD)
    draw.text((70, 65), spec.get("title", "Scientific Plot"), font=FONT_TITLE, fill=AXIS)

    categories = spec.get("categories", [])
    series = spec.get("series", [])
    chart_type = spec.get("chart_type", "grouped-bar")
    x_label = spec.get("x_label", "")
    y_label = spec.get("y_label", "")
    tick_indices = spec.get("tick_indices") or list(range(len(categories)))
    tick_labels = spec.get("tick_labels") or [str(categories[idx]) for idx in tick_indices]
    rotate_ticks = bool(spec.get("rotate_ticks", False))
    all_values = [value for item in series for value in item.get("values", []) if value is not None]
    ymin, ymax = axis_bounds(all_values)
    baseline_value = 0.0 if ymin < 0 < ymax else ymin

    for tick in range(6):
        frac = tick / 5
        y = plot_y1 - plot_h * frac
        value = ymin + (ymax - ymin) * frac
        draw.line((plot_x0, y, plot_x1, y), fill=GRID, width=1)
        draw.text((plot_x0 - 62, y - 10), f"{value:.2f}".rstrip("0").rstrip("."), font=FONT_TICK, fill=SUBTLE)

    draw.line((plot_x0, plot_y0, plot_x0, plot_y1), fill=AXIS, width=2)
    baseline_y = plot_y1 - (baseline_value - ymin) / (ymax - ymin) * plot_h
    draw.line((plot_x0, baseline_y, plot_x1, baseline_y), fill=AXIS, width=2)

    def y_to_px(value: float) -> float:
        return plot_y1 - (value - ymin) / (ymax - ymin) * plot_h

    if chart_type in {"line", "scatter"}:
        numeric_x = all(_is_number(label) for label in categories)
        if numeric_x and len(categories) > 1:
            x_vals = [float(label) for label in categories]
            xmin = min(x_vals)
            xmax = max(x_vals)

            def x_pos(idx: int) -> float:
                if xmax == xmin:
                    return plot_x0 + plot_w / 2
                return plot_x0 + (x_vals[idx] - xmin) / (xmax - xmin) * plot_w
        else:
            step = plot_w / max(1, len(categories) - 1)

            def x_pos(idx: int) -> float:
                return plot_x0 + step * idx

        for item in series:
            points = [(x_pos(idx), y_to_px(value)) for idx, value in enumerate(item["values"])]
            if chart_type == "line" and len(points) > 1:
                draw.line(points, fill=item["color"], width=4, joint="curve")
            for x, y in points:
                draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill=item["color"], outline="white", width=2)
        tick_anchor = x_pos
    elif chart_type == "stacked-bar":
        step = plot_w / max(1, len(categories))
        group_width = step * 0.62
        for cat_idx, label in enumerate(categories):
            left = plot_x0 + step * cat_idx + (step - group_width) / 2
            acc = 0.0
            for item in series:
                value = item["values"][cat_idx]
                top = y_to_px(acc + value)
                bottom = y_to_px(acc)
                draw.rounded_rectangle((left, min(top, bottom), left + group_width, max(top, bottom)), radius=4, fill=item["color"])
                acc += value

        def tick_anchor(idx: int) -> float:
            return plot_x0 + step * idx + step / 2
    else:
        step = plot_w / max(1, len(categories))
        group_width = step * 0.68
        series_count = max(1, len(series))
        bar_span = group_width / series_count
        for cat_idx, label in enumerate(categories):
            group_left = plot_x0 + step * cat_idx + (step - group_width) / 2
            for s_idx, item in enumerate(series):
                value = item["values"][cat_idx]
                bar_left = group_left + s_idx * bar_span
                bar_right = bar_left + bar_span * 0.82
                bar_value_y = y_to_px(value)
                draw.rounded_rectangle((bar_left, min(bar_value_y, baseline_y), bar_right, max(bar_value_y, baseline_y)), radius=4, fill=item["color"])

        def tick_anchor(idx: int) -> float:
            return plot_x0 + step * idx + step / 2

    for idx, label in zip(tick_indices, tick_labels):
        anchor = tick_anchor(idx)
        draw.line((anchor, baseline_y, anchor, baseline_y + 6), fill="#9CA3AF", width=1)
        if rotate_ticks:
            tmp = Image.new("RGBA", (240, 40), (255, 255, 255, 0))
            tmp_draw = ImageDraw.Draw(tmp)
            tmp_draw.text((0, 0), str(label), font=FONT_TICK, fill=SUBTLE)
            rotated = tmp.rotate(35, expand=1, resample=Image.Resampling.BICUBIC)
            image.paste(rotated, (int(anchor - 10), int(plot_y1 + 10)), rotated)
        else:
            draw_text_center(draw, (anchor, plot_y1 + 28), str(label), FONT_TICK, SUBTLE)

    legend_x = WIDTH - 300
    legend_y = 120
    for idx, item in enumerate(series):
        y = legend_y + idx * 30
        draw.rounded_rectangle((legend_x, y, legend_x + 16, y + 16), radius=4, fill=item["color"])
        draw.text((legend_x + 26, y - 2), item["name"], font=FONT_LEGEND, fill=AXIS)

    for annotation in spec.get("annotations", [])[:4]:
        series_name = annotation["series"]
        idx = annotation["index"]
        item = next((candidate for candidate in series if candidate["name"] == series_name), None)
        if item is None:
            continue
        value = item["values"][idx]
        label = annotation.get("label") or f"{annotation.get('type', 'peak')} {value:.2f}".rstrip("0").rstrip(".")
        if chart_type in {"line", "scatter"}:
            if all(_is_number(label) for label in categories) and len(categories) > 1:
                x_vals = [float(label) for label in categories]
                xmin = min(x_vals)
                xmax = max(x_vals)
                x = plot_x0 + (x_vals[idx] - xmin) / (xmax - xmin) * plot_w if xmax != xmin else plot_x0 + plot_w / 2
            else:
                x = plot_x0 + plot_w / max(1, len(categories) - 1) * idx if len(categories) > 1 else plot_x0 + plot_w / 2
            y = y_to_px(value)
            box_y = y - 34 if y > plot_y0 + 52 else y + 12
            box_x = min(max(x + 10, plot_x0 + 8), plot_x1 - 110)
            draw.rounded_rectangle((box_x, box_y, box_x + 100, box_y + 26), radius=8, fill="#111827")
            draw.text((box_x + 10, box_y + 4), label, font=FONT_ANNOT, fill="white")

    draw_text_center(draw, (plot_x0 + plot_w / 2, HEIGHT - 80), x_label, FONT_LABEL, SUBTLE)
    y_tmp = Image.new("RGBA", (220, 40), (255, 255, 255, 0))
    y_draw = ImageDraw.Draw(y_tmp)
    y_draw.text((0, 0), y_label, font=FONT_LABEL, fill=SUBTLE)
    rotated = y_tmp.rotate(90, expand=1, resample=Image.Resampling.BICUBIC)
    image.paste(rotated, (30, int(plot_y0 + plot_h / 2 - rotated.height / 2)), rotated)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)


def _is_number(value: str) -> bool:
    try:
        float(str(value))
        return True
    except ValueError:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a YAML plot spec to PNG.")
    parser.add_argument("spec")
    parser.add_argument("-o", "--output", required=True)
    args = parser.parse_args()

    spec = yaml.safe_load(Path(args.spec).read_text(encoding="utf-8"))
    render(spec, Path(args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
