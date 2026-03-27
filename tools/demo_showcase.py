#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PIPELINE = ROOT / "skills" / "research-figure-studio" / "scripts" / "run_figure_pipeline.py"


def has_banana_key() -> bool:
    return bool(os.getenv("BANANA_API_KEY") or os.getenv("API_KEY"))


def run_job(name: str, cmd: list[str], allowed_codes: set[int]) -> None:
    print(f"[run] {name}", flush=True)
    print("      " + " ".join(cmd), flush=True)
    completed = subprocess.run(cmd, cwd=ROOT)
    if completed.returncode not in allowed_codes:
        raise RuntimeError(f"{name} failed with exit code {completed.returncode}")
    print(f"[done] {name} -> exit {completed.returncode}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a reproducible local showcase for research-figures.")
    parser.add_argument("--output-dir", default="out/showcase_demo")
    parser.add_argument("--offline", action="store_true", help="Force Banana to dry-run mode even if an API key exists.")
    args = parser.parse_args()

    output_dir = (ROOT / args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    banana_dry_run = args.offline or not has_banana_key()
    banana_status = "dry-run" if banana_dry_run else "live-render"

    jobs = [
        (
            "plot_scaling_law",
            [
                "python3",
                str(PIPELINE),
                "--source-file",
                str(ROOT / "examples" / "showcase" / "ml_theory_scaling_law.md"),
                "--request",
                "generate a scaling law line plot",
                "--output-dir",
                str(output_dir / "plot_scaling_law"),
            ],
            {0},
        ),
        (
            "drawio_flac_pipeline",
            [
                "python3",
                str(PIPELINE),
                "--source-file",
                str(ROOT / "examples" / "drawio" / "flac_metadata_pipeline.md"),
                "--request",
                "generate an editable architecture diagram",
                "--output-dir",
                str(output_dir / "drawio_flac_pipeline"),
            ],
            {0},
        ),
        (
            "hybrid_corridor_results",
            [
                "python3",
                str(PIPELINE),
                "--source-file",
                str(ROOT / "examples" / "hybrid" / "corridor_results_hybrid.md"),
                "--request",
                "generate a hybrid figure with structure and result chart",
                "--output-dir",
                str(output_dir / "hybrid_corridor_results"),
            ],
            {0},
        ),
        (
            f"banana_cv_visual_{banana_status}",
            [
                "python3",
                str(PIPELINE),
                "--source-file",
                str(ROOT / "examples" / "showcase" / "cv_multiscale_segmentation_visual.md"),
                "--request",
                "generate a visual abstract",
                "--backend",
                "banana",
                "--figure-class",
                "visual-abstract",
                "--output-dir",
                str(output_dir / "banana_cv_visual"),
            ]
            + (["--dry-run"] if banana_dry_run else []),
            {0, 2} if banana_dry_run else {0},
        ),
    ]

    for name, cmd, allowed_codes in jobs:
        run_job(name, cmd, allowed_codes)

    print()
    print("Showcase ready:", flush=True)
    print(f"- output root: {output_dir}", flush=True)
    print("- plot demo: " + str(output_dir / "plot_scaling_law"), flush=True)
    print("- drawio demo: " + str(output_dir / "drawio_flac_pipeline"), flush=True)
    print("- hybrid demo: " + str(output_dir / "hybrid_corridor_results"), flush=True)
    print("- banana demo: " + str(output_dir / "banana_cv_visual"), flush=True)
    print(f"- banana mode: {banana_status}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
