#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import re
import sys
from collections import OrderedDict
from pathlib import Path

import yaml


COMPONENT_RE = re.compile(
    r"((?:[A-Za-z0-9\u4e00-\u9fff]+)?(?:模块|系统|平台|终端|基站|单元|装置|网络|中心|引擎|代理|Agent|Planner|Stylist|Critic|Renderer|Visualizer|Verifier|Retriever|Encoder|Decoder|Fusion|Backbone|Head))"
)


def read_text(source: str) -> str:
    if source == "-":
        return sys.stdin.read()
    return Path(source).read_text(encoding="utf-8")


def clean_line(line: str) -> str:
    line = re.sub(r"`+", "", line.strip())
    line = re.sub(r"\s+", " ", line)
    return line


def detect_title(lines: list[str]) -> str:
    for line in lines:
        if line.startswith("#"):
            return line.lstrip("#").strip()
    for line in lines:
        raw = line.strip()
        if not raw:
            continue
        if raw.startswith(("```", "-", "*")):
            continue
        if len(raw) <= 40:
            return raw
    return "未命名架构图"


def detect_audience(text: str) -> str:
    if re.search(r"权利要求|实施例|附图|专利|发明", text):
        return "patent"
    if re.search(r"实验|方法|模型|论文|benchmark|ablation|paper|figure|academic", text, re.I):
        return "paper"
    return "report"


def compress_text(label: str, limit: int = 14) -> str:
    label = re.sub(r"[；。:]$", "", label)
    label = re.sub(r"(所述|对应的|至少一种|和/或|以及|通过|根据|针对|利用|进行|执行)", "", label)
    label = re.sub(r"\s+", "", label)
    if len(label) <= limit:
        return label
    return label[:limit]


def compress_step_label(prefix: str, content: str) -> str:
    keyword_map = [
        (r"接入.*测量|测量.*接入|参考信号.*接入", "终端接入与测量"),
        (r"建.*小区|建网|建立.*网络", "区域到达与建网"),
        (r"接入|随机接入|寻呼", "终端接入"),
        (r"测量参数|参考信号|位姿参数", "参数采集"),
        (r"观测位置|虚拟多基站|观测数据集", "多位置观测"),
        (r"三边定位|多边定位|定位方程|位置初值", "三边/多边定位"),
        (r"迭代修正|飞行轨迹|飞行高度|波束|发射功率|闭环", "闭环优化调整"),
        (r"回传|通信链路|指挥端", "通信维持与回传"),
        (r"训练", "模型训练"),
        (r"推理", "模型推理"),
        (r"融合", "特征融合"),
        (r"解码", "结果解码"),
    ]
    for pattern, short in keyword_map:
        if re.search(pattern, content):
            return f"{prefix} {short}".strip()

    chunk = re.split(r"[，；。]", content)[0].strip()
    chunk = compress_text(chunk)
    return f"{prefix} {chunk}".strip()


def extract_steps(lines: list[str]) -> list[str]:
    s_pattern = re.compile(r"^\s*(S\d+)\s*[：:.\-]?\s*(.+?)\s*$", re.I)
    number_patterns = [
        re.compile(r"^\s*(\d+)[\.\)]\s*(.+?)\s*$"),
        re.compile(r"^\s*([一二三四五六七八九十]+)[、.]\s*(.+?)\s*$"),
    ]
    s_steps: list[str] = []
    numbered_steps: list[str] = []
    for line in lines:
        raw = clean_line(line)
        raw = re.sub(r"^\s*[-*+]\s*", "", raw)
        if not raw:
            continue
        s_match = s_pattern.match(raw)
        if s_match:
            prefix = s_match.group(1).upper()
            content = clean_line(s_match.group(2))
            s_steps.append(compress_step_label(prefix, content))
            continue
        for pattern in number_patterns:
            match = pattern.match(raw)
            if match:
                prefix = match.group(1)
                content = clean_line(match.group(2))
                if len(content) <= 40:
                    numbered_steps.append(compress_step_label(prefix, content))
                break
    return s_steps if s_steps else numbered_steps[:8]


