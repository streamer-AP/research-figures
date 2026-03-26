#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile figure_intent.yaml into a Banana-ready prompt.")
    parser.add_argument("intent")
    parser.add_argument("-o", "--output")
    args = parser.parse_args()

    intent = yaml.safe_load(Path(args.intent).read_text(encoding="utf-8"))
    title = intent.get("title", "Scientific Figure")
    figure_class = intent.get("figure_class", "method-overview")
    stages = [stage.get("label", "") for stage in intent.get("stages", []) if stage.get("label")]
    inputs = [str(item) for item in intent.get("inputs", []) if item]
    outputs = [str(item) for item in intent.get("outputs", []) if item]
    visual_objects = [str(item) for item in intent.get("visual_objects", []) if item]
    prompt_lines = [
        f"Create a clean publication-quality scientific figure titled '{title}'.",
        "Use a white or very light background, minimal clutter, balanced composition, and only a few large readable labels.",
        f"Figure class: {figure_class}.",
    ]
    if figure_class in {"method-overview", "editable-diagram"}:
        prompt_lines.append("Use a structured left-to-right or layered method-figure composition rather than a free-form concept image.")
    if figure_class in {"visual-abstract", "teaser"}:
        prompt_lines.append("Prioritize a visually strong paper figure while keeping the scientific story clear.")
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
