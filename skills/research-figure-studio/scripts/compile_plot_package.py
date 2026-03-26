#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import csv
import math
import re
import sys
from pathlib import Path

import yaml


PALETTE = [
    "#2358A5",
    "#2F855A",
    "#C05621",
    "#805AD5",
    "#B83280",
    "#2B6CB0",
]

LINE_MARKERS = ["circle", "square", "diamond", "triangle", "cross", "hex"]
MINIMIZE_TOKENS = {"loss", "error", "perplexity", "latency", "rmse", "mae", "mse", "nll", "wer", "cer"}
MAXIMIZE_TOKENS = {"accuracy", "acc", "iou", "miou", "f1", "precision", "recall", "auc", "bleu", "rouge", "score"}


def read_source(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text).strip()).lower()


def tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z]+|\d+(?:\.\d+)?|[\u4e00-\u9fff]+", normalize_text(text)))


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


def is_numeric_column(rows: list[list[str]], col: int) -> bool:
    values = [parse_number(row[col]) for row in rows if col < len(row)]
    return bool(values) and all(value is not None for value in values)


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


def clean_title(text: str) -> str:
    value = re.sub(r"\s+", " ", str(text).strip()).strip(":.- ")
    return value


def extract_markdown_title(text: str) -> str | None:
    match = re.search(r"^\s*#\s+(.+?)\s*$", text, flags=re.M)
    return clean_title(match.group(1)) if match else None


def extract_latex_caption(text: str) -> str | None:
    match = re.search(r"\\caption\{([^{}]+)\}", strip_latex_comments(text), flags=re.S)
    return clean_title(clean_latex_cell(match.group(1))) if match else None


def infer_title(intent: dict, source_path: Path, source_text: str) -> str:
    existing = clean_title(intent.get("title", ""))
    if existing and existing.lower() != "untitled figure":
        return existing

    if source_path.suffix.lower() == ".tex":
        latex_title = extract_latex_caption(source_text)
        if latex_title:
            return latex_title

    markdown_title = extract_markdown_title(source_text)
    if markdown_title:
        return markdown_title

    return clean_title(source_path.stem.replace("_", " ").replace("-", " ").title()) or "Scientific Plot"


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


def score_table(table: dict, request_text: str) -> int:
    header = table.get("header", [])
    rows = table.get("rows", [])
    if len(header) < 2 or len(rows) < 2:
        return -1

    numeric_cols = [col for col in range(len(header)) if is_numeric_column(rows, col)]
    if not numeric_cols:
        return -1

    request_tokens = tokenize(request_text)
    header_tokens = [tokenize(cell) for cell in header]
    keyword_hits = sum(len(tokens & request_tokens) for tokens in header_tokens)
    width_bonus = min(len(rows), 24) * 2 + len(numeric_cols) * 8
    return width_bonus + keyword_hits * 4


def choose_table(tables: list[dict], request_text: str) -> dict:
    ranked = sorted(tables, key=lambda table: score_table(table, request_text), reverse=True)
    if not ranked or score_table(ranked[0], request_text) < 0:
        raise ValueError("No usable numeric table found in the source.")
    return ranked[0]


def infer_chart_type(text: str, header: list[str], rows: list[list[str]]) -> str:
    lower = normalize_text(text)
    if any(token in lower for token in ["scatter", "scatter plot", "散点图"]):
        return "scatter"
    if any(token in lower for token in ["stacked bar", "stacked", "堆叠柱状图"]):
        return "stacked-bar"
    if any(token in lower for token in ["line plot", "curve", "trend", "scaling law", "折线图"]):
        return "line"
    if any(token in lower for token in ["bar chart", "柱状图", "ablation"]):
        return "grouped-bar"

    first_col_numeric = all(parse_number(row[0]) is not None for row in rows if row)
    numeric_cols = [col for col in range(len(header)) if is_numeric_column(rows, col)]
    if first_col_numeric and len(numeric_cols) >= 2:
        return "line"
    return "grouped-bar"


