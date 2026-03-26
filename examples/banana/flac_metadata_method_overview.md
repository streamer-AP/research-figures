# FLAC Audio Metadata Extraction Architecture

Generate a paper-style method overview illustration for extracting metadata from FLAC audio files.

Core story:

- read a FLAC file container
- parse the FLAC header and metadata block chain
- identify STREAMINFO, VORBIS_COMMENT, PICTURE, CUESHEET, and SEEKTABLE
- extract title, artist, album, duration, sample rate, channels, bit depth, and cover art
- normalize the results into structured JSON output

Composition:

- FLAC file input on the left
- metadata parser in the center
- metadata block branches around the parser
- normalized structured output on the right
- white or very light background
- only a few readable labels