def split_included_components(text: str) -> list[str]:
    candidates: list[str] = []
    for match in re.finditer(r"(?:包括|包含|由)([^。；;\n]+)", text):
        clause = match.group(1)
        for piece in re.split(r"[、，,及和与]", clause):
            piece = clean_line(piece)
            if 2 <= len(piece) <= 18 and not re.search(r"用于|以及|其中|形成|执行|进行", piece):
                candidates.append(piece)
    return candidates


def extract_components(text: str) -> list[str]:
    ordered = OrderedDict()
    for token in split_included_components(text):
        ordered[token] = None
    for token in re.findall(r"\b(Retriever|Planner|Stylist|Critic|Visualizer|Renderer|Verifier|reference set|source context|communicative intent|final illustration|Matplotlib code)\b", text, re.I):
        ordered[clean_line(token)] = None
    for match in COMPONENT_RE.finditer(text):
        token = clean_line(match.group(1))
        if 2 <= len(token) <= 24:
            ordered[token] = None
    return list(ordered.keys())


def to_id(label: str) -> str:
    ascii_part = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")
    if ascii_part:
        return ascii_part[:48]
    cjk_points = [f"u{ord(ch):x}" for ch in label if "\u4e00" <= ch <= "\u9fff"]
    return "_".join(cjk_points[:6]) or "node"


def classify_node(label: str, index: int, total: int) -> str:
    if re.search(r"数据|输入|终端|文本|图像|观测|source|input", label, re.I):
        return "input"
    if re.search(r"结果|输出|位置|指挥端|caption|output", label, re.I):
        return "output"
    if re.search(r"库|数据库|存储|storage", label, re.I):
        return "storage"
    if re.search(r"判断|决策|decision|是否", label, re.I):
        return "decision"
    if index == 0 and total > 2 and re.search(r"终端|输入|数据|文本|图像", label):
        return "input"
    if index == total - 1 and total > 2 and re.search(r"回传|输出|结果|位置|链路", label):
        return "output"
    if index == total - 1 and total > 2 and re.search(r"结果|输出|位置|图像", label):
        return "output"
    return "module"


def choose_diagram_type(text: str, steps: list[str], components: list[str], audience: str) -> str:
    if audience == "patent":
        if steps:
            return "pipeline"
        return "patent-architecture"
    if steps:
        return "pipeline"
    if re.search(r"encoder|decoder|head|backbone|fusion|branch|双流|双分支", text, re.I):
        return "model-structure"
    if len(components) >= 4:
        return "architecture"
    return "architecture"


def choose_layout(text: str, diagram_type: str, steps: list[str], components: list[str]) -> str:
    if diagram_type == "pipeline":
        return "top-to-bottom" if len(steps) >= 5 else "left-to-right"
    if re.search(r"双流|双分支|two-stream|dual-branch|siamese", text, re.I):
        return "dual-branch"
    if re.search(r"无人机|指挥端|控制中心|controller|command center|hub", text, re.I):
        return "hub-and-spoke"
    if diagram_type == "model-structure" and re.search(r"encoder|decoder|编解码", text, re.I):
        return "encoder-decoder"
    return "left-to-right"


