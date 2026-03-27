#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml


PLACEHOLDER_LABELS = {
    "source artifact",
    "scientific figure",
    "source file",
    "figure",
    "research figure",
    "paper figure",
    "源文件",
    "科研图",
    "科学图",
    "图像",
}

GENERIC_REQUEST_PREFIXES = (
    "generate ",
    "create ",
    "draw ",
    "make ",
    "produce ",
    "render ",
    "生成",
    "绘制",
    "画",
    "制作",
)

SECTION_ALIASES = {
    "inputs": "inputs",
    "input": "inputs",
    "outputs": "outputs",
    "output": "outputs",
    "main stages": "stages",
    "stages": "stages",
    "stage": "stages",
    "pipeline": "stages",
    "core story": "story",
    "story": "story",
    "visual elements": "visual",
    "visuals": "visual",
    "notes": "notes",
    "说明": "notes",
    "输入": "inputs",
    "输出": "outputs",
    "主要阶段": "stages",
    "流程": "stages",
    "核心故事": "story",
    "视觉元素": "visual",
    "备注": "notes",
}


def contains_cjk(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text))


def normalize_text(text: str) -> str:
    return " ".join(str(text).strip().split())


def is_placeholder_label(text: str) -> bool:
    normalized = normalize_text(text).lower()
    return normalized in PLACEHOLDER_LABELS


def is_generic_one_liner(text: str) -> bool:
    normalized = normalize_text(text).lower()
    if not normalized:
        return True
    return any(normalized.startswith(prefix) for prefix in GENERIC_REQUEST_PREFIXES)


def clean_items(items, *, drop_placeholders: bool = True) -> list[str]:
    result: list[str] = []
    for item in items or []:
        if isinstance(item, dict):
            label = normalize_text(str(item.get("label") or item.get("purpose") or ""))
        else:
            label = normalize_text(str(item))
        if label and not (drop_placeholders and is_placeholder_label(label)):
            result.append(label)
    return result


def join_items_en(items: list[str], limit: int = 4) -> str:
    kept = items[:limit]
    if not kept:
        return ""
    if len(kept) == 1:
        return kept[0]
    if len(kept) == 2:
        return f"{kept[0]} and {kept[1]}"
    return ", ".join(kept[:-1]) + f", and {kept[-1]}"


def join_items_zh(items: list[str], limit: int = 4) -> str:
    kept = items[:limit]
    return "、".join(kept)


def shorten_stage_list(stages: list[str], lang: str) -> str:
    if lang == "zh":
        return join_items_zh(stages, limit=5)
    return join_items_en(stages, limit=5)


def infer_language(intent: dict, source_context: dict | None = None) -> str:
    probe = "\n".join(
        [
            str(intent.get("title", "")),
            str(intent.get("story", {}).get("one_liner", "")),
            " ".join(clean_items(intent.get("inputs", []))),
            " ".join(clean_items(intent.get("outputs", []))),
            " ".join((source_context or {}).get("inputs", [])),
            " ".join((source_context or {}).get("outputs", [])),
            " ".join((source_context or {}).get("stages", [])),
            " ".join((source_context or {}).get("story", [])),
        ]
    )
    return "zh" if contains_cjk(probe) else "en"


def normalize_section_key(text: str) -> str:
    return normalize_text(text).lower().rstrip(":：")


def split_markdown_row(line: str) -> list[str]:
    stripped = line.strip().strip("|")
    return [normalize_text(cell) for cell in stripped.split("|")]


def parse_markdown_table(text: str) -> dict | None:
    lines = text.splitlines()
    for idx in range(len(lines) - 2):
        header_line = lines[idx].strip()
        align_line = lines[idx + 1].strip()
        if "|" not in header_line:
            continue
        if not re.match(r"^\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)+\|?$", align_line):
            continue
        headers = split_markdown_row(header_line)
        rows: list[list[str]] = []
        cursor = idx + 2
        while cursor < len(lines):
            row_line = lines[cursor].strip()
            if "|" not in row_line or not row_line:
                break
            row = split_markdown_row(row_line)
            if len(row) != len(headers):
                break
            rows.append(row)
            cursor += 1
        if rows:
            return {"headers": headers, "rows": rows}
    return None


