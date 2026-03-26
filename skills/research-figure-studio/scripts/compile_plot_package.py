#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

import yaml


def read_source(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def parse_number(value: str) -> float | None:
    cleaned = str(value).strip().replace(",", "")
    if not cleaned:
        return None
    if cleaned.endswith("%"):
        cleaned = cleaned[:-1]
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_csv_table(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        rows = list(csv.reader(handle))
    if len(rows) < 2:
        return []
    header = [cell.strip() for cell in rows[0]]
    data_rows = [[cell.strip() for cell in row] for row in rows[1:] if any(cell.strip() for cell in row)]
    return [{"header": header, "rows": data_rows, "kind": "csv"}] if data_rows else []


def split_markdown_row(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [cell.strip() for cell in stripped.split("|")]


def is_separator_row(cells: list[str]) -> bool:
    if not cells:
        return False
    return all(re.fullmatch(r":?-{3,}:?", cell or "") for cell in cells)


def parse_markdown_tables(text: str) -> list[dict]:
    tables: list[dict] = []
    lines = text.splitlines()
    idx = 0
    while idx < len(lines):
        if "|" not in lines[idx]:
            idx += 1
            continue

        block: list[str] = []
        while idx < len(lines) and "|" in lines[idx]:
            block.append(lines[idx])
            idx += 1

        if len(block) < 2:
            continue

        header = split_markdown_row(block[0])
        separator = split_markdown_row(block[1])
        if not header or not is_separator_row(separator):
            continue

        rows = []
        for line in block[2:]:
            cells = split_markdown_row(line)
            if len(cells) == len(header):
                rows.append(cells)
        if rows:
            tables.append({"header": header, "rows": rows, "kind": "markdown"})
    return tables


def strip_latex_comments(text: str) -> str:
    return re.sub(r"(?<!\\)%.*$", "", text, flags=re.M)


def clean_latex_cell(cell: str) -> str:
    text = cell.strip()
    text = re.sub(r"\\rowcolor\{[^{}]*\}", "", text)
    text = re.sub(r"\\cellcolor\{[^{}]*\}", "", text)
    text = text.replace(r"\%", "%").replace(r"\_", "_").replace("~", " ")
    text = re.sub(r"\$([^$]+)\$", r"\1", text)
    text = re.sub(r"\\multicolumn\{[^{}]*\}\{[^{}]*\}\{([^{}]*)\}", r"\1", text)
    text = re.sub(r"\\multirow\{[^{}]*\}\{[^{}]*\}\{([^{}]*)\}", r"\1", text)

    previous = None
    while text != previous:
        previous = text
        text = re.sub(r"\\[a-zA-Z*@]+(?:\[[^\]]*\])?\{([^{}]*)\}", r"\1", text)

    text = re.sub(r"\\[a-zA-Z*@]+(?:\[[^\]]*\])?", "", text)
    text = text.replace("{", "").replace("}", "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def parse_latex_tables(text: str) -> list[dict]:
    tables: list[dict] = []
    sanitized = strip_latex_comments(text)
    pattern = re.compile(r"\\begin\{tabular\*?\}.*?\\end\{tabular\*?\}", re.S)

    for match in pattern.finditer(sanitized):
        block = match.group(0)
        lines = []
        for line in block.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith(r"\begin{tabular") or stripped.startswith(r"\end{tabular"):
                continue
            lines.append(line)

        if not lines:
            continue

        content = "\n".join(lines)
        content = re.sub(r"\\(?:toprule|midrule|bottomrule|hline)\b", "", content)
        content = re.sub(r"\\cmidrule(?:\([^)]*\))?\{[^{}]*\}", "", content)
        content = re.sub(r"\\addlinespace(?:\[[^\]]*\])?", "", content)
        row_chunks = re.split(r"\\\\(?:\[[^\]]*\])?", content)

        rows: list[list[str]] = []
        for chunk in row_chunks:
            raw = chunk.strip()
            if not raw:
                continue
            cells = [clean_latex_cell(cell) for cell in raw.split("&")]
            if any(cells):
                rows.append(cells)

        if len(rows) < 2:
            continue

        header = rows[0]
        data_rows = [row for row in rows[1:] if len(row) == len(header)]
        if data_rows:
            tables.append({"header": header, "rows": data_rows, "kind": "latex"})

    return tables


def candidate_tables(path: Path) -> list[dict]:
    if path.suffix.lower() == ".csv":
        return parse_csv_table(path)
    text = read_source(path)
    if path.suffix.lower() == ".tex":
        return parse_latex_tables(text)
    return parse_markdown_tables(text)


def score_table(table: dict) -> int:
    header = table.get("header", [])
    rows = table.get("rows", [])
    if len(header) < 2 or len(rows) < 2:
        return -1

    numeric_cols = 0
    for col in range(len(header)):
        values = [parse_number(row[col]) for row in rows if col < len(row)]
        if values and all(value is not None for value in values):
            numeric_cols += 1
    return len(rows) * 10 + numeric_cols * 5


def choose_table(tables: list[dict]) -> dict:
    ranked = sorted(tables, key=score_table, reverse=True)
    if not ranked or score_table(ranked[0]) < 0:
        raise ValueError("No usable numeric table found in the source.")
    return ranked[0]


def infer_chart_type(text: str, header: list[str], rows: list[list[str]]) -> str:
    lower = text.lower()
    if any(token in lower for token in ["line plot", "curve", "trend", "折线图"]):
        return "line"
    if any(token in lower for token in ["bar chart", "柱状图", "ablation"]):
        return "grouped-bar"

    first_col_numeric = all(parse_number(row[0]) is not None for row in rows if row)
    numeric_cols = sum(
        1
        for col in range(len(header))
        if all(parse_number(row[col]) is not None for row in rows if col < len(row))
    )
    if first_col_numeric and numeric_cols >= 2:
        return "line"
    return "grouped-bar"


def build_series(header: list[str], rows: list[list[str]], chart_type: str) -> tuple[str, list[str], list[dict]]:
    colors = ["#2358a5", "#2f855a", "#c05621", "#805ad5", "#b83280", "#2b6cb0"]

    if chart_type == "line" and all(parse_number(row[0]) is not None for row in rows if row):
        x_label = header[0]
        categories = [row[0] for row in rows]
        series_cols = [
            col
            for col in range(1, len(header))
            if all(parse_number(row[col]) is not None for row in rows if col < len(row))
        ]
    else:
        x_label = header[0]
        categories = [row[0] for row in rows]
        series_cols = [
            col
            for col in range(1, len(header))
            if all(parse_number(row[col]) is not None for row in rows if col < len(row))
        ]

    if not series_cols:
        raise ValueError("No numeric data series found in the selected table.")

    series = []
    for idx, col in enumerate(series_cols):
        series.append(
            {
                "name": header[col],
                "values": [parse_number(row[col]) for row in rows],
                "color": colors[idx % len(colors)],
            }
        )
    return x_label, categories, series


def build_spec(intent: dict, source_path: Path) -> dict:
    tables = candidate_tables(source_path)
    table = choose_table(tables)
    header = table["header"]
    rows = table["rows"]
    context_text = read_source(source_path) + "\n" + str(intent.get("story", {}).get("one_liner", ""))
    chart_type = infer_chart_type(context_text, header, rows)
    x_label, categories, series = build_series(header, rows, chart_type)

    y_values = [value for item in series for value in item["values"] if value is not None]
    if not y_values:
        raise ValueError("Selected table did not contain numeric values.")

    spec = {
        "title": intent.get("title", "Scientific Plot"),
        "chart_type": chart_type,
        "x_label": x_label,
        "y_label": series[0]["name"] if len(series) == 1 else "Value",
        "categories": categories,
        "series": series,
        "style": "academic-minimal",
        "source_path": str(source_path),
        "table_kind": table.get("kind", "unknown"),
        "notes": intent.get("must_keep_terms", []) or ["Generated from source table."],
    }
    return spec


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile figure_intent.yaml into a plot-ready YAML spec.")
    parser.add_argument("intent")
    parser.add_argument("-o", "--output")
    args = parser.parse_args()

    intent = yaml.safe_load(Path(args.intent).read_text(encoding="utf-8"))
    source_items = intent.get("source_artifacts", [])
    if not source_items:
        raise SystemExit("figure_intent.yaml did not provide a source artifact.")

    source_path = Path(source_items[0]["path"]).resolve()
    spec = build_spec(intent, source_path)
    payload = yaml.safe_dump(spec, allow_unicode=True, sort_keys=False)
    if args.output:
        Path(args.output).write_text(payload, encoding="utf-8")
    else:
        sys.stdout.write(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
