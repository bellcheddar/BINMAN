# 🗑️ BINMAN

> **Molecular glues have been sitting in the PDB for thirty years, deposited without being labelled as such. This is the inventory.**

![python](https://img.shields.io/badge/python-3.11-3776AB?logo=python&logoColor=white) ![environment](https://img.shields.io/badge/environment-pixi%20%2B%20uv-1e73be) ![structures](https://img.shields.io/badge/structures-52821%20entries-2C6D60) ![validation](https://img.shields.io/badge/validation-published%20datasets%20only-D65B0A) ![licence](https://img.shields.io/badge/licence-code%20reusable-6A6F68) ![author](https://img.shields.io/badge/author-Marc%20C.%20Deller,%20D.Phil.-1C244B)

<table>
<tr>
<td>🌐 <b>Website</b></td><td><a href="https://marcdeller.com" target="_blank" rel="noopener noreferrer">marcdeller.com</a></td>
<td>✉️ <b>Contact</b></td><td><a href="mailto:marc@marcdeller.com">marc@marcdeller.com</a></td>
<td>🐙 <b>GitHub</b></td><td><a href="https://github.com/bellcheddar/binman" target="_blank" rel="noopener noreferrer">bellcheddar/binman</a></td>
</tr>
</table>

---

**Blind-spot INventory of Molecular Adhesives and Neosubstrates**

Why it matters: a molecular glue is just a small molecule that happens to bury surface against two protein chains at once, and the PDB is full of them sitting unlabelled next to the cryoprotectants. BINMAN mines them out by geometry rather than by annotation, classifies the crystallisation furniture instead of deleting it so the counts reconcile, and refuses to report a number it cannot derive from published data. It is useful for: finding chemotypes that already bridge two proteins, triaging which E3 ligases are worth a ligand campaign, and asking at nomination whether a target even has a usable lysine.

Molecular glues have been sitting in the PDB for thirty years, deposited by
crystallographers who were solving something else and had no reason to label the
ligand as one. BINMAN is the inventory: an empirical atlas of every non-polymer
entity that buries meaningful surface against two or more distinct polymer
chains at once, with the crystallisation furniture classified rather than quietly
deleted.

Around that atlas sit three more modules that answer the questions a degrader
programme actually fails on, and one small language model that does the text
work and none of the arithmetic.

## What it does

| Module | Question | Method |
|---|---|---|
| **Glue Atlas** | Which deposited ligands bridge two protein chains? | ΔSASA against each chain, heavy-atom contacts, bridging balance, PLIP interaction typing at both half-interfaces |
| **Degron Scan** | Which human proteins carry the β-hairpin-with-exposed-glycine geometry that CRBN reads? | DSSP over the AlphaFold human proteome, found by geometry rather than by sequence motif |
| **E3 Triage** | Which E3 ligases are under-exploited and worth a ligand campaign? | InterPro family assignment, fpocket druggability, expression selectivity, substrate counts, ranked by a transparent weighted sum with every component visible |
| **Degradability** | Does this target have a usable lysine near the binding site? | Lysine NZ accessibility and Cβ–Cβ geometry relative to a chosen site, against a reach window fitted to observed ubiquitylation sites rather than assumed |

## The two rules the project is built on

**Every module is validated against independently curated published datasets,
never against controls written for this project.** Where a dataset cannot be
obtained, the metric that depends on it is reported as not computed, with the
reason. It is never filled in with a substitute. `FINDINGS.md` states every
number with its method and its n, and
[`data/validation/MANIFEST.md`](data/validation/MANIFEST.md) records the
version, licence, row count and retrieval date of every dataset used.

**The language model never computes, estimates or reports a number.** ΔSASA,
Cβ–Cβ distances, pocket scores and pLDDT are computed deterministically in
Python and passed to the interface. BINMAN-LM does three text jobs only:
natural language to query object, evidence-class triage, and structured
abstention. A number in its output that was not copied verbatim from a
retrieved record is a defect, not a feature.

## Current state

Phase 1 of four. See [`PROGRESS.md`](PROGRESS.md) for the live checklist,
[`BUILD_LOG.md`](BUILD_LOG.md) for the event log and
[`DECISIONS.md`](DECISIONS.md) for every judgement call with its reasoning and
how to reverse it.

An early result worth stating: the bridging filter recovers five of six
canonical glues with literature-consistent interface residues, and it shows
that a genuine CRBN neosubstrate glue is **strongly asymmetric** (bridging
balance 0.33 to 0.36, against 0.88 for rapamycin). An intuitive symmetry
threshold would have rejected exactly the class the project exists to find.
That is in `FINDINGS.md` with the numbers.

## 🎓 BINMAN-LM: training strategy

The model does three text jobs and no arithmetic. Every number in BINMAN is
computed deterministically in Python and passed to the interface; the model's
only numeric output is a filter threshold the user then sees in the query stack.

**Base model.** `Qwen2.5-3B-Instruct`, 4-bit, through `mlx-lm` on an M2 Ultra.
3B is deliberate: the tasks are structured translation against a closed schema,
not open-ended reasoning, and a small model that fits comfortably in unified
memory can be retrained in minutes rather than hours.

**The baseline runs first, and it decides whether to train at all.** Zero-shot
with the full schema in context, the base model reached set equality 0.233 and a
parse rate of 0.283, well under the 0.85 threshold at which fine-tuning would
have been skipped in favour of grammar-constrained decoding. So it was trained.

### Rounds

Runs are tracked in Weights & Biases under `binman-lm`, named to the convention
used across the other projects.

| Round | Stage | Outcome |
|---|---|---|
| `binman-qwen-2.5-3b-4bit-round01` | LoRA SFT, rank 16, 16 layers, lr 1e-5, 1200 iterations | **Shipped.** Validation loss 2.494 to 0.001. |
| `binman-qwen-2.5-3b-4bit-round02` | DPO, beta 0.1, lr 1e-5, 600 steps | Rejected: collapsed the model. |
| `binman-qwen-2.5-3b-4bit-round03` | DPO, beta 0.1, lr 5e-7, 150 steps | Rejected: still degraded. |

Round 01 is what serves. It turned parse rate 0.283 into **0.992** and set
equality 0.233 into **0.992**, and it internalised the schema well enough that
inference needs 83 prompt tokens where the baseline needed 841.

### Why DPO was attempted

Supervised fine-tuning only ever shows the model correct answers, so it learns
the shape of a right answer but never the boundary between a right one and a
plausible wrong one. Direct Preference Optimisation trains on pairs: the same
question with a correct query object and a deliberately corrupted one, teaching
the model to prefer the first. BINMAN's pairs cover seven corruption modes, 200
each, generated rather than curated:

| Mode | The corruption | What it teaches |
|---|---|---|
| `hallucinated_field` | a plausible field that does not exist | stay inside the schema |
| `operator_inversion` | `gt` becomes `lt` | above against below |
| `unit_confusion` | ΔSASA quoted in Å rather than Å² | domain units are not interchangeable |
| `dropped_constraint` | three clauses in, two out | completeness |
| `invented_entity` | a ligase not in the vocabulary | closed-world discipline |
| `wrong_question` | valid JSON, different intent | semantic fidelity |
| `prose_not_json` | a chatty explanation | format discipline |

### Why it did not ship

Both DPO attempts reached a near-zero loss by collapsing the policy rather than
learning the preference. The first emitted `ccdccdccd…` indefinitely.

The instructive part is that **the metric could not see it**: per-mode preference
win rates measured 0.95 to 1.00 on the collapsed model, because a degenerate
policy trivially assigns a higher likelihood to one string than another. The
adapter would have shipped on those numbers.

So a generation guard now runs held-out test questions through any candidate
adapter and requires 80% to produce a query object the real parser accepts,
before it is allowed to ship. Stage 1 scores 10 of 10; the DPO adapters scored 6
of 10 and 0 of 10 and were refused. Stage 1 already clears every floor it is
measured against, so the preference stage was an improvement on an
already-passing model rather than a requirement.

`mlx-lm` 0.32 ships no preference trainer at all, so the DPO loop is this
project's own code against its LoRA machinery, with reference log-probabilities
cached once from the frozen stage 1 model.

### Serving

BINMAN-LM serves as base model plus adapter, not as a fused model: fusing against
the 4-bit base produced a model that parsed 0 of 10 held-out questions and
invented its own output schema, so the artefact was deleted rather than shipped.
The endpoint is a feature flag. With `BINMAN_LM_URL` unset the natural-language
box is hidden and nothing else changes.

## Repository layout

```
pipeline/     compute stages, each resumable and manifest-backed
app/          Flask app, Mol* viewers, the Depot design system
lm/           BINMAN-LM corpus generation and training scripts
tools/        hardware probe, asset vendoring
config/       hardware.toml and tuning.toml (generated), thresholds.toml (authored)
data/         caches, manifests, validation derivatives (not redistributed)
deploy/       written, never executed
tests/        geometry against hand-computed cases, parser grid, schema integrity
```

Two things live in config and nowhere else: **hardware settings** come from
`config/tuning.toml`, so no core count or memory figure is hard-coded anywhere,
and **every scientific threshold** comes from `config/thresholds.toml`, so no
cutoff is a literal in Python.

## ▶️ Running it

```bash
pixi install                              # compute environment, osx-arm64
pixi run hwprobe                          # writes config/hardware.toml and tuning.toml
pixi run python pipeline/acquire_validation.py
```

The compute environment needs macOS 14.5 or newer, because every available
`fpocket` build requires it.

## 📄 Licence and reuse

The code in this repository is available for reuse. The data is not ours to
give: BINMAN reads ten third-party databases, several of which restrict
redistribution, so no third-party dataset is bundled here or in the deployed
atlas. Only computed metrics leave the build machine. If you reuse the atlas,
read `data/validation/MANIFEST.md` first and cite the underlying resources
separately.

## 👤 Author

**Marc C. Deller, D.Phil.**
Structural biologist and drug discovery scientist
[marcdeller.com](https://marcdeller.com) · [marc@marcdeller.com](mailto:marc@marcdeller.com)

<!--
This is the crude source that tools/readme_forge.py polishes into the repository
README.md (house standard, spec 4.6). Edit this file, then run:

    pixi run python tools/readme_forge.py docs/README.source.md
    cp docs/README.source.polished.md README.md

The forge adds the branded header, the badge row, the contact table and the
author footer, and rewrites GitHub links to this repository. Its palette is the
marcdeller.com site palette, not the app's Depot palette, which applies only to
the running interface.
-->
