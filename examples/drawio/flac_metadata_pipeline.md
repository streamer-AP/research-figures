# FLAC Metadata Parsing Pipeline

Please generate an editable architecture diagram.

Inputs:

- FLAC file

Main stages:

- header parser
- metadata block scanner
- block classifier
- field extractor
- metadata normalizer

Outputs:

- JSON metadata
- artwork reference

Notes:

- keep the layout left to right
- emphasize metadata flow rather than audio playback
