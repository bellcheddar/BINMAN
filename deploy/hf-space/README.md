---
title: BINMAN-LM
emoji: 🗑️
colorFrom: gray
colorTo: orange
sdk: gradio
sdk_version: 4.44.0
app_file: app.py
pinned: false
license: apache-2.0
short_description: Query translation, evidence triage and abstention for the BINMAN atlas
---

# BINMAN-LM

The small language model behind [BINMAN](https://github.com/bellcheddar/BINMAN),
an atlas of bridging ligands (molecular glues), structural degrons, E3 ligase
triage and degradability built from the PDB.

Qwen2.5-3B-Instruct with a LoRA adapter, trained on Apple silicon with `mlx-lm`
and converted to PEFT to run on ZeroGPU.

**The model does three text jobs and no arithmetic.** Every number in BINMAN is
computed deterministically in Python over the atlas and passed to the
interface. A figure in the model's output that was not copied verbatim from a
retrieved record is a defect, not a feature. The abstention tab is as much the
demonstration as the query tab.

The atlas itself is not served here: it is 142 MB, and several of the datasets
behind it carry licences that do not permit redistribution.

## Configuration

| Secret or variable | Purpose |
|---|---|
| `HF_TOKEN` (secret) | read access to the private adapter repository |
| `BINMAN_ADAPTER_REPO` (variable) | defaults to `Dellboy/binman-lm-adapter` |

The adapter repository is **private**. The adapter is a derivative of training
data whose licence permits internal use but not redistribution, so the weights
are not published. See `DECISIONS.md` D-021 and D-029 in the repository.

## Reported performance

Measured on held-out test questions and recorded in the repository's
`FINDINGS.md`, with the full confusion matrix rather than headline numbers
alone. The numbers published there are measured under MLX on Apple silicon;
the conversion to PEFT is verified against the same held-out questions by
`lm/export_hf.py --verify`, because an adapter trained to correct a 4-bit base
is not guaranteed to transfer unchanged to a 16-bit one.
