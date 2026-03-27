# Contributing

Thanks for helping improve `research-figures`.

## Good First Contributions

- add a new showcase example under `examples/`
- improve caption quality for a backend or figure class
- tighten verification rules for a common failure mode
- improve offline demos and reproducibility
- add docs for a strong real-world use case

## Local Setup

```bash
python3 -m pip install -r requirements.txt
./research-figures demo --offline
```

## Contribution Rules

- Keep the repo runnable from a fresh clone.
- Prefer examples that are easy to reproduce locally.
- Do not commit API keys, secrets, or generated private data.
- Keep README focused on user value, not internal process notes.
- When adding a new backend behavior, update both docs and at least one example.

## Where To Put Things

- `examples/`: source material users can inspect and rerun
- `docs/assets/`: checked-in showcase assets referenced by the README
- `skills/research-figure-studio/`: orchestration and shared pipeline logic
- `skills/drawio-architecture-diagram/`: editable diagram path
- `skills/banana-paper-illustration/`: image-first illustration path

## Before Opening A PR

- run `./research-figures demo --offline`
- verify the affected README or docs commands still work
- check that generated docs do not expose secrets
- include before/after screenshots when the change affects visible output
