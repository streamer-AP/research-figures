#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
from pathlib import Path

import yaml
from PIL import Image, ImageDraw, ImageFont

from plot_render_utils import axis_bounds, axis_ticks, fmt, is_number_label, numeric_x_positions, value_to_ratio


WIDTH = 1320
HEIGHT = 860
MARGIN_LEFT = 120
MARGIN_RIGHT = 70
MARGIN_TOP = 120
MARGIN_BOTTOM = 190
BG = "#F7F8FB"
CARD = "#FFFFFF"
GRID = "#E5E7EB"
AXIS = "#111827"
SUBTLE = "#6B7280"


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


FONT_TITLE = load_font(34)
FONT_LABEL = load_font(18)
FONT_TICK = load_font(14)
FONT_LEGEND = load_font(16)
FONT_ANNOT = load_font(15)


def draw_text_center(draw: ImageDraw.ImageDraw, xy, text, font, fill) -> None:
    bbox = draw.textbbox((0, 0), text, font=font)
    x = xy[0] - (bbox[2] - bbox[0]) / 2
    y = xy[1] - (bbox[3] - bbox[1]) / 2
    draw.text((x, y), text, font=font, fill=fill)


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


def render(spec: dict, output_path: Path) -> None:
    image = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(image)

    right_margin = 130 if spec.get("axis_mode") == "left-right" else MARGIN_RIGHT
    plot_x0 = MARGIN_LEFT
    plot_y0 = MARGIN_TOP
    plot_x1 = WIDTH - right_margin
    plot_y1 = HEIGHT - (220 if spec.get("rotate_ticks") else MARGIN_BOTTOM)
    plot_w = plot_x1 - plot_x0
    plot_h = plot_y1 - plot_y0

    draw.rounded_rectangle((36, 36, WIDTH - 36, HEIGHT - 36), radius=28, fill=CARD)
    draw.text((70, 65), spec.get("title", "Scientific Plot"), font=FONT_TITLE, fill=AXIS)

    categories = spec.get("categories", [])
    series = spec.get("series", [])
    left_series = [item for item in series if item.get("axis", "left") != "right"]
    right_series = [item for item in series if item.get("axis") == "right"]
    chart_type = spec.get("chart_type", "grouped-bar")
    x_label = spec.get("x_label", "")
    y_label = spec.get("y_label", "")
    secondary_y_label = spec.get("secondary_y_label")
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
        return plot_y0 + plot_h - ratio * plot_h

    left_baseline_value = left_lower if y_scale == "log" else (0.0 if left_lower < 0 < left_upper else left_lower)
    baseline_y = y_to_px(left_baseline_value, axis="left")

    for tick in axis_ticks(left_lower, left_upper, scale=y_scale):
        y = y_to_px(tick)
        draw.line((plot_x0, y, plot_x1, y), fill=GRID, width=1)
        draw.text((plot_x0 - 64, y - 10), fmt(tick), font=FONT_TICK, fill=SUBTLE)

    draw.line((plot_x0, plot_y0, plot_x0, plot_y1), fill=AXIS, width=2)
    draw.line((plot_x0, baseline_y, plot_x1, baseline_y), fill=AXIS, width=2)

    if right_series and right_lower is not None and right_upper is not None:
        draw.line((plot_x1, plot_y0, plot_x1, plot_y1), fill=AXIS, width=2)
        for tick in axis_ticks(right_lower, right_upper, scale=y_scale):
            y = y_to_px(tick, axis="right")
            draw.text((plot_x1 + 14, y - 10), fmt(tick), font=FONT_TICK, fill=SUBTLE)

    if chart_type in {"line", "scatter"}:
        numeric_x = all(is_number_label(label) for label in categories)
        if numeric_x and len(categories) > 1:
            x_pos = numeric_x_positions(categories, plot_x0, plot_w, scale=x_scale)
        else:
            step = plot_w / max(1, len(categories) - 1)

            def x_pos(idx: int) -> float:
                return plot_x0 + step * idx

        for item in series:
            axis = item.get("axis", "left")
            points = [(x_pos(idx), y_to_px(value, axis=axis)) for idx, value in enumerate(item["values"]) if value is not None]
            if chart_type == "line" and len(points) > 1:
                draw.line(points, fill=item["color"], width=4, joint="curve")
            for idx, value in enumerate(item["values"]):
                if value is None:
                    continue
                x = x_pos(idx)
                y = y_to_px(value, axis=axis)
                errors = item.get("error_values") or []
                error = errors[idx] if idx < len(errors) else None
                if error is not None:
                    y_low = y_to_px(value - error, axis=axis)
                    y_high = y_to_px(value + error, axis=axis)
                    draw.line((x, y_low, x, y_high), fill=item["color"], width=2)
                    draw.line((x - 6, y_low, x + 6, y_low), fill=item["color"], width=2)
                    draw.line((x - 6, y_high, x + 6, y_high), fill=item["color"], width=2)
                draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill=item["color"], outline="white", width=2)
        tick_anchor = x_pos
    elif chart_type == "stacked-bar":
        step = plot_w / max(1, len(categories))
        group_width = step * 0.62
        for cat_idx, _ in enumerate(categories):
            left = plot_x0 + step * cat_idx + (step - group_width) / 2
            acc = 0.0
            for item in left_series or series:
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
        for cat_idx, _ in enumerate(categories):
            group_left = plot_x0 + step * cat_idx + (step - group_width) / 2
            for s_idx, item in enumerate(series):
                value = item["values"][cat_idx]
                axis = item.get("axis", "left")
                bar_left = group_left + s_idx * bar_span
                bar_right = bar_left + bar_span * 0.82
                bar_value_y = y_to_px(value, axis=axis)
                draw.rounded_rectangle((bar_left, min(bar_value_y, baseline_y), bar_right, max(bar_value_y, baseline_y)), radius=4, fill=item["color"])
                errors = item.get("error_values") or []
                error = errors[cat_idx] if cat_idx < len(errors) else None
                if error is not None:
                    anchor = (bar_left + bar_right) / 2
                    y_low = y_to_px(value - error, axis=axis)
                    y_high = y_to_px(value + error, axis=axis)
                    draw.line((anchor, y_low, anchor, y_high), fill=item["color"], width=2)
                    draw.line((anchor - 6, y_low, anchor + 6, y_low), fill=item["color"], width=2)
                    draw.line((anchor - 6, y_high, anchor + 6, y_high), fill=item["color"], width=2)

        def tick_anchor(idx: int) -> float:
            return plot_x0 + step * idx + step / 2

    for idx, label in zip(tick_indices, tick_labels):
        anchor = tick_anchor(idx)
        draw.line((anchor, baseline_y, anchor, baseline_y + 6), fill="#9CA3AF", width=1)
        if rotate_ticks:
            tmp = Image.new("RGBA", (260, 42), (255, 255, 255, 0))
            tmp_draw = ImageDraw.Draw(tmp)
            tmp_draw.text((0, 0), str(label), font=FONT_TICK, fill=SUBTLE)
            rotated = tmp.rotate(35, expand=1, resample=Image.Resampling.BICUBIC)
            image.paste(rotated, (int(anchor - 10), int(plot_y1 + 10)), rotated)
        else:
            draw_text_center(draw, (anchor, plot_y1 + 28), str(label), FONT_TICK, SUBTLE)

    legend_x = WIDTH - right_margin - 220
    legend_y = 120
    for idx, item in enumerate(series):
        y = legend_y + idx * 30
        axis_suffix = " (R)" if item.get("axis") == "right" else ""
        draw.rounded_rectangle((legend_x, y, legend_x + 16, y + 16), radius=4, fill=item["color"])
        draw.text((legend_x + 26, y - 2), item["name"] + axis_suffix, font=FONT_LEGEND, fill=AXIS)

    for annotation in spec.get("annotations", [])[:4]:
        item = next((candidate for candidate in series if candidate["name"] == annotation.get("series")), None)
        if item is None or chart_type not in {"line", "scatter"}:
            continue
        idx = annotation["index"]
        value = item["values"][idx]
        x = tick_anchor(idx)
        y = y_to_px(value, axis=item.get("axis", "left"))
        label = annotation.get("label") or f"{annotation.get('type', 'peak')} {fmt(annotation.get('value', 0.0))}"
        box_y = y - 34 if y > plot_y0 + 52 else y + 12
        box_x = min(max(x + 10, plot_x0 + 8), plot_x1 - 110)
        draw.rounded_rectangle((box_x, box_y, box_x + 100, box_y + 26), radius=8, fill="#111827")
        draw.text((box_x + 10, box_y + 4), label, font=FONT_ANNOT, fill="white")

    draw_text_center(draw, (plot_x0 + plot_w / 2, HEIGHT - 82), x_label, FONT_LABEL, SUBTLE)

    y_tmp = Image.new("RGBA", (240, 44), (255, 255, 255, 0))
    ImageDraw.Draw(y_tmp).text((0, 0), y_label, font=FONT_LABEL, fill=SUBTLE)
    y_rotated = y_tmp.rotate(90, expand=1, resample=Image.Resampling.BICUBIC)
    image.paste(y_rotated, (28, int(plot_y0 + plot_h / 2 - y_rotated.height / 2)), y_rotated)

    if right_series and secondary_y_label:
        y2_tmp = Image.new("RGBA", (240, 44), (255, 255, 255, 0))
        ImageDraw.Draw(y2_tmp).text((0, 0), secondary_y_label, font=FONT_LABEL, fill=SUBTLE)
        y2_rotated = y2_tmp.rotate(-90, expand=1, resample=Image.Resampling.BICUBIC)
        image.paste(y2_rotated, (WIDTH - 42, int(plot_y0 + plot_h / 2 - y2_rotated.height / 2)), y2_rotated)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)


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