def choose_x_axis(header: list[str], rows: list[list[str]], request_text: str) -> tuple[str, list[str], list[int]]:
    lower = normalize_text(request_text)
    col_count = len(header)
    numeric_cols = [col for col in range(col_count) if is_numeric_column(rows, col)]
    non_numeric_cols = [col for col in range(col_count) if col not in numeric_cols]

    # Prefer combined date + time labels when the request implies a time series.
    if len(header) >= 3:
        date_col = next((idx for idx, name in enumerate(header) if "date" in normalize_text(name)), None)
        time_col = next((idx for idx, name in enumerate(header) if "hour" in normalize_text(name) or "time" in normalize_text(name)), None)
        if date_col is not None and time_col is not None and any(token in lower for token in ["time", "hour", "trend", "timeline", "over time", "hourly"]):
            categories = [f"{row[date_col]} {row[time_col]}".strip() for row in rows]
            return "Time", categories, [date_col, time_col]

    if any(token in lower for token in ["time", "hour", "trend", "timeline", "over time", "epoch", "step"]):
        for idx, name in enumerate(header):
            norm = normalize_text(name)
            if any(token in norm for token in ["time", "hour", "epoch", "step", "iteration", "date"]):
                return header[idx], [row[idx] for row in rows], [idx]

    for idx in non_numeric_cols:
        if idx == 0:
            return header[idx], [row[idx] for row in rows], [idx]

    return header[0], [row[0] for row in rows], [0]


def shorten_time_labels(labels: list[str]) -> list[str]:
    pattern = re.compile(
        r"(?P<date>\d{4}[-/]\d{2}[-/]\d{2})\s+(?P<time>\d{2}:\d{2}(?::\d{2})?)"
    )
    matches = [pattern.fullmatch(str(label).strip()) for label in labels]
    if not labels or not all(matches):
        return [str(label) for label in labels]

    dates = [match.group("date").replace("/", "-") for match in matches if match]
    same_date = len(set(dates)) == 1
    shortened = []
    for match in matches:
        assert match is not None
        date = match.group("date").replace("/", "-")
        time = match.group("time")[:5]
        shortened.append(time if same_date else f"{date[5:]} {time}")
    return shortened


def compact_labels(labels: list[str]) -> list[str]:
    compact = shorten_time_labels(labels)
    reduced = []
    for label in compact:
        text = str(label)
        if len(text) > 18:
            text = text[:15].rstrip() + "..."
        reduced.append(text)
    return reduced


def choose_tick_indices(labels: list[str], chart_type: str) -> tuple[list[int], bool, list[str]]:
    if not labels:
        return [], False, []

    display_labels = compact_labels(labels)
    count = len(display_labels)
    max_ticks = 6 if chart_type in {"line", "scatter"} else 8
    if any(len(label) > 14 for label in display_labels):
        max_ticks = min(max_ticks, 5)

    if count <= max_ticks:
        indices = list(range(count))
    else:
        step = max(1, math.ceil((count - 1) / max(1, max_ticks - 1)))
        indices = list(range(0, count, step))
        if indices[-1] != count - 1:
            indices.append(count - 1)
        indices = sorted(set(indices))

    rotate = count > 7 or any(len(label) > 10 for label in display_labels)
    return indices, rotate, display_labels


def choose_series_cols(header: list[str], rows: list[list[str]], excluded_cols: list[int], request_text: str) -> list[int]:
    lower = normalize_text(request_text)
    numeric_cols = []
    for col in range(len(header)):
        if col in excluded_cols or not is_numeric_column(rows, col):
            continue
        name = normalize_text(header[col])
        if name in {"index", "idx", "id", "rank", "step id"}:
            continue
        numeric_cols.append(col)
    if not numeric_cols:
        return []

    if any(token in lower for token in ["vs", "compare", "comparison", "baseline", "improved", "law", "trend"]):
        return numeric_cols[: min(4, len(numeric_cols))]

    if any(token in lower for token in ["single metric", "single line", "single curve"]):
        return numeric_cols[:1]

    return numeric_cols[: min(5, len(numeric_cols))]


