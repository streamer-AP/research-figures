# Corridor Segmentation Pipeline With Results

Generate a hybrid figure that combines an editable architecture diagram with a quantitative results panel.

Main stages:

- whole-scene downsampling
- coarse segmentation backbone
- rare-class enhancement
- sparse refinement branch
- confidence-gated fusion

Outputs:

- dense semantic map
- refined rare-object predictions

| Variant | mIoU | Jumper IoU |
| --- | ---: | ---: |
| Baseline | 0.684 | 0.291 |
| Whole-scene | 0.711 | 0.356 |
| Full Method | 0.751 | 0.495 |
