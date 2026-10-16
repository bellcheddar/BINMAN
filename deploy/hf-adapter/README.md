---
base_model: Qwen/Qwen2.5-3B-Instruct
library_name: peft
license: other
license_name: qwen-research
license_link: https://huggingface.co/Qwen/Qwen2.5-3B-Instruct/blob/main/LICENSE
pipeline_tag: text-generation
tags:
  - lora
  - peft
  - structural-biology
  - molecular-glue
  - targeted-protein-degradation
language:
  - en
---

# BINMAN-LM adapter

A LoRA adapter for `Qwen/Qwen2.5-3B-Instruct`, trained for
[**BINMAN**](https://github.com/bellcheddar/BINMAN): an atlas of bridging
ligands (molecular glues), structural degrons, E3 ligase triage and
degradability built from the PDB.

Try it: [**Dellboy/binman-lm**](https://huggingface.co/spaces/Dellboy/binman-lm)

> **Current weights: training round 15** — 32 LoRA layers at rank 8, 15,806
> iterations, round 07's recipe on a corpus whose abstain task carries both
> classes. Perfect Task A set equality (1.000) and, for the first time, an
> abstain head that lets answerable questions through: specificity **1.000**
> against round 07's 0.000. This repository is updated when a round measures
> better, and the comparison is re-run on the current corpus each time rather
> than quoted from the previous round's table.

## What it does, and what it must never do

Three text jobs:

1. **Query translation** — a question about the atlas into a query object.
2. **Evidence triage** — a bridging ligand into one of four evidence classes:
   `crystallisation_artefact`, `molecular_glue`, `native_cofactor`, `protac`.
3. **Abstention** — refusing, in structured form, when the atlas schema cannot
   answer the question.

**It never computes, estimates or reports a number.** Every figure in BINMAN
(ΔSASA, Cβ–Cβ distances, pocket scores, pLDDT) is computed deterministically in
Python over the atlas and passed to the interface. A number in this model's
output that was not copied verbatim from a retrieved record is a defect, not a
feature. That is why abstention is a measured task rather than a disclaimer.

## Training

| | |
|---|---|
| Base | `Qwen/Qwen2.5-3B-Instruct` |
| Trained against | `mlx-community/Qwen2.5-3B-Instruct-4bit` (4-bit) |
| Method | LoRA, rank 8, scale 20 (PEFT `lora_alpha` 160), **32 layers** (4-35) |
| Iterations | 14,152 at batch 4, two epochs over 28,304 examples |
| Targets | `q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj`, `down_proj` |
| Framework | `mlx-lm` on Apple silicon, converted to PEFT |

Measured on a class-balanced 240-sample triage set (60 per class, fixed seed):

| Metric | Value |
|---|---|
| Task B macro-F1 | **0.9295** |
| `molecular_glue` F1 / recall | 0.949 / 0.933 |
| `protac` F1 | 0.967 |
| Task A set equality | **1.000** |
| Task A parse rate | **1.000** |
| Task C abstention recall / fabrication | 1.00 / **0.00** |
| Task C abstention **specificity** | **1.000** |

Abstention specificity is the rate at which the head correctly declines to
abstain on questions the atlas demonstrably answers. Measured on BINMAN's own
twelve shipped presets, each verified end to end against the database. Round 07
scored 0.000 on it: trained on refusals alone, it had learned that the answer is
always no. Recall and fabrication are measured on unanswerable questions only
and cannot detect that, which is why specificity is reported beside them.

Metrics are published in
[`FINDINGS.md`](https://github.com/bellcheddar/BINMAN/blob/main/FINDINGS.md)
with their n and their method, including the full Task B confusion matrix
rather than the macro-F1 alone: the model's errors concentrate in the
glue-against-PROTAC cell, which is the pair worth knowing about.

## Known limitation: quantisation transfer

The adapter was trained to correct a **4-bit quantised** base and is served
against a **16-bit** one. Nothing guarantees the correction transfers
unchanged. `lm/export_hf.py --verify` in the repository runs the real held-out
test questions through the converted adapter and prints the same metrics the
MLX evaluation reports, so the two can be compared rather than assumed equal.
Read the published numbers as measured under MLX unless stated otherwise.

## Intended use and scope

Research and evaluation on the BINMAN atlas schema. It is a 3B model fine-tuned
on one project's query language: it is not a general chemistry assistant, it
has no knowledge of binding affinities, assay results or clinical status, and
it should abstain when asked for them. Treat any confident-sounding chemistry
claim outside the three tasks above as unverified.

## Licence

The base model is `Qwen/Qwen2.5-3B-Instruct` under the **Qwen Research License
Agreement**, which permits use, modification and redistribution for
**non-commercial purposes only**. This adapter is a modification within the
meaning of section 3 of that Agreement and is redistributed under the same
terms. `LICENSE` and `NOTICE` in this repository carry the Agreement and the
required attribution.

Training data derives from BioLiP2, MGDB, MolGlueDB, MGTbind and PROTAC-DB, all
cited with DOIs in the
[repository README](https://github.com/bellcheddar/BINMAN#-source-data) and in
`data/validation/MANIFEST.md`. **No source dataset is redistributed here.**
PROTAC-DB's own terms permit internal use including derivatives and prohibit
redistribution; publishing these weights was a decision the author made
explicitly, recorded with its reasoning as `DECISIONS.md` D-030. Anyone reusing
this adapter should read that entry and form their own view.

## Citation

```bibtex
@software{deller_binman,
  author = {Deller, Marc C.},
  title  = {BINMAN: Blind-spot INventory of Molecular Adhesives and Neosubstrates},
  url    = {https://github.com/bellcheddar/BINMAN}
}
```
