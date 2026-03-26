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
ERROR_TOKENS = {"std", "stderr", "error", "err", "ci", "conf", "interval", "deviation", "uncertainty"}
VALUE_TOKENS = {"mean", "avg", "average", "value", "score"}
HELPER_NUMERIC_HEADERS = {"index", "idx", "id", "rank", "step id"}
DUAL_AXIS_HINTS = {"dual axis", "dual-axis", "secondary axis", "right axis", "left axis", "双轴", "双y", "双y轴"}
LOG_X_HINTS = {"log x", "log-x", "x log", "semilogx", "对数x", "横轴对数"}
LOG_Y_HINTS = {"log y", "log-y", "y log", "semilogy", "纵轴对数", "对数y"}
LOG_BOTH_HINTS = {"log-log", "log scale", "log-scale", "双对数", "对数坐标"}


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


def parse_measure(value: str) -> tuple[float | None, float | None]:
    text = str(value).strip().replace(",", "")
    if not text:
        return None, None
    if text.endswith("%"):
        text = text[:-1]

    match = re.fullmatch(
        r"([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\s*(?:±|\+/-|\+-)\s*([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)",
        text,
    )
    if match:
        return float(match.group(1)), abs(float(match.group(2)))

    simple = parse_number(text)
    return simple, None


def is_numeric_column(rows: list[list[str]], col: int) -> bool:
    values = [parse_measure(row[col])[0] for row in rows if col < len(row)]
    return bool(values) and all(value is not None for value in values)


def split_markdown_row(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [cell.strip() for cell in stripped.split("|")]


def is_separator_row(cells: list[str]) -> bool:
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell or "") for cell in cells)


