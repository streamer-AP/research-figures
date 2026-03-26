#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify a diagram spec and convert it to a draw.io file.")
    parser.add_argument("source", help="Path to a YAML spec file or a Markdown file with a fenced YAML block.")
    parser.add_argument("-o", "--output", help="Output .drawio path.")
    parser.add_argument("--from-markdown", action="store_true", help="Force Markdown mode.")
    parser.add_argument("--from-yaml", action="store_true", help="Force raw YAML mode.")
    parser.add_argument("--allow-warnings", action="store_true", help="Generate draw.io output even if verification reports warnings but no hard errors.")
    args = parser.parse_args()

    if args.from_markdown and args.from_yaml:
        parser.error("Choose only one of --from-markdown or --from-yaml.")

    script_dir = Path(__file__).resolve().parent
    verifier = script_dir / "verify_diagram_spec.py"
    converter = script_dir / "spec_to_drawio.py"

    verify_cmd = ["python3", str(verifier), args.source]
    convert_cmd = ["python3", str(converter), args.source]

    if args.output:
        convert_cmd.extend(["-o", args.output])
    if args.from_markdown:
        verify_cmd.append("--from-markdown")
        convert_cmd.append("--from-markdown")
    if args.from_yaml:
        verify_cmd.append("--from-yaml")
        convert_cmd.append("--from-yaml")

    verify_proc = subprocess.run(verify_cmd)
    if verify_proc.returncode == 1:
        return 1
    if verify_proc.returncode == 2 and not args.allow_warnings:
        print("[verify_and_convert] Verification returned needs-fix. Use --allow-warnings to convert anyway.", file=sys.stderr)
        return 2

    convert_proc = subprocess.run(convert_cmd)
    return convert_proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