def infer_y_label(series_names: list[str]) -> str:
    if len(series_names) == 1:
        return series_names[0]
    suffixes = set()
    for name in series_names:
        parts = normalize_text(name).split()
        if parts:
            suffixes.add(parts[-1])
    if len(suffixes) == 1:
        suffix = next(iter(suffixes))
        return suffix.upper() if len(suffix) <= 4 else suffix.title()
    return "Value"


def prefers_lower(metric_text: str) -> bool:
    lower = normalize_text(metric_text)
    if any(token in lower for token in MAXIMIZE_TOKENS):
        return False
    return any(token in lower for token in MINIMIZE_TOKENS)


def annotate_series(series: list[dict], chart_type: str, y_label: str) -> list[dict]:
    if not series:
        return []

    annotations: list[dict] = []
    if chart_type in {"line", "scatter"}:
        for item in series:
            values = item["values"]
            lower_is_better = prefers_lower(f"{item['name']} {y_label}")
            best_idx = (
                min(range(len(values)), key=lambda idx: values[idx])
                if lower_is_better
                else max(range(len(values)), key=lambda idx: values[idx])
            )
            label_prefix = "best" if lower_is_better else "peak"
            annotations.append(
                {
                    "series": item["name"],
                    "type": "best" if lower_is_better else "peak",
                    "index": best_idx,
                    "value": values[best_idx],
                    "label": f"{label_prefix} {values[best_idx]:.2f}".rstrip("0").rstrip("."),
                }
            )
    return annotations


def build_series(
    header: list[str],
    rows: list[list[str]],
    chart_type: str,
    request_text: str,
) -> tuple[str, list[str], list[dict], list[int]]:
    x_label, categories, excluded_cols = choose_x_axis(header, rows, request_text)
    series_cols = choose_series_cols(header, rows, excluded_cols, request_text)

    if not series_cols:
        raise ValueError("No numeric data series found in the selected table.")

    series = []
    for idx, col in enumerate(series_cols):
        series.append(
            {
                "name": header[col],
                "values": [parse_number(row[col]) for row in rows],
                "color": PALETTE[idx % len(PALETTE)],
                "marker": LINE_MARKERS[idx % len(LINE_MARKERS)],
            }
        )
    return x_label, categories, series, excluded_cols


def build_spec(intent: dict, source_path: Path) -> dict:
    request_text = str(intent.get("story", {}).get("one_liner", ""))
    source_text = read_source(source_path)
    tables = candidate_tables(source_path)
    table = choose_table(tables, request_text + "\n" + source_text)
    header = table["header"]
    rows = table["rows"]
    context_text = source_text + "\n" + request_text
    chart_type = infer_chart_type(context_text, header, rows)
    x_label, categories, series, _ = build_series(header, rows, chart_type, request_text)

    y_values = [value for item in series for value in item["values"] if value is not None]
    if not y_values:
        raise ValueError("Selected table did not contain numeric values.")

    series_names = [item["name"] for item in series]
    y_label = infer_y_label(series_names)
    tick_indices, rotate_ticks, tick_labels = choose_tick_indices(categories, chart_type)
    spec = {
        "title": infer_title(intent, source_path, source_text),
        "chart_type": chart_type,
        "x_label": x_label,
        "y_label": y_label,
        "categories": categories,
        "tick_indices": tick_indices,
        "tick_labels": [tick_labels[idx] for idx in tick_indices],
        "rotate_ticks": rotate_ticks,
        "series": series,
        "style": "academic-polished",
        "source_path": str(source_path),
        "table_kind": table.get("kind", "unknown"),
        "notes": intent.get("must_keep_terms", []) or ["Generated from source table."],
        "annotations": annotate_series(series, chart_type, y_label),
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
