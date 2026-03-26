#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml


def read_text(path: str | None, request: str | None) -> str:
    parts = []
    if request:
        parts.append(request)
    if path:
        parts.append(Path(path).read_text(encoding="utf-8", errors="replace"))
    return "\n".join(parts)


def has_numeric_table(text: str) -> bool:
    if re.search(r"\\begin\{tabular", text):
        return True
    if re.search(r"^\s*\|.+\|\s*$", text, flags=re.M):
        return True
    return False


def has_stage_language(text: str) -> bool:
    lower = text.lower()
    if any(token in lower for token in ["stages", "steps", "pipeline", "workflow", "main stages", "method figure", "architecture", "流程", "步骤", "阶段", "架构"]):
        return True
    return bool(re.search(r"^\s*[-*+]\s+", text, flags=re.M) or re.search(r"^\s*\d+[.)]\s+", text, flags=re.M))


def route(text: str) -> dict:
    lower = text.lower()

    if any(token in lower for token in ["hybrid", "hybrid figure", "composite figure", "mixed figure", "结构+结果", "架构+结果"]):
        return {
            "figure_class": "hybrid-figure",
            "backend": "hybrid",
            "fallback_backend": "drawio",
            "reason": ["the request explicitly asks for a combined structure-plus-results figure"],
        }

    if has_numeric_table(text) and has_stage_language(text):
        return {
            "figure_class": "hybrid-figure",
            "backend": "hybrid",
            "fallback_backend": "drawio",
            "reason": ["the source includes both structural stages and quantitative tables"],
        }

    # Prioritize explicit figure intent before broad keyword matching.
    if any(token in lower for token in ["专利", "权利要求", "附图", "patent"]):
        return {
            "figure_class": "patent-figure",
            "backend": "drawio",
            "fallback_backend": "manual-vector",
            "reason": ["patent figures need controllable structure and editable layout"],
        }
    if any(token in lower for token in ["visual abstract", "visual-abstract"]):
        return {
            "figure_class": "visual-abstract",
            "backend": "banana",
            "fallback_backend": "hybrid",
            "reason": ["the figure is image-first and communication-oriented"],
        }
    if any(token in lower for token in ["teaser", "cover figure", "封面图"]):
        return {
            "figure_class": "teaser",
            "backend": "banana",
            "fallback_backend": "hybrid",
            "reason": ["the figure prioritizes visual impact over editable topology"],
        }
    if any(token in lower for token in ["plot", "chart", "curve", "ablation", "bar chart", "line chart", "指标图", "折线图", "柱状图"]):
        return {
            "figure_class": "chart-or-plot",
            "backend": "plot",
            "fallback_backend": "none",
            "reason": ["numeric fidelity matters more than image styling"],
        }
    if any(token in lower for token in ["system concept", "concept figure", "multi-agent", "uav", "drone", "robot"]):
        return {
            "figure_class": "system-concept",
            "backend": "banana",
            "fallback_backend": "drawio",
            "reason": ["the figure is a system concept illustration with strong visual anchors"],
        }
    if any(token in lower for token in ["drawio", "editable", "架构图", "流程图", "pipeline", "框图", "method figure", "architecture diagram"]):
        return {
            "figure_class": "editable-diagram",
            "backend": "drawio",
            "fallback_backend": "hybrid",
            "reason": ["the request implies strict structure or manual editing later"],
        }
    return {
        "figure_class": "method-overview",
        "backend": "drawio",
        "fallback_backend": "banana",
        "reason": ["default to the more controllable backend for scientific method figures"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Route a scientific figure request to the correct backend.")
    parser.add_argument("--source-file")
    parser.add_argument("--request")
    parser.add_argument("-o", "--output")
    args = parser.parse_args()

    text = read_text(args.source_file, args.request)
    result = route(text)
    payload = yaml.safe_dump(result, allow_unicode=True, sort_keys=False)
    if args.output:
        Path(args.output).write_text(payload, encoding="utf-8")
    else:
        sys.stdout.write(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
