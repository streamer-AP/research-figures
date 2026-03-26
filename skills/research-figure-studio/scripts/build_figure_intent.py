#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml


FALLBACK_PALETTE = "vivid-academic"
DOMAIN_PALETTE_RULES = [
    (
        "tol-vibrant",
        {
            "cv",
            "computer vision",
            "vision",
            "segmentation",
            "detection",
            "tracking",
            "point cloud",
            "lidar",
            "3d perception",
            "scene understanding",
            "corridor",
            "image encoder",
            "visual",
        },
    ),
    (
        "tol-bright",
        {
            "nlp",
            "natural language",
            "language model",
            "document",
            "text",
            "entity",
            "relation extraction",
            "knowledge graph",
            "retrieval",
            "corpus",
            "token",
            "semantic parsing",
        },
    ),
    (
        "okabe-ito",
        {
            "llm",
            "agent",
            "tool",
            "planner",
            "verifier",
            "memory",
            "rag",
            "multi-agent",
            "execution loop",
            "response synthesizer",
            "reasoning",
        },
    ),
    (
        "vivid-academic",
        {
            "robot",
            "robotics",
            "drone",
            "uav",
            "system",
            "hardware",
            "sensor",
            "edge",
            "wireless",
            "network",
            "audio",
            "flac",
            "signal",
            "speech",
            "base station",
        },
    ),
    (
        "clean-academic",
        {
            "optimization",
            "theory",
            "mathematics",
            "proof",
            "scaling law",
            "benchmark chart",
            "ablation",
            "plot",
            "statistics",
        },
    ),
]


def read_text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8", errors="replace")


def detect_title(text: str) -> str:
    m = re.search(r"\\title\{([^}]+)\}", text)
    if m:
        return m.group(1).strip()
    for line in text.splitlines():
        raw = line.strip()
        if raw.startswith("#"):
            return raw.lstrip("#").strip()
    return "Untitled Figure"


def detect_stages(text: str) -> list[dict]:
    patterns = [
        re.compile(r"^\s*\d+[.)]\s*(.+?)\s*$"),
        re.compile(r"^\s*S(\d+)\s*[:：.\-]?\s*(.+?)\s*$", re.I),
    ]
    stage_headers = (
        "main stages",
        "stages",
        "steps",
        "pipeline stages",
        "主要阶段",
        "步骤",
        "流程",
    )
    stages = []
    in_stage_block = False
    saw_stage_item = False

    def add_stage(label: str) -> None:
        nonlocal saw_stage_item
        clean = re.sub(r"\s+", " ", label).strip().rstrip(";.")
        if not clean:
            return
        saw_stage_item = True
        stages.append(
            {
                "id": f"stage_{len(stages)+1}",
                "label": clean[:64],
                "purpose": clean[:160],
            }
        )

    for line in text.splitlines():
        stripped = line.strip()
        lowered = re.sub(r"\s+", " ", stripped.lower())

        if any(lowered.startswith(header) for header in stage_headers):
            in_stage_block = True
            saw_stage_item = False
            continue

        if not stripped:
            if in_stage_block:
                continue
            continue

        for pattern in patterns:
            m = pattern.match(stripped)
            if m:
                add_stage(m.group(len(m.groups())))
                break
        else:
            bullet_match = re.match(r"^\s*[-*+]\s*(.+?)\s*$", line)
            if in_stage_block and bullet_match:
                add_stage(bullet_match.group(1))
            elif in_stage_block and saw_stage_item:
                in_stage_block = False
    return stages[:8]


def route(text: str, request: str) -> tuple[str, str]:
    lower = (text + "\n" + request).lower()
    has_table = "\\begin{tabular" in text or bool(re.search(r"^\s*\|.+\|\s*$", text, flags=re.M))
    has_stage_text = bool(detect_stages(text)) or any(token in lower for token in ["pipeline", "workflow", "architecture", "流程", "步骤", "阶段", "架构"])
    if any(token in lower for token in ["hybrid", "hybrid figure", "composite figure", "mixed figure", "结构+结果", "架构+结果"]) or (has_table and has_stage_text):
        return "hybrid-figure", "hybrid"
    if any(token in lower for token in ["专利", "附图", "patent"]):
        return "patent-figure", "drawio"
    if any(token in lower for token in ["visual abstract", "teaser", "cover figure", "visual-abstract"]):
        return "visual-abstract", "banana"
    if any(token in lower for token in ["plot", "chart", "ablation", "折线图", "柱状图"]):
        return "chart-or-plot", "plot"
    if any(token in lower for token in ["drawio", "editable", "架构图", "流程图", "框图"]):
        return "editable-diagram", "drawio"
    return "method-overview", "drawio"


def recommend_palette(text: str, request: str, backend: str) -> str:
    if backend != "banana":
        return "clean-academic"
    lower = (text + "\n" + request).lower()
    scores = {}
    for palette, keywords in DOMAIN_PALETTE_RULES:
        score = 0
        for keyword in keywords:
            if keyword in lower:
                score += len(keyword.split())
        scores[palette] = score
    best_palette = max(scores, key=scores.get)
    if scores[best_palette] == 0:
        return FALLBACK_PALETTE
    return best_palette


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a shared figure_intent.yaml from source text.")
    parser.add_argument("--source-file", required=True)
    parser.add_argument("--request", default="")
    parser.add_argument("--figure-class")
    parser.add_argument("--backend")
    parser.add_argument("-o", "--output")
    args = parser.parse_args()

    text = read_text(args.source_file)
    figure_class, backend = route(text, args.request)
    if args.figure_class:
        figure_class = args.figure_class
    if args.backend:
        backend = args.backend

    stages = detect_stages(text)
    title = detect_title(text)
    palette = recommend_palette(text, args.request, backend)
    intent = {
        "title": title,
        "figure_class": figure_class,
        "backend": backend,
        "audience": "paper" if figure_class != "patent-figure" else "patent",
        "story": {
            "one_liner": args.request or "Generate a scientific figure that preserves the paper's core story.",
            "emphasis": [stage["label"] for stage in stages[:4]],
        },
        "source_artifacts": [{"path": args.source_file, "kind": Path(args.source_file).suffix.lstrip(".") or "text"}],
        "must_keep_terms": [stage["label"] for stage in stages[:4]],
        "forbidden_details": ["tiny paragraphs inside image", "decorative background"],
        "inputs": ["source artifact"],
        "outputs": ["scientific figure"],
        "stages": stages,
        "edges": [{"from": stages[idx]["id"], "to": stages[idx + 1]["id"]} for idx in range(max(0, len(stages) - 1))],
        "visual_objects": [],
        "style_constraints": {"palette": palette, "background": "white", "label_density": "low"},
        "verification_targets": ["required stages preserved", "no extra invented stage"],
        "assumptions": [] if stages else ["Source text did not expose explicit stages; the figure intent is incomplete."],
    }
    payload = yaml.safe_dump(intent, allow_unicode=True, sort_keys=False)
    if args.output:
        Path(args.output).write_text(payload, encoding="utf-8")
    else:
        sys.stdout.write(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
