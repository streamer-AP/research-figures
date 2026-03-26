#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs" / "assets"
SHOWCASE = ASSETS / "showcase"

WIDTH = 1600
HEIGHT = 960
BG = "#0F172A"
CARD = "#111827"
CARD_ALT = "#0B1220"
TEXT = "#F8FAFC"
SUBTLE = "#94A3B8"
ACCENT = "#38BDF8"


def load_font(size: int, bold: bool = False):
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial Bold.ttf" if bold else "/Library/Fonts/Arial.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


FONT_TITLE = load_font(56, bold=True)
FONT_SUB = load_font(24)
FONT_CARD = load_font(22, bold=True)
FONT_META = load_font(18)


def load_image(path: Path, inset: tuple[int, int, int, int] | None = None) -> Image.Image:
    image = Image.open(path).convert("RGB")
    if inset:
        left, top, right, bottom = inset
        image = image.crop((left, top, max(left + 1, image.width - right), max(top + 1, image.height - bottom)))
    return image


def fit_crop(path: Path, width: int, height: int, inset: tuple[int, int, int, int] | None = None) -> Image.Image:
    image = load_image(path, inset=inset)
    src_w, src_h = image.size
    target_ratio = width / height
    src_ratio = src_w / src_h
    if src_ratio > target_ratio:
        new_w = int(src_h * target_ratio)
        left = (src_w - new_w) // 2
        image = image.crop((left, 0, left + new_w, src_h))
    else:
        new_h = int(src_w / target_ratio)
        top = (src_h - new_h) // 2
        image = image.crop((0, top, src_w, top + new_h))
    return image.resize((width, height), Image.Resampling.LANCZOS)


def fit_contain(
    path: Path,
    width: int,
    height: int,
    fill: str = "#F8FAFC",
    inset: tuple[int, int, int, int] | None = None,
) -> Image.Image:
    image = load_image(path, inset=inset)
    canvas = Image.new("RGB", (width, height), fill)
    image.thumbnail((width, height), Image.Resampling.LANCZOS)
    offset_x = (width - image.width) // 2
    offset_y = (height - image.height) // 2
    canvas.paste(image, (offset_x, offset_y))
    return canvas


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a GitHub showcase banner from repository assets.")
    parser.add_argument("-o", "--output", default=str(ASSETS / "hero_banner.png"))
    args = parser.parse_args()

    canvas = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(canvas)

    draw.text((64, 48), "Research Figure Skills", font=FONT_TITLE, fill=TEXT)
    draw.text((66, 116), "Routing-first scientific figures across CV, NLP, LLM, hybrid systems, and advanced plots", font=FONT_SUB, fill=SUBTLE)
    draw.rounded_rectangle((64, 156, 316, 194), radius=19, fill=ACCENT)
    draw.text((88, 163), "drawio  banana  plot  hybrid", font=FONT_META, fill="#082F49")

    gutter = 28
    tile_w = 484
    tile_h = 250
    col1_x = 64
    col2_x = col1_x + tile_w + gutter
    col3_x = col2_x + tile_w + gutter
    row1_y = 232
    row2_y = row1_y + tile_h + 34

    tiles = [
        {
            "title": "CV  Corridor Segmentation",
            "meta": "Banana method overview",
            "path": SHOWCASE / "cv_multiscale_segmentation.png",
            "box": (col1_x, row1_y, col1_x + tile_w, row1_y + tile_h),
        },
        {
            "title": "NLP  Document IE",
            "meta": "Banana paper illustration",
            "path": SHOWCASE / "nlp_document_ie.png",
            "box": (col2_x, row1_y, col2_x + tile_w, row1_y + tile_h),
        },
        {
            "title": "LLM  Tool-Using Agent",
            "meta": "Banana paper illustration",
            "path": SHOWCASE / "llm_agent_pipeline.png",
            "box": (col3_x, row1_y, col3_x + tile_w, row1_y + tile_h),
        },
        {
            "title": "Hybrid  Structure + Results",
            "meta": "drawio + plot composite preview",
            "path": SHOWCASE / "hybrid_corridor_results.png",
            "fit": "contain",
            "inset": (28, 28, 28, 28),
            "box": (col1_x, row2_y, col1_x + tile_w, row2_y + tile_h),
        },
        {
            "title": "Plot  Scaling Law",
            "meta": "Preview-ready line chart",
            "path": SHOWCASE / "ml_theory_scaling_law.png",
            "fit": "contain",
            "inset": (36, 36, 36, 36),
            "box": (col2_x, row2_y, col2_x + tile_w, row2_y + tile_h),
        },
        {
            "title": "Plot  Dual Axis + Log X",
            "meta": "Advanced metric visualization",
            "path": SHOWCASE / "plot_dual_axis_logx.png",
            "fit": "contain",
            "inset": (30, 30, 30, 30),
            "box": (col3_x, row2_y, col3_x + tile_w, row2_y + tile_h),
        },
    ]

    for tile in tiles:
        x0, y0, x1, y1 = tile["box"]
        draw.rounded_rectangle((x0, y0, x1, y1), radius=28, fill=CARD if y0 == row1_y else CARD_ALT)
        fit_mode = tile.get("fit", "crop")
        inset = tile.get("inset")
        if fit_mode == "contain":
            image = fit_contain(tile["path"], x1 - x0 - 24, y1 - y0 - 72, inset=inset)
        else:
            image = fit_crop(tile["path"], x1 - x0 - 24, y1 - y0 - 72, inset=inset)
        canvas.paste(image, (x0 + 12, y0 + 12))
        draw.text((x0 + 20, y1 - 52), tile["title"], font=FONT_CARD, fill=TEXT)
        draw.text((x0 + 20, y1 - 26), tile["meta"], font=FONT_META, fill=SUBTLE)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path)
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
