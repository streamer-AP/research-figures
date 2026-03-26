# draw.io Integration

Use draw.io as an editable target, not as a place to paste static rendered images.

## Recommended flow

1. Generate the planning summary and `Diagram Spec` YAML block.
2. Verify the spec with `scripts/verify_diagram_spec.py`.
3. Convert it into `.drawio` XML with `scripts/spec_to_drawio.py`.
4. Or use `scripts/verify_and_convert.py` for the strict path.
5. Open the generated `.drawio` file in draw.io or diagrams.net for manual refinement.

## Examples

Convert the first fenced YAML block from Markdown:

```bash
python3 scripts/spec_to_drawio.py result.md --from-markdown -o diagram.drawio
```

Convert a raw YAML spec:

```bash
python3 scripts/spec_to_drawio.py spec.yaml -o diagram.drawio
```

Verify and convert in one step:

```bash
python3 scripts/verify_and_convert.py spec.yaml -o diagram.drawio
```

## Notes

- This path keeps the output editable inside draw.io.
- Prefer this over importing a static SVG when the user wants to refine boxes, arrows, labels, or grouping.
- The generated layout is intentionally simple and scriptable; use draw.io for final visual polish.
- If the verifier reports `needs-fix`, correct the structure before polishing the layout.
