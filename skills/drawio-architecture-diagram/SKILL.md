---
name: drawio-architecture-diagram
description: Generate editable draw.io architecture diagrams from paper text, patent drafts, technical notes, or method descriptions. Use when the user wants a scientific or technical architecture figure as a real .drawio file for diagrams.net/draw.io, especially for papers, patents, proposals, system block diagrams, or model framework figures.
---

# draw.io Architecture Diagram

Create editable `.drawio` architecture diagrams from technical text.

This skill is intentionally narrow. Use it for architecture figures only. Do not use it for charts, plots, timelines, result figures, or artistic illustrations.

## What Changed

This skill now follows a PaperBanana-inspired workflow:

1. `Retriever`: retrieve the right diagram family and layout pattern, not just the topic.
2. `Planner`: turn source text into a compact structural plan before writing the final spec.
3. `Stylist`: enforce academic or patent figure conventions.
4. `Verifier`: check the spec for structural mistakes before rendering.
5. `Renderer`: convert the verified spec into `.drawio`.

The goal is not a flashy prompt. The goal is a controllable diagram pipeline.

## Supported Diagram Types

- `architecture`: overall research or system architecture
- `pipeline`: processing or method flow
- `model-structure`: modular model framework
- `patent-architecture`: patent or technical disclosure system figure

If the request is not really an architecture figure, say so and do not force it into draw.io output.

## Workflow

Follow this workflow:

### 1. Retriever

Retrieve the closest figure family from the layout references:

- pipeline
- controller-centered architecture
- dual-branch architecture
- encoder-decoder structure
- patent system figure

Important:

- prioritize visual structure over research topic
- retrieve by control flow, grouping, and feedback-loop shape
- say which layout family you selected and why

### 2. Planner

Before writing the final spec, extract:

- inputs
- outputs
- modules
- branches
- feedback loops
- subsystem groups
- confirmed facts
- assumptions
- missing structural facts

Use short labels. Compress long prose into 1-4 visible words where possible.

If helpful, generate a planning draft with:

```bash
python3 scripts/plan_from_source.py source.md -o planning_bundle.md
```

The planner is heuristic, so treat it as a draft generator, not as ground truth.

### 3. Stylist

Apply academic or patent figure style rules:

- keep labels short
- preserve terminology consistency
- prefer orthogonal flow
- use subsystem grouping only when it adds meaning
- keep the layout symmetric when the structure is paired or dual-stream

### 4. Diagram Spec

Build a `diagram spec` in YAML using the standard schema.

### 5. Verifier

Run a structural check before conversion:

```bash
python3 scripts/verify_diagram_spec.py spec.yaml
```

The verifier checks:

- missing node references
- duplicate ids
- duplicate visible labels
- isolated nodes
- suspiciously long labels
- group membership issues
- layout mismatches
- graph cycles or feedback paths

If the verifier reports hard errors, fix the spec before conversion.

### 6. Renderer

Convert the verified spec into an editable `.drawio` file:

```bash
python3 scripts/spec_to_drawio.py spec.yaml -o diagram.drawio
```

Or use the helper wrapper:

```bash
python3 scripts/verify_and_convert.py spec.yaml -o diagram.drawio
```

## Output Contract

By default, produce these seven items:

### 1. Diagram Type

State the chosen type and why it fits.

### 2. Planning Summary

Return a short planning block covering:

- confirmed structure
- assumptions
- missing facts
- chosen layout family

### 3. Diagram Spec

Return a YAML spec using this shape:

```yaml
title: ...
diagram_type: architecture
layout: left-to-right
audience: paper|patent|report
style: academic-minimal
nodes:
  - id: ...
    label: ...
    type: input|module|output|storage|decision|group-anchor
edges:
  - from: ...
    to: ...
    label: ...
groups:
  - label: ...
    members: [...]
notes:
  - ...
```

### 4. Verification Notes

Return a short verification summary:

- `pass` or `needs-fix`
- the top structural risks
- any assumption that affects correctness

### 5. draw.io File

Create a `.drawio` file with `scripts/spec_to_drawio.py` unless the user explicitly asks for analysis only.

Return:

- output file path
- a short note on whether the file was actually generated or only specified

Only return raw draw.io XML inline when the user explicitly asks for it.

### 6. Figure Title And Caption

Return:

- one Chinese title when the source is Chinese
- one English title when the source is English or paper-oriented
- one caption paragraph

### 7. Layout Notes

Return 4-8 flat bullets covering:

- layout direction
- grouping
- important alignments
- feedback-loop placement
- highlight emphasis if any

## File Creation Rules

- Prefer a file name derived from the figure title, using lowercase English words or safe ASCII where possible.
- If the task already has a project folder, save the `.drawio` file in the current working directory unless the user specifies another location.
- If a YAML spec file is created as an intermediate artifact, keep it next to the `.drawio` file.
- If a planning bundle is created, keep it next to the spec.

## Label Rules

- Prefer 1-4 words per visible label.
- Keep terminology consistent with the source.
- Put nuance in `notes` or the caption, not inside the boxes.
- When the source is Chinese and the user does not request English, keep Chinese labels.

## Style Rules

- Keep the diagram academic and minimal.
- Do not overuse color.
- Keep the layout clean and aligned.
- Prefer simple orthogonal flow for patent and system diagrams.
- Prefer symmetric branches when the source is dual-stream or paired-input.
- For patent figures, prioritize structural correctness over visual decoration.

For schema, layout, workflow, and draw.io notes, read:

- [references/spec-schema.md](references/spec-schema.md)
- [references/layout-patterns.md](references/layout-patterns.md)
- [references/drawio.md](references/drawio.md)
- [references/paperbanana-inspired-workflow.md](references/paperbanana-inspired-workflow.md)

## Tooling

Use:

- [scripts/plan_from_source.py](scripts/plan_from_source.py)
- [scripts/verify_diagram_spec.py](scripts/verify_diagram_spec.py)
- [scripts/verify_and_convert.py](scripts/verify_and_convert.py)
- [scripts/spec_to_drawio.py](scripts/spec_to_drawio.py)

The converter accepts:

- raw YAML spec files
- Markdown files containing a fenced `yaml` block

Examples:

```bash
python3 scripts/plan_from_source.py source.md -o planning_bundle.md
python3 scripts/verify_diagram_spec.py spec.yaml
python3 scripts/verify_and_convert.py spec.yaml -o diagram.drawio
```

## Quality Bar

Before finalizing, verify:

- all important modules exist in the spec
- no edge references a missing node
- labels are shorter than the source prose
- the chosen layout matches the actual structure
- feedback loops are deliberate and clearly placed
- the `.drawio` output is editable

## Failure Handling

If the source text is vague:

1. list the missing structural facts
2. provide a best-effort draft
3. separate assumptions from confirmed structure
4. mark the verification result as `needs-fix` when assumptions materially affect the diagram

If the environment is read-only or file creation is not possible:

- still return the planning summary and YAML spec
- tell the user which `.drawio` file should be generated
- do not pretend the file was created
