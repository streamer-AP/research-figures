#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml


DEFAULT_PALETTE = "vivid-academic"
PALETTE_PRESETS = {
    "clean-academic": {
        "summary": "a restrained scientific palette with calm contrast and publication-safe accents",
        "accents": ["#4477AA", "#66CCEE", "#228833", "#CCBB44", "#AA3377"],
        "guidance": [
            "keep the background white or very light neutral gray",
            "use blue, teal, green, amber, and plum as the main accent family",
            "keep support elements in slate, graphite, and soft gray",
        ],
    },
    "vivid-academic": {
        "summary": "a lively but still academic palette inspired by Paul Tol bright and vibrant schemes plus Okabe-Ito accents",
        "accents": ["#4477AA", "#66CCEE", "#228833", "#CCBB44", "#EE6677", "#AA3377"],
        "guidance": [
            "use 4 to 6 saturated accent colors with crisp separation between modules",
            "favor cobalt blue, cyan, teal, amber, coral, and magenta instead of muddy blue-gray monotony",
            "reserve the warmest accent for the key novelty, output, or feedback loop",
        ],
    },
    "okabe-ito": {
        "summary": "a color-blind-friendly palette based on the Okabe-Ito set",
        "accents": ["#E69F00", "#56B4E9", "#009E73", "#F0E442", "#0072B2", "#D55E00", "#CC79A7"],
        "guidance": [
            "keep hues distinct and accessible",
            "avoid relying on red-green separation alone",
        ],
    },
    "tol-bright": {
        "summary": "a publication palette based on Paul Tol's bright qualitative scheme",
        "accents": ["#4477AA", "#EE6677", "#228833", "#CCBB44", "#66CCEE", "#AA3377"],
        "guidance": [
            "prefer strong module blocks and crisp arrows",
            "keep gray as a support tone, not the main visual voice",
        ],
    },
    "tol-vibrant": {
        "summary": "a more energetic scientific palette based on Paul Tol's vibrant qualitative scheme",
        "accents": ["#EE7733", "#0077BB", "#33BBEE", "#EE3377", "#CC3311", "#009988"],
        "guidance": [
            "push contrast slightly more than a default paper palette while staying publication-safe",
            "avoid neon glow and dark poster aesthetics",
        ],
    },
    "brewer-accent": {
        "summary": "a ColorBrewer-inspired qualitative palette with grouped hues and accent highlights",
        "accents": ["#66C2A5", "#FC8D62", "#8DA0CB", "#E78AC3", "#A6D854", "#FFD92F"],
        "guidance": [
            "treat related modules as related hues",
            "reserve the strongest accent for the most important outcome",
        ],
    },
}
AUTO_PALETTE_NOTES = {
    "tol-vibrant": "Auto-selected for CV and perception-heavy figures.",
    "tol-bright": "Auto-selected for NLP and document-centric figures.",
    "okabe-ito": "Auto-selected for LLM, agent, and tool-using workflows.",
    "vivid-academic": "Auto-selected for systems, robotics, audio, and hardware-heavy figures.",
    "clean-academic": "Auto-selected for theory-leaning or chart-adjacent figures.",
}


def palette_lines(palette: str, figure_class: str) -> list[str]:
    preset = PALETTE_PRESETS.get(palette, PALETTE_PRESETS[DEFAULT_PALETTE])
    lines = [
        f"Use {preset['summary']}.",
        "Preferred accent colors: " + ", ".join(preset["accents"]) + ".",
        "Palette guidance: " + "; ".join(preset["guidance"]) + ".",
    ]
    if palette in AUTO_PALETTE_NOTES:
        lines.append(AUTO_PALETTE_NOTES[palette])
    if figure_class in {"method-overview", "editable-diagram"}:
        lines.append("Use color to separate modules and states with broad readable regions, not decorative gradients.")
    if figure_class in {"visual-abstract", "teaser", "system-concept"}:
        lines.append("Allow one restrained cool-to-warm atmospheric transition, but keep the science crisp and legible.")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile figure_intent.yaml into a Banana-ready prompt.")
    parser.add_argument("intent")
    parser.add_argument("-o", "--output")
    args = parser.parse_args()

    intent = yaml.safe_load(Path(args.intent).read_text(encoding="utf-8"))
    title = intent.get("title", "Scientific Figure")
    figure_class = intent.get("figure_class", "method-overview")
    style_constraints = intent.get("style_constraints", {}) or {}
    palette = str(style_constraints.get("palette") or DEFAULT_PALETTE)
    background = str(style_constraints.get("background") or "white")
    label_density = str(style_constraints.get("label_density") or "low")
    stages = [stage.get("label", "") for stage in intent.get("stages", []) if stage.get("label")]
    inputs = [str(item) for item in intent.get("inputs", []) if item]
    outputs = [str(item) for item in intent.get("outputs", []) if item]
    visual_objects = [str(item) for item in intent.get("visual_objects", []) if item]
    prompt_lines = [
        f"Create a clean publication-quality scientific figure titled '{title}'.",
        f"Use a {background} or very light neutral background, minimal clutter, balanced composition, and only a few large readable labels.",
        f"Figure class: {figure_class}.",
    ]
    prompt_lines.extend(palette_lines(palette, figure_class))
    if figure_class in {"method-overview", "editable-diagram"}:
        prompt_lines.append("Use a structured left-to-right or layered method-figure composition rather than a free-form concept image.")
    if figure_class in {"visual-abstract", "teaser"}:
        prompt_lines.append("Prioritize a visually strong paper figure while keeping the scientific story clear.")
    if label_density == "low":
        prompt_lines.append("Keep label density low and avoid paragraphs inside the figure.")
    elif label_density == "medium":
        prompt_lines.append("Allow only a moderate amount of labels and keep each label short.")
    if inputs:
        prompt_lines.append("Inputs to show:")
        prompt_lines.append(", ".join(inputs[:5]) + ".")
    if stages:
        prompt_lines.append("Main stages to preserve:")
        prompt_lines.append(", ".join(stages[:6]) + ".")
    if outputs:
        prompt_lines.append("Outputs to show:")
        prompt_lines.append(", ".join(outputs[:3]) + ".")
    if visual_objects:
        prompt_lines.append("Important visual objects:")
        prompt_lines.append(", ".join(visual_objects[:6]) + ".")
    for item in intent.get("must_keep_terms", [])[:6]:
        prompt_lines.append(f"Must preserve: {item}.")
    for item in intent.get("forbidden_details", [])[:6]:
        prompt_lines.append(f"Avoid: {item}.")
    prompt_lines.append("Do not add tiny paragraphs, excessive legends, or labels not implied by the scientific story.")
    prompt = "\n".join(prompt_lines)

    if args.output:
        Path(args.output).write_text(prompt + "\n", encoding="utf-8")
    else:
        sys.stdout.write(prompt + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
