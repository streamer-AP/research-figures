# Research Figure Skills

[中文](#中文说明) | [English](#english)

![Hero banner](docs/assets/hero_banner.png)

## English

A routing-first toolkit for scientific figure generation.

License: [MIT](LICENSE)

A single entry point routes requests to the right backend:

- `drawio` for editable structure
- `banana` for image-first paper figures
- `plot` for polished charts from Markdown, CSV, and common LaTeX tables
- `hybrid` for editable structure plus a quantitative panel in one run

## Showcase

| Domain | Example | Backend | Preview |
| --- | --- | --- | --- |
| CV | Coarse-to-fine corridor segmentation | banana | ![CV showcase](docs/assets/showcase/cv_multiscale_segmentation.png) |
| NLP | Document-level information extraction | banana | ![NLP showcase](docs/assets/showcase/nlp_document_ie.png) |
| LLM | Tool-using agent pipeline | banana | ![LLM showcase](docs/assets/showcase/llm_agent_pipeline.png) |
| ML Theory | Scaling law comparison | plot | ![ML theory showcase](docs/assets/showcase/ml_theory_scaling_law.png) |
| Audio / Systems | FLAC metadata extraction overview, plus [editable `.drawio`](docs/assets/drawio_flac_pipeline.drawio) | banana + drawio | ![Audio showcase](docs/assets/banana_flac_metadata_overview.png) |

## More Examples

| Case | Source | Backend | Preview |
| --- | --- | --- | --- |
| Error-bar ablation chart | [ablation_with_error.md](examples/plot/ablation_with_error.md) | plot | ![Error bar showcase](docs/assets/showcase/plot_error_bars.png) |
| Dual-axis log-x tradeoff chart | [benchmark_dual_axis.md](examples/plot/benchmark_dual_axis.md) | plot | ![Dual axis showcase](docs/assets/showcase/plot_dual_axis_logx.png) |
| Structure + results composite figure | [corridor_results_hybrid.md](examples/hybrid/corridor_results_hybrid.md) | hybrid | ![Hybrid showcase](docs/assets/showcase/hybrid_corridor_results.png) |

## Capabilities

- `research-figure-studio`: route, build `figure_intent.yaml`, render, verify
- `drawio-architecture-diagram`: editable `.drawio` architecture and pipeline figures
- `banana-paper-illustration`: visual abstracts, concept figures, paper-style method art
- `plot`: Markdown / CSV / LaTeX tables to line, grouped-bar, stacked-bar, and scatter charts with `SVG + PNG`
- `plot`: error bars, dual-axis, log-scale, dense-tick reduction, and preview-ready chart cards
- `hybrid`: one-click `.drawio` + plot artifacts + a composed preview image

## Repository Layout

```text
research-figure-skills-github/
├── README.md
├── .gitignore
├── docs/
│   └── assets/
├── examples/
│   ├── banana/
│   ├── drawio/
│   ├── hybrid/
│   └── plot/
└── skills/
    ├── research-figure-studio/
    ├── drawio-architecture-diagram/
    └── banana-paper-illustration/
```

Important:

- keep the three skill folders as siblings under the same `skills/` directory
- `research-figure-studio` expects to find the backend skills next to it

## Quick Start

```bash
python3 skills/research-figure-studio/scripts/run_figure_pipeline.py \
  --source-file examples/showcase/ml_theory_scaling_law.md \
  --request "generate a scaling law line plot" \
  --output-dir out/demo
```

```bash
python3 skills/research-figure-studio/scripts/run_figure_pipeline.py \
  --source-file examples/hybrid/corridor_results_hybrid.md \
  --request "generate a hybrid figure with structure and result chart" \
  --output-dir out/hybrid_demo
```

## Current Limits

- LaTeX parsing is pragmatic and focuses on common `tabular` cases
- Banana is not suitable for exact topology control
- `hybrid` preview is a studio-rendered composite, not a direct draw.io export render

---

## 中文说明

这是一个“路由优先”的科研绘图工具箱。

统一入口会先判断该走哪类后端：

- `drawio` 负责可编辑结构图
- `banana` 负责论文风图像式配图
- `plot` 负责从 Markdown / CSV / 常见 LaTeX 表格生成成品图表
- `hybrid` 负责一次输出可编辑结构图和结果面板

## 展示效果

| 方向 | 示例 | 后端 | 展示 |
| --- | --- | --- | --- |
| CV | 粗到细走廊点云分割 | banana | ![CV 展示图](docs/assets/showcase/cv_multiscale_segmentation.png) |
| NLP | 文档级信息抽取 | banana | ![NLP 展示图](docs/assets/showcase/nlp_document_ie.png) |
| LLM | 工具调用智能体流程 | banana | ![LLM 展示图](docs/assets/showcase/llm_agent_pipeline.png) |
| ML 理论 | scaling law 对比图 | plot | ![ML 理论展示图](docs/assets/showcase/ml_theory_scaling_law.png) |
| 音频 / 系统 | FLAC 元信息提取，附 [可编辑 `.drawio`](docs/assets/drawio_flac_pipeline.drawio) | banana + drawio | ![Audio 展示图](docs/assets/banana_flac_metadata_overview.png) |

## 更多案例

| 案例 | 源文件 | 后端 | 展示 |
| --- | --- | --- | --- |
| 带误差棒的 ablation 图 | [ablation_with_error.md](examples/plot/ablation_with_error.md) | plot | ![误差棒案例](docs/assets/showcase/plot_error_bars.png) |
| 双轴对数横轴 tradeoff 图 | [benchmark_dual_axis.md](examples/plot/benchmark_dual_axis.md) | plot | ![双轴案例](docs/assets/showcase/plot_dual_axis_logx.png) |
| 结构图 + 结果图组合图 | [corridor_results_hybrid.md](examples/hybrid/corridor_results_hybrid.md) | hybrid | ![Hybrid 案例](docs/assets/showcase/hybrid_corridor_results.png) |

## 能力范围

- `research-figure-studio`：总控路由、意图生成、渲染与校验
- `drawio-architecture-diagram`：可编辑 `.drawio` 架构图与流程图
- `banana-paper-illustration`：论文风 visual abstract、概念图、方法图
- `plot`：支持从 Markdown / CSV / LaTeX 表格生成折线图、分组柱状图、堆叠柱状图、散点图，并输出 `SVG + PNG`
- `plot`：补充了 error bar、双轴、对数坐标、稠密横轴压缩和标题兜底
- `hybrid`：一键产出 `.drawio`、plot 图和组合预览图

## 仓库结构

```text
research-figure-skills-github/
├── README.md
├── .gitignore
├── docs/
│   └── assets/
├── examples/
│   ├── banana/
│   ├── drawio/
│   ├── hybrid/
│   └── plot/
└── skills/
    ├── research-figure-studio/
    ├── drawio-architecture-diagram/
    └── banana-paper-illustration/
```

注意：

- 三个 skill 必须作为同级目录保留在 `skills/` 下
- `research-figure-studio` 会查找旁边的两个后端 skill

## 快速开始

```bash
python3 skills/research-figure-studio/scripts/run_figure_pipeline.py \
  --source-file examples/showcase/ml_theory_scaling_law.md \
  --request "generate a scaling law line plot" \
  --output-dir out/demo
```

```bash
python3 skills/research-figure-studio/scripts/run_figure_pipeline.py \
  --source-file examples/hybrid/corridor_results_hybrid.md \
  --request "generate a hybrid figure with structure and result chart" \
  --output-dir out/hybrid_demo
```

## 当前限制

- LaTeX 解析是实用型实现，重点支持常见 `tabular`
- Banana 不适合追求像素级结构控制
- `hybrid` 预览图是 studio 内部合成结果，不是 draw.io 直接导出的位图