def parse_csv_table(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        rows = list(csv.reader(handle))
    if len(rows) < 2:
        return []
    header = [cell.strip() for cell in rows[0]]
    data_rows = [[cell.strip() for cell in row] for row in rows[1:] if any(cell.strip() for cell in row)]
    return [{"header": header, "rows": data_rows, "kind": "csv"}] if data_rows else []


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
    return re.sub(r"\s+", " ", str(text).strip()).strip(":.- ")


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
    if any(token in lower for token in ["line plot", "curve", "trend", "scaling law", "折线图", "双轴", "dual axis"]):
        return "line"
    if any(token in lower for token in ["bar chart", "柱状图", "ablation"]):
        return "grouped-bar"
    first_col_numeric = all(parse_measure(row[0])[0] is not None for row in rows if row)
    numeric_cols = [col for col in range(len(header)) if is_numeric_column(rows, col)]
    if first_col_numeric and len(numeric_cols) >= 2:
        return "line"
    return "grouped-bar"


def choose_x_axis(header: list[str], rows: list[list[str]], request_text: str) -> tuple[str, list[str], list[int]]:
    lower = normalize_text(request_text)
    col_count = len(header)
    numeric_cols = [col for col in range(col_count) if is_numeric_column(rows, col)]
    non_numeric_cols = [col for col in range(col_count) if col not in numeric_cols]

    if len(header) >= 3:
        date_col = next((idx for idx, name in enumerate(header) if "date" in normalize_text(name)), None)
        time_col = next((idx for idx, name in enumerate(header) if "hour" in normalize_text(name) or "time" in normalize_text(name)), None)
        if date_col is not None and time_col is not None and any(token in lower for token in ["time", "hour", "trend", "timeline", "over time", "hourly"]):
            return "Time", [f"{row[date_col]} {row[time_col]}".strip() for row in rows], [date_col, time_col]

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
    pattern = re.compile(r"(?P<date>\d{4}[-/]\d{2}[-/]\d{2})\s+(?P<time>\d{2}:\d{2}(?::\d{2})?)")
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
    reduced = []
    for label in shorten_time_labels(labels):
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


def metric_key(name: str) -> str:
    lower = normalize_text(name)
    lower = re.sub(r"[()\[\]{}]", " ", lower)
    tokens = re.findall(r"[a-zA-Z]+|[\u4e00-\u9fff]+", lower)
    filtered = [token for token in tokens if token not in ERROR_TOKENS and token not in VALUE_TOKENS]
    return " ".join(filtered).strip()


def is_error_like_header(name: str) -> bool:
    lower = normalize_text(name)
    return "±" in lower or any(token in lower for token in ERROR_TOKENS)


def build_error_column_map(header: list[str], rows: list[list[str]], excluded_cols: list[int]) -> dict[int, int]:
    base_candidates: dict[str, list[int]] = {}
    error_candidates: dict[str, list[int]] = {}
    for col, name in enumerate(header):
        if col in excluded_cols or not is_numeric_column(rows, col):
            continue
        if normalize_text(name) in HELPER_NUMERIC_HEADERS:
            continue
        key = metric_key(name)
        if not key:
            continue
        target = error_candidates if is_error_like_header(name) else base_candidates
        target.setdefault(key, []).append(col)

    mapping: dict[int, int] = {}
    for key, base_cols in base_candidates.items():
        if key not in error_candidates:
            continue
        for base_col, error_col in zip(base_cols, error_candidates[key]):
            mapping[base_col] = error_col
    return mapping


def choose_series_cols(header: list[str], rows: list[list[str]], excluded_cols: list[int], request_text: str) -> list[int]:
    lower = normalize_text(request_text)
    numeric_cols = []
    for col, name in enumerate(header):
        if col in excluded_cols or not is_numeric_column(rows, col):
            continue
        if normalize_text(name) in HELPER_NUMERIC_HEADERS:
            continue
        if is_error_like_header(name):
            continue
        numeric_cols.append(col)
    if not numeric_cols:
        return []
    if any(token in lower for token in ["vs", "compare", "comparison", "baseline", "improved", "law", "trend", "dual axis", "双轴"]):
        return numeric_cols[: min(4, len(numeric_cols))]
    if any(token in lower for token in ["single metric", "single line", "single curve"]):
        return numeric_cols[:1]
    return numeric_cols[: min(5, len(numeric_cols))]


def infer_y_label(series_names: list[str]) -> str:
    if len(series_names) == 1:
        return series_names[0]
    lower_names = [normalize_text(name) for name in series_names]
    for hint, label in [("iou", "IoU"), ("accuracy", "Accuracy"), ("loss", "Loss"), ("latency", "Latency")]:
        if all(hint in name for name in lower_names):
            return label
    suffixes = set()
    for name in series_names:
        parts = normalize_text(name).split()
        if parts:
            suffixes.add(parts[-1])
    if len(suffixes) == 1:
        suffix = next(iter(suffixes))
        return suffix.upper() if len(suffix) <= 4 else suffix.title()
    return "Value"


def prefers_lower(metric_text: str, fallback_text: str = "") -> bool:
    primary = normalize_text(metric_text)
    if any(token in primary for token in MINIMIZE_TOKENS):
        return True
    if any(token in primary for token in MAXIMIZE_TOKENS):
        return False
    secondary = normalize_text(fallback_text)
    if any(token in secondary for token in MAXIMIZE_TOKENS):
        return False
    return any(token in secondary for token in MINIMIZE_TOKENS)


def infer_scales(request_text: str, chart_type: str, categories: list[str], series: list[dict]) -> tuple[str, str]:
    lower = normalize_text(request_text)
    x_scale = "linear"
    y_scale = "linear"

    numeric_categories = all(parse_number(category) is not None for category in categories)
    all_values = [value for item in series for value in item["values"] if value is not None]
    positive_values = [value for value in all_values if value > 0]

    if any(token in lower for token in LOG_BOTH_HINTS):
        if numeric_categories and chart_type in {"line", "scatter"} and all(parse_number(category) > 0 for category in categories):
            x_scale = "log"
        if len(positive_values) == len(all_values) and all_values:
            y_scale = "log"
    else:
        if any(token in lower for token in LOG_X_HINTS | {"scaling law"}):
            if numeric_categories and chart_type in {"line", "scatter"} and all(parse_number(category) > 0 for category in categories):
                x_scale = "log"
        if any(token in lower for token in LOG_Y_HINTS):
            if len(positive_values) == len(all_values) and all_values:
                y_scale = "log"
    return x_scale, y_scale


def should_use_dual_axis(request_text: str, series: list[dict]) -> bool:
    lower = normalize_text(request_text)
    if any(token in lower for token in DUAL_AXIS_HINTS):
        return len(series) >= 2
    if len(series) != 2:
        return False

    names = [normalize_text(item["name"]) for item in series]
    left_values = [abs(value) for value in series[0]["values"] if value is not None]
    right_values = [abs(value) for value in series[1]["values"] if value is not None]
    if not left_values or not right_values:
        return False
    ratio = max(max(left_values), max(right_values)) / max(1e-9, min(max(left_values), max(right_values)))
    semantic_conflict = any(token in names[0] for token in MAXIMIZE_TOKENS | MINIMIZE_TOKENS) and any(
        token in names[1] for token in {"latency", "time", "memory", "params", "throughput"}
    )
    semantic_conflict = semantic_conflict or (
        any(token in names[1] for token in MAXIMIZE_TOKENS | MINIMIZE_TOKENS)
        and any(token in names[0] for token in {"latency", "time", "memory", "params", "throughput"})
    )
    return ratio >= 8 and semantic_conflict


def assign_axes(request_text: str, series: list[dict]) -> tuple[str, str | None]:
    for item in series:
        item["axis"] = "left"
    if not should_use_dual_axis(request_text, series):
        return "left", None
    # Keep the first series on the left axis and move the second to the right axis.
    series[1]["axis"] = "right"
    return "left-right", series[1]["name"]


def annotate_series(series: list[dict], chart_type: str, y_label: str, secondary_y_label: str | None = None) -> list[dict]:
    if chart_type not in {"line", "scatter"}:
        return []
    annotations = []
    for item in series:
        values = item["values"]
        if not values:
            continue
        axis_label = secondary_y_label if item.get("axis") == "right" and secondary_y_label else y_label
        lower_is_better = prefers_lower(item["name"], axis_label)
        best_idx = min(range(len(values)), key=lambda idx: values[idx]) if lower_is_better else max(range(len(values)), key=lambda idx: values[idx])
        prefix = "best" if lower_is_better else "peak"
        annotations.append(
            {
                "series": item["name"],
                "type": "best" if lower_is_better else "peak",
                "index": best_idx,
                "value": values[best_idx],
                "label": f"{prefix} {values[best_idx]:.2f}".rstrip("0").rstrip("."),
            }
        )
    return annotations


def build_series(header: list[str], rows: list[list[str]], request_text: str) -> tuple[str, list[str], list[dict]]:
    x_label, categories, excluded_cols = choose_x_axis(header, rows, request_text)
    series_cols = choose_series_cols(header, rows, excluded_cols, request_text)
    if not series_cols:
        raise ValueError("No numeric data series found in the selected table.")

    error_map = build_error_column_map(header, rows, excluded_cols)
    series = []
    for idx, col in enumerate(series_cols):
        values = []
        inline_errors = []
        for row in rows:
            value, error = parse_measure(row[col])
            values.append(value)
            inline_errors.append(error)

        separate_error_values = None
        if col in error_map:
            separate_error_values = [parse_measure(row[error_map[col]])[0] for row in rows]

        error_values = inline_errors if any(item is not None for item in inline_errors) else separate_error_values
        series_item = {
            "name": header[col],
            "values": values,
            "color": PALETTE[idx % len(PALETTE)],
            "marker": LINE_MARKERS[idx % len(LINE_MARKERS)],
        }
        if error_values and any(item is not None for item in error_values):
            series_item["error_values"] = error_values
        series.append(series_item)
    return x_label, categories, series


def build_spec(intent: dict, source_path: Path) -> dict:
    request_text = str(intent.get("story", {}).get("one_liner", ""))
    source_text = read_source(source_path)
    tables = candidate_tables(source_path)
    table = choose_table(tables, request_text + "\n" + source_text)
    header = table["header"]
    rows = table["rows"]
    context_text = source_text + "\n" + request_text
    chart_type = infer_chart_type(context_text, header, rows)
    x_label, categories, series = build_series(header, rows, request_text)

    all_values = [value for item in series for value in item["values"] if value is not None]
    if not all_values:
        raise ValueError("Selected table did not contain numeric values.")

    axis_mode, secondary_y_label = assign_axes(request_text, series)
    x_scale, y_scale = infer_scales(request_text, chart_type, categories, series)

    left_names = [item["name"] for item in series if item.get("axis") != "right"]
    right_names = [item["name"] for item in series if item.get("axis") == "right"]
    left_y_label = infer_y_label(left_names) if left_names else "Value"
    right_y_label = infer_y_label(right_names) if right_names else None

    tick_indices, rotate_ticks, tick_labels = choose_tick_indices(categories, chart_type)
    spec = {
        "title": infer_title(intent, source_path, source_text),
        "chart_type": chart_type,
        "x_label": x_label,
        "y_label": left_y_label,
        "secondary_y_label": right_y_label or secondary_y_label,
        "axis_mode": axis_mode,
        "x_scale": x_scale,
        "y_scale": y_scale,
        "categories": categories,
        "tick_indices": tick_indices,
        "tick_labels": [tick_labels[idx] for idx in tick_indices],
        "rotate_ticks": rotate_ticks,
        "series": series,
        "style": "academic-polished",
        "source_path": str(source_path),
        "table_kind": table.get("kind", "unknown"),
        "notes": intent.get("must_keep_terms", []) or ["Generated from source table."],
        "annotations": annotate_series(series, chart_type, left_y_label, right_y_label or secondary_y_label),
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
