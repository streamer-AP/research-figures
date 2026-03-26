#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml


def infer_diagram_type(intent: dict) -> str:
    figure_class = intent.get("figure_class", "method-overview")
    if figure_class == "patent-figure":
        return "patent-architecture"
    if figure_class in {"editable-diagram", "method-overview"}:
        return "pipeline"
    return "architecture"


def infer_layout(intent: dict) -> str:
    stages = intent.get("stages", [])
    if intent.get("figure_class") == "patent-figure":
        return "left-to-right"
    if 2 <= len(stages) <= 5:
        return "left-to-right"
    return "top-to-bottom"


def shorten(label: str, limit: int = 36) -> str:
    label = " ".join(str(label).split())
    if len(label) <= limit:
        return label
    return label[: limit - 3].rstrip() + "..."


def build_spec(intent: dict) -> dict:
    title = intent.get("title", "Scientific Figure")
    audience = intent.get("audience", "paper")
    stages = intent.get("stages", [])
    inputs = intent.get("inputs", [])
    outputs = intent.get("outputs", [])
    notes = intent.get("must_keep_terms", [])[:]
    notes.extend(intent.get("assumptions", [])[:])

    nodes = []
    edges = []
    groups = []

    input_ids = []
    for index, item in enumerate(inputs, start=1):
        node_id = f"input_{index}"
        input_ids.append(node_id)
        nodes.append({"id": node_id, "label": shorten(item), "type": "input"})

    stage_ids = []
    for stage in stages:
        node_id = stage.get("id") or f"stage_{len(stage_ids)+1}"
        stage_ids.append(node_id)
        nodes.append({"id": node_id, "label": shorten(stage.get("label", node_id)), "type": "module"})

    output_ids = []
    for index, item in enumerate(outputs, start=1):
        node_id = f"output_{index}"
        output_ids.append(node_id)
        nodes.append({"id": node_id, "label": shorten(item), "type": "output"})

    if input_ids and stage_ids:
        for node_id in input_ids:
            edges.append({"from": node_id, "to": stage_ids[0], "label": ""})

    for index in range(len(stage_ids) - 1):
        edges.append({"from": stage_ids[index], "to": stage_ids[index + 1], "label": ""})

    if stage_ids and output_ids:
        for node_id in output_ids:
            edges.append({"from": stage_ids[-1], "to": node_id, "label": ""})

    if stage_ids:
        groups.append({"label": "Main Pipeline", "members": stage_ids})

    if input_ids:
        groups.append({"label": "Inputs", "members": input_ids})
    if output_ids:
        groups.append({"label": "Outputs", "members": output_ids})

    spec = {
        "title": title,
        "diagram_type": infer_diagram_type(intent),
        "layout": infer_layout(intent),
        "audience": audience,
        "style": "academic-minimal",
        "nodes": nodes,
        "edges": edges,
        "groups": groups,
        "notes": notes or ["Generated from figure_intent.yaml."],
    }
    return spec


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile figure_intent.yaml into a draw.io-ready YAML spec.")
    parser.add_argument("intent")
    parser.add_argument("-o", "--output")
    args = parser.parse_args()

    intent = yaml.safe_load(Path(args.intent).read_text(encoding="utf-8"))
    spec = build_spec(intent)
    payload = yaml.safe_dump(spec, allow_unicode=True, sort_keys=False)
    if args.output:
        Path(args.output).write_text(payload, encoding="utf-8")
    else:
        sys.stdout.write(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
