#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml


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
    return "Untitled Figure Source"


def detect_abstract(text: str) -> str:
    m = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", text, re.S)
    if m:
        return re.sub(r"\s+", " ", m.group(1)).strip()
    return ""


def extract_stages(text: str) -> list[dict]:
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
        short = clean[:80]
        stages.append(
            {
                "id": f"stage_{len(stages)+1}",
                "label": short,
                "purpose": short,
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


def extract_terms(text: str) -> list[str]:
    candidates = []
    for phrase in [
        "whole-scene coarse inference",
        "template prior",
        "sparse fine refinement",
        "confidence-gated fusion",
        "focal loss",
        "prototype-guided contrastive learning",
    ]:
        if phrase.lower() in text.lower():
            candidates.append(phrase)
    return candidates


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract figure-relevant scientific content from source text.")
    parser.add_argument("--source-file", required=True)
    parser.add_argument("-o", "--output")
    args = parser.parse_args()

    text = read_text(args.source_file)
    result = {
        "title": detect_title(text),
        "abstract_summary": detect_abstract(text)[:500],
        "stages": extract_stages(text),
        "must_keep_terms": extract_terms(text),
    }
    payload = yaml.safe_dump(result, allow_unicode=True, sort_keys=False)
    if args.output:
        Path(args.output).write_text(payload, encoding="utf-8")
    else:
        sys.stdout.write(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
