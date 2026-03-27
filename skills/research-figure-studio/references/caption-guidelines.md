# Figure Caption Guidelines

Use caption generation to produce paper-ready supporting text from `figure_intent.yaml`.

## Goals

- generate a short caption for quick preview or README use
- generate a longer paper caption for manuscripts
- generate alt text for accessibility or web publishing

## Rules

- do not merely repeat every visible label in the figure
- explain the scientific story, not just the layout
- keep captions concise: usually 2 to 4 sentences
- mention the core flow from inputs to outputs when the figure is structural
- for hybrid figures, explicitly distinguish the left and right panels
- for plot figures, focus on what is being compared or summarized

## Backend-Specific Hints

### drawio / banana

- describe inputs, core stages, outputs, and the key innovation
- preserve the method name and important terms from `must_keep_terms`

### plot

- describe the metric trend or comparison target
- avoid inventing axis labels if the intent does not provide them

### hybrid

- mention that one panel shows structure and the other shows quantitative evidence

## Output Shape

Recommended sections:

- `Title`
- `Short Caption`
- `Paper Caption`
- `Alt Text`
