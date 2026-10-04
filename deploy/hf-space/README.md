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
| `BINMAN_ADAPTER_REPO` (variable) | defaults to `Dellboy/binman-lm-adapter` |
| `HF_TOKEN` (secret) | not needed for a public adapter; read if present |

## Training data and licences

The adapter is trained on data derived from BioLiP2, MGDB, MolGlueDB, MGTbind
and PROTAC-DB, all cited with DOIs in the
[repository README](https://github.com/bellcheddar/BINMAN#-source-data) and in
`data/validation/MANIFEST.md`. **No source dataset is redistributed here**: the
Space serves inference only.

PROTAC-DB's terms permit internal use including derivatives and prohibit
redistribution. Publishing these weights is a decision the author made
explicitly, recorded as `DECISIONS.md` D-030, on the basis that the work is
non-commercial and the source is credited. Anyone reusing the adapter should
read that entry and form their own view.

## Reported performance

Measured on held-out test questions and recorded in the repository's
`FINDINGS.md`, with the full confusion matrix rather than headline numbers
alone. The numbers published there are measured under MLX on Apple silicon;
the conversion to PEFT is verified against the same held-out questions by
`lm/export_hf.py --verify`, because an adapter trained to correct a 4-bit base
is not guaranteed to transfer unchanged to a 16-bit one.