def parse_markdown_context(text: str) -> dict:
    context = {
        "title": "",
        "inputs": [],
        "outputs": [],
        "stages": [],
        "story": [],
        "visual": [],
        "notes": [],
        "table": parse_markdown_table(text),
    }
    current_section: str | None = None
    lines = text.splitlines()

    for line in lines:
        heading = re.match(r"^\s*#\s+(.+?)\s*$", line)
        if heading and not context["title"]:
            context["title"] = normalize_text(heading.group(1))
            continue

        section = re.match(r"^\s*([^\n:：]{1,40})\s*[:：]\s*$", line)
        if section:
            current_section = SECTION_ALIASES.get(normalize_section_key(section.group(1)))
            continue

        bullet = re.match(r"^\s*[-*]\s+(.+?)\s*$", line)
        if bullet and current_section:
            context[current_section].append(normalize_text(bullet.group(1)))
            continue

        if current_section in {"story", "notes"} and line.strip():
            context[current_section].append(normalize_text(line))

    return context


def parse_tex_context(text: str) -> dict:
    context = {
        "title": "",
        "inputs": [],
        "outputs": [],
        "stages": [],
        "story": [],
        "visual": [],
        "notes": [],
        "table": None,
    }
    title_match = re.search(r"\\title\{(.+?)\}", text, re.S)
    if title_match:
        context["title"] = normalize_text(title_match.group(1))
    abstract_match = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", text, re.S)
    if abstract_match:
        abstract = normalize_text(re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?(?:\{[^}]*\})?", " ", abstract_match.group(1)))
        if abstract:
            context["story"].append(abstract)
    return context


def extract_source_context(intent: dict) -> dict:
    default_context = {
        "title": "",
        "inputs": [],
        "outputs": [],
        "stages": [],
        "story": [],
        "visual": [],
        "notes": [],
        "table": None,
    }
    for artifact in intent.get("source_artifacts", []) or []:
        path_value = artifact.get("path") if isinstance(artifact, dict) else artifact
        if not path_value:
            continue
        path = Path(path_value)
        if not path.exists() or not path.is_file():
            continue
        if path.suffix.lower() not in {".md", ".markdown", ".txt", ".tex"}:
            continue
        text = path.read_text(encoding="utf-8")
        if path.suffix.lower() == ".tex":
            return parse_tex_context(text)
        return parse_markdown_context(text)
    return default_context


def infer_inputs_from_stage(stage: str) -> str:
    normalized = normalize_text(stage)
    lowered = normalized.lower()
    prefixes = ("input ", "inputs ", "start from ", "begin with ")
    for prefix in prefixes:
        if lowered.startswith(prefix):
            return normalize_text(normalized[len(prefix) :])
    if normalized.startswith("输入"):
        return normalize_text(normalized[2:])
    return ""


def infer_output_from_stage(stage: str) -> str:
    normalized = normalize_text(stage)
    lowered = normalized.lower()
    patterns = (
        r"(?:produce|produces|producing|output|outputs|obtain|obtains|yield|yields|generate|generates)\s+(.+)",
        r".+\s+into\s+(.+)",
    )
    for pattern in patterns:
        match = re.match(pattern, lowered)
        if match:
            source_match = re.match(pattern, normalized, re.IGNORECASE)
            if source_match:
                return normalize_text(source_match.group(1))
    zh_patterns = (
        r"(?:得到|输出|生成|形成)(.+)",
        r".+为(.+)",
    )
    for pattern in zh_patterns:
        match = re.match(pattern, normalized)
        if match:
            return normalize_text(match.group(1))
    return ""


def collect_context(intent: dict) -> dict:
    source_context = extract_source_context(intent)
    lang = infer_language(intent, source_context)
    title = normalize_text(str(intent.get("title") or source_context.get("title") or "Scientific Figure"))
    one_liner = normalize_text(str(intent.get("story", {}).get("one_liner", "")))
    if is_generic_one_liner(one_liner):
        one_liner = ""
    inputs = clean_items(intent.get("inputs", [])) or source_context.get("inputs", [])
    outputs = clean_items(intent.get("outputs", [])) or source_context.get("outputs", [])
    stages = clean_items(intent.get("stages", [])) or source_context.get("stages", []) or source_context.get("story", [])
    emphasis = clean_items(intent.get("story", {}).get("emphasis", [])) or clean_items(intent.get("must_keep_terms", []))

    if not inputs and stages:
        inferred_input = infer_inputs_from_stage(stages[0])
        if inferred_input:
            inputs = [inferred_input]
            stages = stages[1:]
    if not outputs and stages:
        inferred_output = infer_output_from_stage(stages[-1])
        if inferred_output:
            outputs = [inferred_output]
    if not emphasis:
        emphasis = stages[:4]

    return {
        "lang": lang,
        "title": title,
        "figure_class": str(intent.get("figure_class", "method-overview")),
        "backend": str(intent.get("backend", "drawio")),
        "one_liner": one_liner,
        "inputs": inputs,
        "outputs": outputs,
        "stages": stages,
        "emphasis": emphasis,
        "visual": source_context.get("visual", []),
        "notes": source_context.get("notes", []),
        "table": source_context.get("table"),
    }


