# Backend Routing

## Choose `drawio` when

- structure is strict
- labels must be exact
- boxes and arrows must be editable
- the user will likely revise the figure manually

## Choose `banana` when

- the figure should look polished
- the output is image-first
- the figure is a teaser, visual abstract, or concept illustration

## Choose `plot` when

- numeric fidelity matters
- the figure includes axes, legends, and values

## Choose `hybrid` when

- both strict structure and strong visuals are required

## Default Rule

If uncertain, prefer the more controllable backend:

- `drawio` over `banana`
- `plot` over image generation for quantitative content
