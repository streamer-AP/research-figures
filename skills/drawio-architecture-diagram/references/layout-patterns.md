# Layout Patterns

Choose the simplest layout that matches the structure.

Retrieve by structural family first, then by topic.

## left-to-right

Use for:

- classic processing pipelines
- stepwise methods
- patent technical flows

## top-to-bottom

Use for:

- hierarchical stages
- layered training/inference workflows

## dual-branch

Use for:

- paired inputs
- before/after processing
- Siamese or two-stream models

Rules:

- keep the two branches visually symmetric
- place fusion or comparison modules in the center or downstream

## encoder-decoder

Use for:

- hourglass networks
- compression-reconstruction structures

Rules:

- align encoder and decoder stages
- place skip links clearly if needed

## hub-and-spoke

Use for:

- controller-centered systems
- UAV/command-center style architectures

Rules:

- place the controller or command node in the middle
- keep peripheral subsystems evenly distributed