def caption_for_method(context: dict) -> dict[str, str]:
    title = context["title"]
    backend = context["backend"]
    lang = context["lang"]
    figure_class = context["figure_class"]
    inputs = context["inputs"]
    outputs = context["outputs"]
    stages = context["stages"]
    emphasis = context["emphasis"]
    visual = context["visual"]

    if lang == "zh":
        short_caption = f"{title}的整体方法框架图。"
        lead = {
            "visual-abstract": f"该图概括了{title}的核心技术流程。",
            "system-concept": f"该图展示了{title}的系统级结构。",
            "teaser": f"该图给出了{title}的视觉化概览。",
        }.get(figure_class, f"该图展示了{title}的整体方法框架。")
        body_parts = [lead]
        if inputs:
            body_parts.append(f"方法从{join_items_zh(inputs, limit=4)}出发，")
        if stages:
            body_parts.append(f"依次经过{shorten_stage_list(stages, 'zh')}等关键阶段，")
        if outputs:
            body_parts.append(f"最终得到{join_items_zh(outputs, limit=3)}。")
        elif body_parts[-1].endswith("，"):
            body_parts[-1] = body_parts[-1].rstrip("，") + "。"
        if emphasis:
            body_parts.append(f"图中重点强调了{join_items_zh(emphasis, limit=4)}。")
        if backend == "banana":
            alt = f"一张论文风科研插图，标题为{title}，展示输入对象、核心阶段以及最终输出。"
            if visual:
                alt += f"画面包含{join_items_zh(visual, limit=3)}。"
        else:
            alt = f"一张结构化科研架构图，标题为{title}，展示输入、处理模块、输出以及关键连接关系。"
        return {
            "title": title,
            "short_caption": short_caption,
            "paper_caption": "".join(body_parts).replace("。。", "。"),
            "alt_text": alt,
        }

    short_caption = f"Overview of {title}."
    lead = {
        "visual-abstract": f"This figure summarizes the core scientific story of {title}.",
        "system-concept": f"This figure presents the system-level structure of {title}.",
        "teaser": f"This figure provides a visual summary of {title}.",
    }.get(figure_class, f"This figure illustrates the overall method pipeline of {title}.")
    body_parts = [lead]
    if inputs:
        body_parts.append(f"It starts from {join_items_en(inputs, limit=4)}.")
    if stages:
        body_parts.append(f"Key stages include {shorten_stage_list(stages, 'en')}.")
    if outputs:
        body_parts.append(f"It finally produces {join_items_en(outputs, limit=3)}.")
    if emphasis:
        body_parts.append(f"The figure emphasizes {join_items_en(emphasis, limit=4)}.")
    alt = f"A paper-style scientific figure titled {title}, arranged to show inputs, major processing stages, and outputs."
    if visual:
        alt += f" The visual layout includes {join_items_en(visual, limit=3)}."
    return {
        "title": title,
        "short_caption": short_caption,
        "paper_caption": " ".join(body_parts),
        "alt_text": alt,
    }


