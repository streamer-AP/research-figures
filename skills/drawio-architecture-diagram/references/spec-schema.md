# Diagram Spec Schema

Use this schema when turning source text into an intermediate diagram representation.

```yaml
title: ...
diagram_type: architecture|pipeline|model-structure|patent-architecture
layout: left-to-right|top-to-bottom|dual-branch|encoder-decoder|hub-and-spoke
audience: paper|patent|report
style: academic-minimal
nodes:
  - id: unique_snake_case_id
    label: short visible text
    type: input|module|output|storage|decision|group-anchor
edges:
  - from: source_node_id
    to: target_node_id
    label: optional short edge text
groups:
  - label: optional subsystem name
    members: [node_id_1, node_id_2]
notes:
  - optional assumption or hidden relation
```

Guidelines:

- Keep node ids stable and machine-friendly.
- Keep visible labels short.
- Use groups only when they add real structural meaning.
- Put full nuance in `notes` or the caption, not inside labels.
