# BINMAN

**Blind-spot INventory of Molecular Adhesives and Neosubstrates**

Nature has been depositing molecular glues in the PDB for thirty years without
labelling them as such. BINMAN is the inventory: an empirical atlas of every
non-polymer entity that buries meaningful surface against two or more distinct
polymer chains at once, with the crystallisation furniture classified rather
than quietly deleted.

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

## Running it

```bash
pixi install                              # compute environment, osx-arm64
pixi run hwprobe                          # writes config/hardware.toml and tuning.toml
pixi run python pipeline/acquire_validation.py
```

The compute environment needs macOS 14.5 or newer, because every available
`fpocket` build requires it.

## Licence and reuse

The code in this repository is available for reuse. The data is not ours to
give: BINMAN reads ten third-party databases, several of which restrict
redistribution, so no third-party dataset is bundled here or in the deployed
atlas. Only computed metrics leave the build machine. If you reuse the atlas,
read `data/validation/MANIFEST.md` first and cite the underlying resources
separately.

## Author

**Marc C. Deller, D.Phil.**
Structural biologist and drug discovery scientist
[marcdeller.com](https://marcdeller.com) · [marc@marcdeller.com](mailto:marc@marcdeller.com)
