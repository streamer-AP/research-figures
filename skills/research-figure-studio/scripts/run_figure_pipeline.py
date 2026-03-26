#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import yaml


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def existing_backend_paths() -> dict[str, Path]:
    skills_root = Path(__file__).resolve().parents[2]
    return {
        "drawio_convert": skills_root / "drawio-architecture-diagram" / "scripts" / "verify_and_convert.py",
        "banana_render": skills_root / "banana-paper-illustration" / "scripts" / "generate_banana_illustration.py",
    }


def route_pipeline(script_dir: Path, source_file: str, request: str, route_path: Path) -> dict:
    run(
        [
            "python3",
            str(script_dir / "route_figure_backend.py"),
            "--source-file",
            source_file,
            "--request",
            request,
            "-o",
            str(route_path),
        ]
    )
    return yaml.safe_load(route_path.read_text(encoding="utf-8"))


def build_intent(
    script_dir: Path,
    source_file: str,
    request: str,
    figure_class: str,
    backend: str,
    intent_path: Path,
) -> dict:
    run(
        [
            "python3",
            str(script_dir / "build_figure_intent.py"),
            "--source-file",
            source_file,
            "--request",
            request,
            "--figure-class",
            figure_class,
            "--backend",
            backend,
            "-o",
            str(intent_path),
        ]
    )
    return yaml.safe_load(intent_path.read_text(encoding="utf-8"))


def render_drawio(
    script_dir: Path,
    backend_scripts: dict[str, Path],
    intent_path: Path,
    output_dir: Path,
) -> tuple[Path, list[Path]]:
    spec_path = output_dir / "figure.drawio_spec.yaml"
    drawio_path = output_dir / "figure.drawio"
    run(["python3", str(script_dir / "compile_drawio_package.py"), str(intent_path), "-o", str(spec_path)])
    run(["python3", str(backend_scripts["drawio_convert"]), str(spec_path), "-o", str(drawio_path)])
    return drawio_path, [spec_path, drawio_path]


def banana_mode_from_figure_class(figure_class: str) -> str:
    if figure_class in {"visual-abstract"}:
        return "visual-abstract"
    if figure_class in {"teaser"}:
        return "teaser"
    if figure_class in {"system-concept"}:
        return "system-concept"
    return "method-overview"


def render_banana(
    script_dir: Path,
    backend_scripts: dict[str, Path],
    intent_path: Path,
    output_dir: Path,
    figure_class: str,
    dry_run: bool,
) -> tuple[Path | None, list[Path]]:
    prompt_path = output_dir / "figure.prompt.txt"
    image_path = output_dir / "figure.png"
    run(["python3", str(script_dir / "compile_banana_prompt.py"), str(intent_path), "-o", str(prompt_path)])
    cmd = [
        "python3",
        str(backend_scripts["banana_render"]),
        "--prompt",
        prompt_path.read_text(encoding="utf-8"),
        "--mode",
        banana_mode_from_figure_class(figure_class),
        "--output",
        str(image_path),
    ]
    if dry_run:
        cmd.append("--dry-run")
    run(cmd)
    return (None if dry_run else image_path), [prompt_path] + ([] if dry_run else [image_path, image_path.with_suffix(image_path.suffix + ".prompt.txt")])


def render_plot(
    script_dir: Path,
    intent_path: Path,
    output_dir: Path,
) -> tuple[Path, list[Path]]:
    spec_path = output_dir / "figure.plot_spec.yaml"
    plot_path = output_dir / "figure.svg"
    plot_png_path = output_dir / "figure.png"
    run(["python3", str(script_dir / "compile_plot_package.py"), str(intent_path), "-o", str(spec_path)])
    run(["python3", str(script_dir / "render_plot_svg.py"), str(spec_path), "-o", str(plot_path)])
    run(["python3", str(script_dir / "render_plot_png.py"), str(spec_path), "-o", str(plot_png_path)])
    return plot_png_path, [spec_path, plot_path, plot_png_path]


