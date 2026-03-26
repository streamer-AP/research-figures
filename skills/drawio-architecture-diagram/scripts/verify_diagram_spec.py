#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict, deque
from pathlib import Path

import yaml


VALID_TYPES = {"architecture", "pipeline", "model-structure", "patent-architecture"}
VALID_LAYOUTS = {"left-to-right", "top-to-bottom", "dual-branch", "encoder-decoder", "hub-and-spoke"}
VALID_AUDIENCE = {"paper", "patent", "report"}
VALID_NODE_TYPES = {"input", "module", "output", "storage", "decision", "group-anchor"}


def extract_yaml_from_markdown(text: str) -> str:
    match = re.search(r"```ya?ml\s*\n(.*?)\n```", text, re.S)
    if not match:
        raise ValueError("No fenced YAML block found in the Markdown source.")
    return match.group(1).strip() + "\n"


def read_spec(path_str: str, from_markdown: bool | None) -> tuple[dict, Path | None]:
    if path_str == "-":
        text = sys.stdin.read()
        source_path = None
        suffix = ".md" if from_markdown else ".yaml"
    else:
        source_path = Path(path_str)
        text = source_path.read_text(encoding="utf-8")
        suffix = source_path.suffix.lower()

    md_mode = from_markdown if from_markdown is not None else suffix in {".md", ".markdown"}
    yaml_text = extract_yaml_from_markdown(text) if md_mode else text
    spec = yaml.safe_load(yaml_text)
    if not isinstance(spec, dict):
        raise ValueError("Diagram spec must decode to a mapping.")
    return spec, source_path


def detect_cycles(node_ids: list[str], edges: list[dict]) -> list[list[str]]:
    graph: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        src = edge.get("from")
        dst = edge.get("to")
        if src in node_ids and dst in node_ids:
            graph[src].append(dst)

    cycles: list[list[str]] = []
    temp = set()
    perm = set()
    stack: list[str] = []

    def visit(node_id: str) -> None:
        if node_id in perm:
            return
        if node_id in temp:
            if node_id in stack:
                start = stack.index(node_id)
                cycles.append(stack[start:] + [node_id])
            return
        temp.add(node_id)
        stack.append(node_id)
        for nxt in graph[node_id]:
            visit(nxt)
        stack.pop()
        temp.remove(node_id)
        perm.add(node_id)

    for node_id in node_ids:
        if node_id not in perm:
            visit(node_id)
    return cycles


def connected_components(node_ids: list[str], edges: list[dict]) -> int:
    adjacency: dict[str, set[str]] = defaultdict(set)
    for edge in edges:
        src = edge.get("from")
        dst = edge.get("to")
        if src in node_ids and dst in node_ids:
            adjacency[src].add(dst)
            adjacency[dst].add(src)

    seen = set()
    count = 0
    for node_id in node_ids:
        if node_id in seen:
            continue
        count += 1
        queue = deque([node_id])
        seen.add(node_id)
        while queue:
            current = queue.popleft()
            for nxt in adjacency[current]:
                if nxt not in seen:
                    seen.add(nxt)
                    queue.append(nxt)
    return count


def recommended_layout(spec: dict) -> str:
    diagram_type = spec.get("diagram_type")
    edges = spec.get("edges", [])
    nodes = spec.get("nodes", [])

    indegree = Counter()
    outdegree = Counter()
    for edge in edges:
        outdegree[edge.get("from")] += 1
        indegree[edge.get("to")] += 1

    if diagram_type == "pipeline":
        return "top-to-bottom" if len(nodes) >= 5 else "left-to-right"
    if any(outdegree[node.get("id")] >= 2 for node in nodes) and any(indegree[node.get("id")] >= 2 for node in nodes):
        return "hub-and-spoke"
    if diagram_type == "model-structure":
        return "encoder-decoder"
    return "left-to-right"


