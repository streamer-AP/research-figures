# Quickstart

This page is optimized for first-run success on a fresh clone.

## Install

```bash
python3 -m pip install -r requirements.txt
```

Current Python dependencies are intentionally small:

- `PyYAML`
- `Pillow`

## Fastest Offline Demo

```bash
./research-figures demo --offline
```

This generates:

- a plot demo
- an editable draw.io demo
- a hybrid structure-plus-results demo
- a Banana dry-run prompt bundle and caption bundle

All output goes to `out/showcase_demo/` by default.

## Generate One Figure

```bash
./research-figures \
  --source-file examples/showcase/ml_theory_scaling_law.md \
  --request "generate a scaling law line plot" \
  --output-dir out/demo_plot
```

Expected output files include:

- `figure.png` or `figure.drawio`
- `figure.caption.md`
- `figure_intent.yaml`
- `verification.yaml`
- `bundle.yaml`

## Generate A Real Banana Figure

If you have a valid Banana / Jiekou API key:

```bash
export BANANA_API_KEY=your_key_here
./research-figures \
  --source-file examples/showcase/cv_multiscale_segmentation_visual.md \
  --request "generate a visual abstract" \
  --backend banana \
  --figure-class visual-abstract \
  --output-dir out/demo_banana
```

If no key is configured, use the same command with `--dry-run` to generate the prompt, caption, and bundle without a live render.

## Under The Hood

`./research-figures` is a thin wrapper over:

```bash
python3 skills/research-figure-studio/scripts/run_figure_pipeline.py
```

Use the lower-level script directly if you want to integrate the pipeline into another tool.

---

## 中文快速开始

这个页面只关注第一次跑通。

### 安装

```bash
python3 -m pip install -r requirements.txt
```

### 最快试跑

```bash
./research-figures demo --offline
```

默认会在 `out/showcase_demo/` 下生成：

- plot 示例
- draw.io 结构图示例
- hybrid 组合图示例
- Banana 的 dry-run 结果、prompt 和 caption

### 生成单张图

```bash
./research-figures \
  --source-file examples/showcase/ml_theory_scaling_law.md \
  --request "generate a scaling law line plot" \
  --output-dir out/demo_plot
```

### 生成真实 Banana 图片

配置好 `BANANA_API_KEY` 或 `API_KEY` 后：

```bash
./research-figures \
  --source-file examples/showcase/cv_multiscale_segmentation_visual.md \
  --request "generate a visual abstract" \
  --backend banana \
  --figure-class visual-abstract \
  --output-dir out/demo_banana
```