def render_hybrid(
    script_dir: Path,
    backend_scripts: dict[str, Path],
    intent_path: Path,
    output_dir: Path,
) -> tuple[Path, list[Path]]:
    drawio_spec = output_dir / "figure.drawio_spec.yaml"
    drawio_path = output_dir / "figure.drawio"
    plot_spec = output_dir / "figure.plot_spec.yaml"
    plot_svg = output_dir / "figure.plot.svg"
    plot_png = output_dir / "figure.plot.png"
    preview_png = output_dir / "figure.hybrid_preview.png"

    run(["python3", str(script_dir / "compile_drawio_package.py"), str(intent_path), "-o", str(drawio_spec)])
    run(["python3", str(backend_scripts["drawio_convert"]), str(drawio_spec), "-o", str(drawio_path)])
    run(["python3", str(script_dir / "compile_plot_package.py"), str(intent_path), "-o", str(plot_spec)])
    run(["python3", str(script_dir / "render_plot_svg.py"), str(plot_spec), "-o", str(plot_svg)])
    run(["python3", str(script_dir / "render_plot_png.py"), str(plot_spec), "-o", str(plot_png)])
    run(
        [
            "python3",
            str(script_dir / "render_hybrid_preview.py"),
            "--drawio-spec",
            str(drawio_spec),
            "--plot-image",
            str(plot_png),
            "-o",
            str(preview_png),
        ]
    )
    return preview_png, [drawio_spec, drawio_path, plot_spec, plot_svg, plot_png, preview_png]


def verify(
    script_dir: Path,
    intent_path: Path,
    backend: str,
    artifact_path: Path | None,
    report_path: Path,
) -> dict:
    cmd = [
        "python3",
        str(script_dir / "verify_figure_result.py"),
        "--intent",
        str(intent_path),
        "--backend",
        backend,
        "-o",
        str(report_path),
    ]
    if artifact_path:
        cmd.extend(["--artifact", str(artifact_path)])
    completed = subprocess.run(cmd)
    report = yaml.safe_load(report_path.read_text(encoding="utf-8"))
    if completed.returncode not in (0, 2):
        raise RuntimeError("Verification script failed unexpectedly.")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the research-figure-studio pipeline end-to-end.")
    parser.add_argument("--source-file", required=True)
    parser.add_argument("--request", default="")
    parser.add_argument("--output-dir", default=".")
    parser.add_argument("--backend", choices=["drawio", "banana", "plot", "hybrid"])
    parser.add_argument("--figure-class")
    parser.add_argument("--dry-run", action="store_true", help="Prepare backend artifacts without live rendering when supported.")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    route_path = output_dir / "route.yaml"
    intent_path = output_dir / "figure_intent.yaml"
    verify_path = output_dir / "verification.yaml"
    bundle_path = output_dir / "bundle.yaml"

    backend_scripts = existing_backend_paths()
    route_data = route_pipeline(script_dir, args.source_file, args.request, route_path)

    figure_class = args.figure_class or str(route_data.get("figure_class", "method-overview"))
    backend = args.backend or str(route_data.get("backend", "drawio"))
    route_data["figure_class"] = figure_class
    route_data["backend"] = backend
    route_path.write_text(yaml.safe_dump(route_data, allow_unicode=True, sort_keys=False), encoding="utf-8")

    build_intent(script_dir, args.source_file, args.request, figure_class, backend, intent_path)

    produced_files: list[Path] = [route_path, intent_path]
    artifact_path: Path | None = None

    if backend == "drawio":
        artifact_path, artifacts = render_drawio(script_dir, backend_scripts, intent_path, output_dir)
        produced_files.extend(artifacts)
    elif backend == "banana":
        artifact_path, artifacts = render_banana(script_dir, backend_scripts, intent_path, output_dir, figure_class, args.dry_run)
        produced_files.extend(artifacts)
    elif backend == "plot":
        artifact_path, artifacts = render_plot(script_dir, intent_path, output_dir)
        produced_files.extend(artifacts)
    elif backend == "hybrid":
        artifact_path, artifacts = render_hybrid(script_dir, backend_scripts, intent_path, output_dir)
        produced_files.extend(artifacts)
    else:
        raise SystemExit(f"Unsupported backend: {backend}")

    verification = verify(script_dir, intent_path, backend, artifact_path, verify_path)
    produced_files.append(verify_path)

    bundle = {
        "figure_class": figure_class,
        "backend": backend,
        "route_file": str(route_path),
        "intent_file": str(intent_path),
        "artifact": str(artifact_path) if artifact_path else None,
        "verification_file": str(verify_path),
        "verification_status": verification.get("status"),
        "produced_files": [str(path) for path in produced_files],
    }
    bundle_path.write_text(yaml.safe_dump(bundle, allow_unicode=True, sort_keys=False), encoding="utf-8")
    produced_files.append(bundle_path)

    for path in produced_files:
        print(path)
    return 0 if verification.get("status") == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