def analyze(spec: dict) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    info: list[str] = []

    for key in ("title", "diagram_type", "layout", "audience", "style", "nodes", "edges"):
        if key not in spec:
            errors.append(f"缺少必填字段: {key}")

    diagram_type = spec.get("diagram_type")
    layout = spec.get("layout")
    audience = spec.get("audience")
    nodes = spec.get("nodes", [])
    edges = spec.get("edges", [])
    groups = spec.get("groups", [])
    notes = spec.get("notes", [])

    if diagram_type and diagram_type not in VALID_TYPES:
        errors.append(f"不支持的 diagram_type: {diagram_type}")
    if layout and layout not in VALID_LAYOUTS:
        errors.append(f"不支持的 layout: {layout}")
    if audience and audience not in VALID_AUDIENCE:
        errors.append(f"不支持的 audience: {audience}")

    node_ids = []
    label_counter = Counter()
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            errors.append(f"节点 {index} 不是对象。")
            continue
        node_id = node.get("id")
        label = str(node.get("label", "")).strip()
        node_type = node.get("type")
        if not node_id:
            errors.append(f"节点 {index} 缺少 id。")
            continue
        node_ids.append(node_id)
        if node_type not in VALID_NODE_TYPES:
            errors.append(f"节点 {node_id} 使用了不支持的类型: {node_type}")
        if not label:
            errors.append(f"节点 {node_id} 缺少 label。")
        label_counter[label] += 1
        english_words = re.findall(r"[A-Za-z0-9]+", label)
        cjk_chars = len(re.findall(r"[\u4e00-\u9fff]", label))
        if len(english_words) > 4 or cjk_chars > 12:
            warnings.append(f"节点 {node_id} 的可见标签偏长，建议再压缩: {label}")

    duplicates = [node_id for node_id, count in Counter(node_ids).items() if count > 1]
    for node_id in duplicates:
        errors.append(f"存在重复节点 id: {node_id}")

    duplicate_labels = [label for label, count in label_counter.items() if label and count > 1]
    for label in duplicate_labels:
        warnings.append(f"存在重复可见标签，后续编辑可能混淆: {label}")

    node_id_set = set(node_ids)
    indegree = Counter()
    outdegree = Counter()
    for index, edge in enumerate(edges):
        if not isinstance(edge, dict):
            errors.append(f"边 {index} 不是对象。")
            continue
        src = edge.get("from")
        dst = edge.get("to")
        if src not in node_id_set:
            errors.append(f"边 {index} 的起点不存在: {src}")
        if dst not in node_id_set:
            errors.append(f"边 {index} 的终点不存在: {dst}")
        if src in node_id_set:
            outdegree[src] += 1
        if dst in node_id_set:
            indegree[dst] += 1

    for group in groups:
        if not isinstance(group, dict):
            warnings.append("存在非对象类型的 group。")
            continue
        for member in group.get("members", []):
            if member not in node_id_set:
                errors.append(f"group {group.get('label', '<unnamed>')} 引用了不存在的成员: {member}")

    if not notes:
        warnings.append("notes 为空，建议至少写出一个假设或设计说明。")

    isolated = [node_id for node_id in node_ids if indegree[node_id] == 0 and outdegree[node_id] == 0]
    if len(nodes) > 1 and isolated:
        warnings.append("存在孤立节点: " + ", ".join(isolated))

    components = connected_components(node_ids, edges) if node_ids else 0
    if components > 1:
        warnings.append(f"图存在 {components} 个连通分量，可能需要补充连接关系。")

    cycles = detect_cycles(node_ids, edges)
    if cycles:
        cycle_preview = " -> ".join(cycles[0])
        warnings.append(f"检测到循环或反馈路径: {cycle_preview}")

    recommended = recommended_layout(spec)
    if layout and recommended != layout:
        warnings.append(f"当前 layout={layout}，结构上更像 {recommended}。")

    if diagram_type == "pipeline":
        branching_nodes = [node_id for node_id in node_ids if outdegree[node_id] > 1]
        if branching_nodes:
            warnings.append("pipeline 图中存在多分支节点，需确认是否仍应使用流程图布局。")

    info.append(f"nodes={len(nodes)}")
    info.append(f"edges={len(edges)}")
    info.append(f"groups={len(groups)}")
    info.append(f"recommended_layout={recommended}")

    status = "pass" if not errors else "needs-fix"
    return {
        "status": status,
        "errors": errors,
        "warnings": warnings,
        "info": info,
    }


def format_report(report: dict) -> str:
    lines = [f"STATUS: {report['status']}"]
    lines.extend(report["info"])
    lines.append("")
    lines.append("Errors:")
    if report["errors"]:
        lines.extend([f"- {item}" for item in report["errors"]])
    else:
        lines.append("- None")
    lines.append("")
    lines.append("Warnings:")
    if report["warnings"]:
        lines.extend([f"- {item}" for item in report["warnings"]])
    else:
        lines.append("- None")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a diagram spec before draw.io conversion.")
    parser.add_argument("source", help="Path to a YAML spec file, a Markdown file, or '-' for stdin.")
    parser.add_argument("--from-markdown", action="store_true", help="Force Markdown mode and read the first fenced YAML block.")
    parser.add_argument("--from-yaml", action="store_true", help="Force raw YAML mode.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = parser.parse_args()

    if args.from_markdown and args.from_yaml:
        parser.error("Choose only one of --from-markdown or --from-yaml.")
    from_markdown = True if args.from_markdown else False if args.from_yaml else None

    try:
        spec, _ = read_spec(args.source, from_markdown)
        report = analyze(spec)
    except (FileNotFoundError, ValueError, yaml.YAMLError) as exc:
        print(f"[verify_diagram_spec] {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(format_report(report), end="")
    return 0 if report["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