def parse_number(value: str) -> float | None:
    match = re.search(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", value.replace(",", ""))
    return float(match.group(0)) if match else None


def build_plot_summary(table: dict, lang: str) -> tuple[str, str]:
    headers = table.get("headers", [])
    rows = table.get("rows", [])
    if len(headers) < 3 or len(rows) < 2:
        return "", ""

    x_label = headers[0]
    series = headers[1:]
    numeric_columns: list[list[float]] = []
    for column_idx in range(1, len(headers)):
        column_values = [parse_number(row[column_idx]) for row in rows]
        if any(value is None for value in column_values):
            return "", ""
        numeric_columns.append([value for value in column_values if value is not None])

    x_start = rows[0][0]
    x_end = rows[-1][0]
    trend_parts: list[str] = []
    for series_name, values in zip(series, numeric_columns):
        if all(curr <= prev for prev, curr in zip(values, values[1:])):
            trend_parts.append(f"{series_name} decreases with scale")
        elif all(curr >= prev for prev, curr in zip(values, values[1:])):
            trend_parts.append(f"{series_name} increases with scale")

    relation = ""
    if len(series) == 2:
        left = numeric_columns[0]
        right = numeric_columns[1]
        if all(r < l for l, r in zip(left, right)):
            relation = f"{series[1]} remains below {series[0]} across the full range"
        elif all(r > l for l, r in zip(left, right)):
            relation = f"{series[1]} remains above {series[0]} across the full range"

    if lang == "zh":
        caption = f"该图比较了{join_items_zh(series, limit=4)}随{x_label}变化的趋势，横轴范围为{x_start}到{x_end}。"
        if trend_parts:
            caption += f"{join_items_zh(trend_parts, limit=3)}。"
        if relation:
            caption += f"{relation}。"
        alt = f"一张折线图，横轴为{x_label}，展示{join_items_zh(series, limit=4)}的变化趋势。"
        return caption, alt

    caption = f"This figure compares {join_items_en(series, limit=4)} as a function of {x_label}, spanning {x_start} to {x_end} on the horizontal axis."
    if trend_parts:
        caption += " " + ". ".join(part.capitalize() for part in trend_parts) + "."
    if relation:
        caption += f" {relation.capitalize()}."
    alt = f"A line chart with {x_label} on the horizontal axis, comparing {join_items_en(series, limit=4)}."
    return caption, alt


def caption_for_plot(context: dict) -> dict[str, str]:
    title = context["title"]
    lang = context["lang"]
    one_liner = context["one_liner"]
    emphasis = context["emphasis"]
    table = context["table"]

    if lang == "zh":
        short_caption = f"{title}的定量结果图。"
        caption = f"该图用于展示与{title}相关的定量对比结果。"
        alt = f"一张科研定量图，标题为{title}，用于展示关键指标或对比结果。"
        table_caption, table_alt = build_plot_summary(table or {}, lang)
        if table_caption:
            caption = table_caption
            alt = table_alt
        if one_liner:
            caption += f"其核心任务是：{one_liner}。"
        if emphasis:
            caption += f"图中重点关注{join_items_zh(emphasis, limit=4)}。"
        return {
            "title": title,
            "short_caption": short_caption,
            "paper_caption": caption,
            "alt_text": alt,
        }

    short_caption = f"Quantitative results for {title}."
    caption = f"This figure reports quantitative results related to {title}."
    alt = f"A scientific chart titled {title}, intended to highlight quantitative comparisons or trends."
    table_caption, table_alt = build_plot_summary(table or {}, lang)
    if table_caption:
        caption = table_caption
        alt = table_alt
    if one_liner:
        caption += f" It is intended to support the request: {one_liner}."
    if emphasis:
        caption += f" The main emphasis is on {join_items_en(emphasis, limit=4)}."
    return {
        "title": title,
        "short_caption": short_caption,
        "paper_caption": caption,
        "alt_text": alt,
    }


def caption_for_hybrid(context: dict) -> dict[str, str]:
    title = context["title"]
    lang = context["lang"]
    stages = context["stages"]
    if lang == "zh":
        short_caption = f"{title}的结构与结果组合图。"
        caption = f"该组合图将{title}的结构流程与定量结果放在同一幅图中。"
        if stages:
            caption += f"左侧结构部分突出{join_items_zh(stages, limit=4)}等关键阶段，右侧结果部分用于展示相应实验指标或趋势。"
        alt = f"一张结构与结果并列的科研组合图，左侧为流程结构，右侧为定量结果。"
        return {
            "title": title,
            "short_caption": short_caption,
            "paper_caption": caption,
            "alt_text": alt,
        }

    short_caption = f"Hybrid structure-and-results view for {title}."
    caption = f"This composite figure combines the structural pipeline of {title} with a quantitative result panel."
    if stages:
        caption += f" The left panel highlights {join_items_en(stages, limit=4)}, while the right panel summarizes the corresponding metrics or trends."
    alt = f"A hybrid scientific figure with a structure panel on the left and a quantitative results panel on the right."
    return {
        "title": title,
        "short_caption": short_caption,
        "paper_caption": caption,
        "alt_text": alt,
    }


def build_caption(intent: dict, backend: str) -> dict[str, str]:
    context = collect_context(intent)
    context["backend"] = backend
    if backend == "plot":
        payload = caption_for_plot(context)
    elif backend == "hybrid":
        payload = caption_for_hybrid(context)
    else:
        payload = caption_for_method(context)
    payload["language"] = context["lang"]
    return payload


def render_markdown(payload: dict[str, str]) -> str:
    return (
        "# Figure Caption\n\n"
        f"## Title\n{payload['title']}\n\n"
        f"## Short Caption\n{payload['short_caption']}\n\n"
        f"## Paper Caption\n{payload['paper_caption']}\n\n"
        f"## Alt Text\n{payload['alt_text']}\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile a paper-ready figure caption from figure_intent.yaml.")
    parser.add_argument("intent")
    parser.add_argument("--backend", choices=["drawio", "banana", "plot", "hybrid"])
    parser.add_argument("-o", "--output")
    args = parser.parse_args()

    intent = yaml.safe_load(Path(args.intent).read_text(encoding="utf-8"))
    backend = args.backend or str(intent.get("backend", "drawio"))
    payload = build_caption(intent, backend)
    rendered = render_markdown(payload)

    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
