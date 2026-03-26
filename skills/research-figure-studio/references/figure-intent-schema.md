# Figure Intent Schema

Use `figure_intent.yaml` as the shared intermediate representation.

Suggested fields:

```yaml
title: ...
figure_class: method-overview
backend: drawio
audience: paper
story:
  one_liner: ...
  emphasis:
    - ...
source_artifacts:
  - path: paper.tex
    kind: latex
must_keep_terms:
  - ...
forbidden_details:
  - tiny paragraphs
inputs:
  - ...
outputs:
  - ...
stages:
  - id: stage_1
    label: ...
    purpose: ...
edges:
  - from: input
    to: stage_1
visual_objects:
  - ...
style_constraints:
  palette: clean-academic
  background: white
  label_density: low
verification_targets:
  - ...
assumptions:
  - ...
```

Rules:

- keep stage labels short
- keep nuance in `purpose`, not in visible labels
- record assumptions explicitly
