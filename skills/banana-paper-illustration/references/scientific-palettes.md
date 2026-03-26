# Scientific Palette Notes

This skill now treats color direction as part of figure intent, not just a vague styling afterthought.

The presets below are grounded in widely used scientific-visualization references:

- `Paul Tol`: color-blind-safe qualitative schemes with strong defaults for bright, vibrant, and muted categorical figures.
- `Okabe-Ito`: a compact color-blind-friendly palette often cited for scientific graphics.
- `ColorBrewer`: guidance for choosing qualitative, sequential, and diverging color families based on data semantics.
- `Nature Methods` Points of View columns by Bang Wong and collaborators: practical advice on color coding, color blindness, and mapping quantitative data to color.

## Skill Presets

### `vivid-academic`

Default for Banana rendering.

- Goal: more lively paper figures without sliding into neon poster aesthetics.
- Accent family: `#4477AA`, `#66CCEE`, `#228833`, `#CCBB44`, `#EE6677`, `#AA3377`
- Best for: method overviews, visual abstracts, research covers with structured scientific content.

### `clean-academic`

- Goal: restrained publication palette with calm contrast.
- Accent family: `#4477AA`, `#66CCEE`, `#228833`, `#CCBB44`, `#AA3377`
- Best for: conservative journals, more diagram-like figures.

### `okabe-ito`

- Goal: strong color-blind-friendly category separation.
- Accent family: `#E69F00`, `#56B4E9`, `#009E73`, `#F0E442`, `#0072B2`, `#D55E00`, `#CC79A7`
- Best for: categorical scientific scenes where accessibility matters.

### `tol-bright`

- Goal: balanced categorical colors derived from Paul Tol's bright scheme.
- Accent family: `#4477AA`, `#EE6677`, `#228833`, `#CCBB44`, `#66CCEE`, `#AA3377`
- Best for: modular pipelines and stage-separated figures.

### `tol-vibrant`

- Goal: slightly more energetic module separation derived from Paul Tol's vibrant scheme.
- Accent family: `#EE7733`, `#0077BB`, `#33BBEE`, `#EE3377`, `#CC3311`, `#009988`
- Best for: teaser figures, stronger concept illustrations.

### `brewer-accent`

- Goal: ColorBrewer-style qualitative grouping with accent emphasis.
- Accent family: `#66C2A5`, `#FC8D62`, `#8DA0CB`, `#E78AC3`, `#A6D854`, `#FFD92F`
- Best for: families of related modules with one or two emphasized outcomes.

## Auto Routing

When the user does not specify a palette, the skill now picks one by domain:

| Domain cue | Default palette |
| --- | --- |
| CV, 3D perception, segmentation, LiDAR, point cloud | `tol-vibrant` |
| NLP, document understanding, IE, text pipelines | `tol-bright` |
| LLM, agent, tool use, memory, RAG | `okabe-ito` |
| Systems, robotics, drone, audio, wireless, hardware | `vivid-academic` |
| Theory, scaling law, mathematically restrained figures | `clean-academic` |
| Fallback | `vivid-academic` |

## Practical Prompt Rules

- Keep the background white or very light neutral unless the user explicitly wants a dark poster style.
- Use 4 to 6 accents max in most figures.
- Reserve the warmest or highest-saturation accent for the scientific novelty, result, or feedback loop.
- Avoid muddy blue-gray monotony unless the subject is intentionally subdued.
- Avoid rainbow ordering for ordered quantities unless the user explicitly wants a false-color look.

## References

- Paul Tol, “Introduction to colour schemes”: https://sronpersonalpages.nl/~pault/
- Okabe and Ito, “Color Universal Design (CUD)”: https://jfly.uni-koeln.de/color/
- ColorBrewer 2.0: https://colorbrewer2.org/
- Bang Wong, “Color coding,” Nature Methods (2010): https://doi.org/10.1038/nmeth0810-573
- Bang Wong, “Points of view: Color blindness,” Nature Methods (2011): https://doi.org/10.1038/nmeth.1618
- Gehlenborg and Wong, “Mapping quantitative data to color,” Nature Methods (2012): https://doi.org/10.1038/nmeth.2134
