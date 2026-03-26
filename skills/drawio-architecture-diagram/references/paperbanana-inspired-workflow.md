# PaperBanana-Inspired Workflow

This skill borrows the most practical ideas from PaperBanana, but adapts them to an editable draw.io pipeline instead of direct image generation.

## Core Principle

Do not jump directly from long source text to a rendered diagram.

Use a staged pipeline:

1. retrieve the right figure family
2. plan the structure
3. apply style rules
4. verify the graph
5. render to an editable target

## Retriever

Retrieve by visual structure, not just by topic.

Examples:

- a method with ordered stages should retrieve a pipeline pattern
- a controller with multiple peripherals should retrieve a hub-and-spoke pattern
- two input streams should retrieve a dual-branch pattern
- a patent system with modules and feedback should retrieve a patent architecture pattern

## Planner

The planner should separate:

- confirmed structure
- likely structure
- missing structure

The planner should prefer:

- short labels
- stable ids
- explicit edges
- compact notes for nuance

## Stylist

The stylist should not invent new structure.

The stylist should only improve:

- label brevity
- layout family
- grouping
- symmetry
- caption tone

## Verifier

The verifier should catch:

- node id mismatches
- dangling edges
- isolated nodes
- duplicate labels
- unintended cycles
- layout choices that do not match the graph

## Renderer

The renderer should output an editable file.

For this skill, the renderer target is `.drawio`, not a static raster image.

## Why This Matters

For scientific and patent diagrams, the hard problem is not only visual polish. The hard problem is structural correctness.

That is why this skill treats diagram creation more like compiling a structured artifact than like prompting an image model.
