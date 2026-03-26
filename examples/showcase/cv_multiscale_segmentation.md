# Multi-Scale Corridor Point Cloud Segmentation

Generate an editable architecture diagram for a computer vision and 3D perception paper.

Inputs:

- corridor point cloud
- sparse labels

Main stages:

- whole-scene downsampling
- coarse segmentation backbone
- rare-class enhancement
- sparse refinement branch
- confidence-gated fusion

Outputs:

- dense semantic segmentation map
- refined rare-object predictions

Notes:

- emphasize a multi-stage CV pipeline
- keep the layout left to right
- show coarse-to-fine reasoning clearly
