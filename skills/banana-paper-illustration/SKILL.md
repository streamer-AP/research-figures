---
name: banana-paper-illustration
description: Generate paper-style illustrations with the Banana/Jiekou text-to-image API when the user wants a visual abstract, teaser figure, concept illustration, method overview art, or publication-style research image from a paper abstract, method description, caption, or technical note. Use this skill for image-first scientific figures, not for precise charts, tables, or editable box-arrow diagrams.
---

# Banana Paper Illustration

Generate publication-style research illustrations with the Banana text-to-image API.

Use this skill when the user wants:

- a paper teaser image
- a visual abstract
- a polished concept illustration for a method or system
- a paper figure that should look more visual than a draw.io block diagram

Do not use this skill when the user needs:

- exact plots or charts
- precise tables
- patent black-and-white line drawings
- editable architecture diagrams with strict node/edge control

For editable structure-first diagrams, prefer `drawio-architecture-diagram`.

## Workflow

### 1. Decide Whether Image Generation Is Appropriate

Use this skill only if the target figure is image-first.

Good fits:

- visual summaries
- conceptual figures
- research covers
- system atmosphere figures
- hybrid method overview illustrations with limited labels

Bad fits:

- algorithm flowcharts with exact topology
- benchmark plots
- diagrams requiring deterministic box placement

### 2. Build The Figure Intent

Extract from the user's source:

- the paper or method title
- the central scientific story
- 3-6 visual elements
- what must be foreground vs background
- whether arrows, stages, agents, or feedback loops should appear
- what style is expected

If the source is long, compress it before prompting. Do not dump raw sections into the API.

### 3. Choose A Figure Mode

Use one of these modes:

- `teaser`: visually strong paper opener with one dominant composition
- `method-overview`: a semi-structured method illustration with a few modules or arrows
- `visual-abstract`: balanced high-level summary for the whole paper
- `system-concept`: system or architecture concept art with technical atmosphere

### 4. Generate A Prompt

Use the bundled prompt logic in:

- [scripts/generate_banana_illustration.py](scripts/generate_banana_illustration.py)

Read these references as needed:

- [references/api.md](references/api.md)
- [references/prompt-patterns.md](references/prompt-patterns.md)
- [references/scientific-palettes.md](references/scientific-palettes.md)

The script can:

- accept a direct prompt
- derive a prompt from a source file
- auto-select a palette by domain when `--palette` is not specified
- apply a scientific palette preset such as `vivid-academic` or `okabe-ito`
- save the final resolved prompt to a sibling `.prompt.txt` file
- call the API and write the returned image to disk

### 5. Call The API

Use the script instead of hand-writing the request each time:

```bash
python3 scripts/generate_banana_illustration.py \
  --source-file paper_method.md \
  --mode method-overview \
  --palette vivid-academic \
  --output paper_figure.png
```

The script reads the API key from:

1. `BANANA_API_KEY`
2. `API_KEY`

Do not hard-code secrets into the skill or output files.

### 6. Review And Iterate

After generation, review:

- whether the scientific story is clear
- whether the composition matches the intended figure type
- whether the image uses too much unreadable micro-text
- whether key modules or agents are visually distinct
- whether the output looks like a paper figure instead of generic concept art

If the result is too loose:

- simplify the figure story
- reduce the number of modules
- add stronger composition instructions
- switch to `drawio-architecture-diagram` if exact structure matters more than visual richness

## Output Contract

By default, produce:

### 1. Figure Intent

State:

- chosen figure mode
- why image generation fits better than draw.io for this request

### 2. Prompt Summary

Return:

- a short summary of the final prompt direction
- the main scientific elements being visualized
- the key style constraints

### 3. Generated Files

Return:

- image path
- prompt file path
- source file path if one was created

### 4. Risks

Call out the main failure risks, such as:

- unreadable text inside the image
- structure drift
- too much artistic freedom
- weak faithfulness to the paper

## Practical Rules

- Prefer light or white backgrounds unless the user explicitly wants a dark poster style.
- Prefer sparse labels; text rendering inside images is fragile.
- Keep the scientific story narrow. One figure should express one main idea.
- For method illustrations, ask for a structured composition but do not expect pixel-perfect topology.
- If the user needs strict module placement, switch to draw.io instead of fighting the image model.

## Validation

Before finalizing, verify:

- the prompt is specific enough to encode the main scientific story
- the requested mode matches the actual figure need
- the output path is explicit
- the API key is read from environment variables only

## Failure Handling

If the API key is missing:

- stop with a clear error naming the supported environment variables

If the API returns non-image content:

- save or print the diagnostic response
- do not pretend the image succeeded

If the result is too diagram-like but still inaccurate:

- recommend switching to `drawio-architecture-diagram`
