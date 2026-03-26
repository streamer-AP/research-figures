# Maintainer Notes

This file keeps repository-maintenance notes out of the public-facing README.

## Public Release Checklist

- do not commit API keys or `.env` files
- keep secrets in environment variables only
- do not commit figures generated from private documents
- avoid machine-specific shell config or absolute local paths
- review `examples/` and `docs/assets/` before each public push
- verify Git history does not contain temporary secrets

## Recommended Positioning

- controllable scientific figure generation toolkit
- routing-first workflow instead of a single-renderer demo
- bridge between paper text, editable diagrams, plots, and image-first illustrations