def build_spec(title: str, text: str, lines: list[str]) -> tuple[dict, dict]:
    audience = detect_audience(text)
    steps = extract_steps(lines)
    components = extract_components(text)
    diagram_type = choose_diagram_type(text, steps, components, audience)
    layout = choose_layout(text, diagram_type, steps, components)

    if steps:
        labels = steps
    else:
        labels = components[:8]
    if not labels:
        labels = ["输入", "处理模块", "输出"]

    nodes = []
    seen_ids = set()
    for index, label in enumerate(labels):
        node_id = to_id(label)
        suffix = 2
        while node_id in seen_ids:
            node_id = f"{node_id}_{suffix}"
            suffix += 1
        seen_ids.add(node_id)
        nodes.append(
            {
                "id": node_id,
                "label": label,
                "type": classify_node(label, index, len(labels)),
            }
        )

    edges = []
    for index in range(len(nodes) - 1):
        edge_label = ""
        if diagram_type == "pipeline":
            edge_label = "下一步"
        edges.append({"from": nodes[index]["id"], "to": nodes[index + 1]["id"], "label": edge_label})

    groups = []
    if audience == "patent" and len(nodes) >= 5 and not steps:
        groups.append({"label": "核心模块", "members": [node["id"] for node in nodes[1:-1]]})

    assumptions = []
    missing_facts = []
    if not steps and len(components) < 4:
        assumptions.append("原文未提供完整模块拆分，当前结构为启发式草案。")
        missing_facts.append("建议补充输入、核心模块、输出和反馈关系。")
    if diagram_type == "pipeline" and len(nodes) < 4:
        assumptions.append("步骤数较少，流程图可能需要补充中间阶段。")
    if layout == "hub-and-spoke" and len(nodes) < 4:
        missing_facts.append("中心节点与外围节点关系尚不充分，hub-and-spoke 可能需要人工确认。")

    spec = {
        "title": title,
        "diagram_type": diagram_type,
        "layout": layout,
        "audience": audience,
        "style": "academic-minimal",
        "nodes": nodes,
        "edges": edges,
        "groups": groups,
        "notes": assumptions[:] if assumptions else ["该结构由启发式规划得到，需结合原文进一步校核。"],
    }

    planning = {
        "title": title,
        "diagram_type": diagram_type,
        "layout": layout,
        "audience": audience,
        "confirmed_structure": [node["label"] for node in nodes],
        "assumptions": assumptions,
        "missing_facts": missing_facts,
        "retrieval_hints": [
            f"layout-family={layout}",
            f"diagram-type={diagram_type}",
            f"audience={audience}",
        ],
    }
    return planning, spec


def render_markdown(planning: dict, spec: dict) -> str:
    lines = [
        f"# Diagram Planning Bundle: {planning['title']}",
        "",
        "## Planning Summary",
        f"- diagram_type: `{planning['diagram_type']}`",
        f"- layout: `{planning['layout']}`",
        f"- audience: `{planning['audience']}`",
        "",
        "## Confirmed Structure",
    ]
    for item in planning["confirmed_structure"]:
        lines.append(f"- {item}")

    lines.extend(["", "## Retriever Hints"])
    for item in planning["retrieval_hints"]:
        lines.append(f"- {item}")

    lines.extend(["", "## Assumptions"])
    if planning["assumptions"]:
        for item in planning["assumptions"]:
            lines.append(f"- {item}")
    else:
        lines.append("- 无明显结构假设。")

    lines.extend(["", "## Missing Facts"])
    if planning["missing_facts"]:
        for item in planning["missing_facts"]:
            lines.append(f"- {item}")
    else:
        lines.append("- 无。")

    yaml_block = yaml.safe_dump(spec, allow_unicode=True, sort_keys=False)
    lines.extend(["", "## Suggested Spec", "```yaml", yaml_block.rstrip(), "```", ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a heuristic planning bundle and draft diagram spec from source text.")
    parser.add_argument("source", help="Path to a text/Markdown file, or '-' for stdin.")
    parser.add_argument("-o", "--output", help="Write the planning bundle to this file.")
    parser.add_argument("--yaml-only", action="store_true", help="Print only the suggested YAML spec.")
    args = parser.parse_args()

    text = read_text(args.source)
    lines = [line for line in text.splitlines() if clean_line(line)]
    title = detect_title(lines)
    planning, spec = build_spec(title, text, lines)
    result = yaml.safe_dump(spec, allow_unicode=True, sort_keys=False) if args.yaml_only else render_markdown(planning, spec)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(result, encoding="utf-8")
    else:
        sys.stdout.write(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
