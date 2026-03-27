---
name: research-figure-studio
description: Generate scientific figures from papers, LaTeX manuscripts, patent drafts, method descriptions, and technical notes by routing requests to the correct backend. Use when Codex needs to create an editable architecture diagram, a publication-style method figure, a visual abstract, a teaser illustration, a patent figure, or a quantitative plot, and when backend selection, scientific content extraction, and figure verification matter as much as the final rendering.
---

# Research Figure Studio

Route scientific figure requests to the right backend and normalize them into a shared figure plan.

Use this skill as the top-level orchestrator. Do not force every figure through one rendering path.

## Workflow

For the normal one-click path, prefer:

```bash
python3 scripts/run_figure_pipeline.py --source-file paper.tex --request "生成投稿用方法图" --output-dir out
```

This wrapper will:

- route the figure request
- build `figure_intent.yaml`
- compile backend-ready artifacts
- invoke the installed backend skill
- verify the result
- compile a paper-ready caption file, with source-aware fallback when the intent is thin
- write `bundle.yaml`

### 1. Route The Figure

Determine the figure class first.

Use:

- `editable-diagram`
- `method-overview`
- `visual-abstract`
- `teaser`
- `system-concept`
- `chart-or-plot`
- `patent-figure`
- `hybrid-figure`

Then choose the backend:

- `drawio` for strict structure and editable topology
- `banana` for image-first paper illustrations
- `plot` for quantitative charts and metrics
- `hybrid` when structure and visual polish are both required

Use:

```bash
python3 scripts/route_figure_backend.py --request "根据这篇论文生成方法图" --source-file paper.tex
```

Read:

- [references/figure-classes.md](references/figure-classes.md)
- [references/backend-routing.md](references/backend-routing.md)

### 2. Extract Scientific Structure

Extract only the figure-relevant scientific content:

- title
- task
- inputs
- outputs
- main stages
- branches
- feedback loops
- must-keep terms

Do not dump the entire paper into a prompt.

Use:

```bash
python3 scripts/extract_scientific_figure_content.py --source-file paper.tex
```

### 3. Build The Shared Figure Intent

Convert the routed task and extracted content into `figure_intent.yaml`.

This file is the shared contract between understanding and rendering.

Use:

```bash
python3 scripts/build_figure_intent.py --source-file paper.tex --request "生成投稿方法图" -o figure_intent.yaml
```

Read:

- [references/figure-intent-schema.md](references/figure-intent-schema.md)

### 4. Compile For The Chosen Backend

If backend is `banana`, compile a tightly-scoped image prompt:

```bash
python3 scripts/compile_banana_prompt.py figure_intent.yaml -o figure.prompt.txt
```

If backend is `drawio`, delegate to `drawio-architecture-diagram`.

If backend is `plot`, compile a plot spec and render both an SVG chart and a polished PNG preview:

```bash
python3 scripts/compile_plot_package.py figure_intent.yaml -o figure.plot_spec.yaml
python3 scripts/render_plot_svg.py figure.plot_spec.yaml -o figure.svg
python3 scripts/render_plot_png.py figure.plot_spec.yaml -o figure.png
```

The plot backend is intended for:

- Markdown tables
- CSV tables
- common LaTeX `tabular` tables
- line, grouped-bar, stacked-bar, and scatter plots
- time-series charts with dense-label reduction and preview-ready layout
- error bars, dual-axis plots, and request-driven log scales

If backend is `hybrid`, generate both the editable structure and the quantitative panel:

```bash
python3 scripts/run_figure_pipeline.py \
  --source-file examples/hybrid/corridor_results_hybrid.md \
  --request "generate a hybrid figure with structure and result chart" \
  --output-dir out/hybrid_demo
```

The hybrid backend currently outputs:

- a `.drawio` architecture file
- plot `SVG + PNG` artifacts
- a composed preview PNG for GitHub, papers, or demos

Read:

- [references/scientific-figure-prompt-patterns.md](references/scientific-figure-prompt-patterns.md)
- [references/caption-guidelines.md](references/caption-guidelines.md)

### 5. Verify Before Finalizing

Verify:

- required stages are present
- the backend matches the figure need
- labels are not overloaded
- the result did not drift away from the scientific story

Use:

```bash
python3 scripts/verify_figure_result.py --intent figure_intent.yaml --artifact output.png --backend banana
```

Read:

- [references/verification-rules.md](references/verification-rules.md)
- [references/failure-cookbook.md](references/failure-cookbook.md)

### 6. Iterate Or Switch Backend

If verification fails:

- reduce text
- reduce modules
- tighten composition
- strengthen forbidden details

If the image backend still drifts on a structure-heavy figure:

- stop retrying image generation
- switch to `drawio`

## Practical Rules

- Prefer one clear scientific story per figure.
- Keep visible labels short.
- Treat `figure_intent.yaml` as the source of truth.
- Use `drawio` when exact module placement matters.
- Use `banana` when communication value matters more than exact topology.
- Use `plot` for metrics, charts, and ablations.
- Use `hybrid` when the source includes both stages and quantitative evidence.

## Bundled Scripts

- [scripts/route_figure_backend.py](scripts/route_figure_backend.py)
- [scripts/extract_scientific_figure_content.py](scripts/extract_scientific_figure_content.py)
- [scripts/build_figure_intent.py](scripts/build_figure_intent.py)
- [scripts/compile_figure_caption.py](scripts/compile_figure_caption.py)
- [scripts/compile_banana_prompt.py](scripts/compile_banana_prompt.py)
- [scripts/compile_drawio_package.py](scripts/compile_drawio_package.py)
- [scripts/compile_plot_package.py](scripts/compile_plot_package.py)
- [scripts/plot_render_utils.py](scripts/plot_render_utils.py)
- [scripts/render_plot_png.py](scripts/render_plot_png.py)
- [scripts/render_plot_svg.py](scripts/render_plot_svg.py)
- [scripts/render_hybrid_preview.py](scripts/render_hybrid_preview.py)
- [scripts/verify_figure_result.py](scripts/verify_figure_result.py)
- [scripts/run_figure_pipeline.py](scripts/run_figure_pipeline.py)

## Output Contract

Return:

1. chosen figure class
2. chosen backend and reason
3. `figure_intent.yaml`
4. backend-ready artifact such as a prompt or diagram package
5. generated caption file
6. verification summary
7. fallback recommendation when needed

## Failure Handling

If the figure type is unclear:

- emit the top two candidate figure classes
- explain the tradeoff
- default to the more controllable backend

If the extracted structure is too weak:

- produce a best-effort `figure_intent.yaml`
- mark assumptions explicitly

If the user asks for a chart but provides no data:

- stop and state the missing quantitative inputs
