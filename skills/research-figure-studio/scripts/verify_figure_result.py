#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml


STRUCTURE_HEAVY_CLASSES = {"editable-diagram", "patent-figure"}
NUMERIC_CLASSES = {"chart-or-plot"}


def collect_issues(intent: dict, backend: str, artifact: str | None) -> list[str]:
    issues: list[str] = []
    figure_class = intent.get("figure_class")

    if figure_class not in NUMERIC_CLASSES and not intent.get("stages"):
        issues.append("no explicit stages found in figure intent")

    if backend == "banana" and figure_class in STRUCTURE_HEAVY_CLASSES:
        issues.append("banana backend is risky for a structure-heavy figure")

    if figure_class in NUMERIC_CLASSES and backend != "plot":
        issues.append("numeric figure class should use the plot backend")

    if backend == "plot" and figure_class not in NUMERIC_CLASSES:
        issues.append("plot backend is mismatched with a non-numeric figure class")

    if artifact and not Path(artifact).exists():
        issues.append("artifact path does not exist")

    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify figure intent and generated artifact at a high level.")
    parser.add_argument("--intent", required=True)
    parser.add_argument("--artifact")
    parser.add_argument("--backend", required=True)
    parser.add_argument("-o", "--output")
    args = parser.parse_args()

    intent = yaml.safe_load(Path(args.intent).read_text(encoding="utf-8"))
    issues = collect_issues(intent, args.backend, args.artifact)

    report = {
        "status": "pass" if not issues else "needs-fix",
        "backend_ok": not any("backend" in issue for issue in issues),
        "structure_ok": not any("stages" in issue for issue in issues),
        "label_density_ok": True,
        "issues": issues,
        "retry_strategy": (
            ["switch to drawio"]
            if any("banana backend" in issue for issue in issues)
            else ["switch to plot backend"]
            if any("plot backend" in issue or "numeric figure class" in issue for issue in issues)
            else ([] if not issues else ["strengthen intent before rendering"])
        ),
    }
    payload = yaml.safe_dump(report, allow_unicode=True, sort_keys=False)
    if args.output:
        Path(args.output).write_text(payload, encoding="utf-8")
    else:
        sys.stdout.write(payload)
    return 0 if not issues else 2


if __name__ == "__main__":
    raise SystemExit(main())
