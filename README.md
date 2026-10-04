# 🗑️ BINMAN

> **Molecular glues have been sitting in the PDB for thirty years, deposited without being labelled as such. This is the inventory.**

![python](https://img.shields.io/badge/python-3.11-3776AB?logo=python&logoColor=white) ![environment](https://img.shields.io/badge/environment-pixi%20%2B%20uv-1e73be) ![structures](https://img.shields.io/badge/structures-52821%20entries-2C6D60) ![validation](https://img.shields.io/badge/validation-published%20datasets%20only-D65B0A) ![licence](https://img.shields.io/badge/licence-code%20reusable-6A6F68) ![author](https://img.shields.io/badge/author-Marc%20C.%20Deller,%20D.Phil.-1C244B)

<table>
<tr>
<td>🌐 <b>Website</b></td><td><a href="https://marcdeller.com" target="_blank" rel="noopener noreferrer">marcdeller.com</a></td>
<td>✉️ <b>Contact</b></td><td><a href="mailto:marc@marcdeller.com">marc@marcdeller.com</a></td>
<td>🐙 <b>GitHub</b></td><td><a href="https://github.com/bellcheddar/BINMAN" target="_blank" rel="noopener noreferrer">bellcheddar/BINMAN</a></td>
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
| **Degron Scan** | Which human proteins carry the β-hairpin-with-exposed-glycine geometry that CRBN reads? | DSSP over the AlphaFold human proteome, found by geometry rather than by sequence motif. **Validated and failed:** against a matched published screen it scores AUC 0.44, so it ships as a hypothesis generator, not a classifier (see [FINDINGS](FINDINGS.md#section-92-degron-scan-validation)) |
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

## 📚 Source data

Nothing in BINMAN is hand-written ground truth. Every dataset below is
independently curated and published, every reference is Crossref-verified at
build time by [`pipeline/references.py`](pipeline/references.py), and
[`data/validation/MANIFEST.md`](data/validation/MANIFEST.md) records the
version, licence, row count and retrieval date of each one.

**10 of 12 validation datasets resolved.** A metric whose dataset did
not resolve is reported as not computed, never estimated and never replaced
by a control written for this project.

### Validation datasets: the ground truth every metric is judged against

| Dataset | Licence | Rows | Resolved | Reference | DOI |
|---|---|---|---|---|---|
| `biolip2_artefacts` | BSD-2-Clause (Zhang-Freddolino lab, mmCIF2BioLiP) | 463 | yes | Zhang *et al.* 2023 | [10.1093/nar/gkad630](https://doi.org/10.1093/nar/gkad630) |
| `biolip2_annotations` | free for academic use, redistribution not granted in writing | 1,071,951 | yes | Zhang *et al.* 2023 | [10.1093/nar/gkad630](https://doi.org/10.1093/nar/gkad630) |
| `mgdb_glues` | open access; no redistribution terms stated | 10,263 | yes | Li *et al.* 2025 | [10.1093/nar/gkaf1131](https://doi.org/10.1093/nar/gkaf1131) |
| `molgluedb_glues` | free and open access; no redistribution terms stated | 1,840 | yes | Wang *et al.* 2025 | [10.1093/nar/gkaf811](https://doi.org/10.1093/nar/gkaf811) |
| `mgtbind_ternary` | open access; no redistribution terms stated | 3,924 | yes | Zhu *et al.* 2025 | [10.1093/nar/gkaf1075](https://doi.org/10.1093/nar/gkaf1075) |
| `mgtbind_compounds` | open access; no redistribution terms stated | 3,093 | yes | Zhu *et al.* 2025 | [10.1093/nar/gkaf1075](https://doi.org/10.1093/nar/gkaf1075) |
| `protacdb_protacs` | internal use only, derivatives included; redistribution prohibited (H... | 15,502 | yes | Ge *et al.* 2024 | [10.1093/nar/gkae768](https://doi.org/10.1093/nar/gkae768) |
| `sievers_zf_screen` | open supplement, Science author-choice | 5,663 | yes | Sievers *et al.* 2018 | [10.1126/science.aat0572](https://doi.org/10.1126/science.aat0572) |
| `ubibrowser_literature_e3` | not determined | 3,158 | yes | Wang *et al.* 2021 | [10.1093/nar/gkab962](https://doi.org/10.1093/nar/gkab962) |
| `ubibrowser_predicted_e3` | not determined | 113,656 | yes | Wang *et al.* 2021 | [10.1093/nar/gkab962](https://doi.org/10.1093/nar/gkab962) |
| `degronopedia` | not determined | not resolved | **no** | Szulc *et al.* 2024 | [10.1093/nar/gkae238](https://doi.org/10.1093/nar/gkae238) |
| `protcid_interfaces` | free for academic use | not resolved | **no** | Xu *et al.* 2010 | [10.1093/nar/gkq1059](https://doi.org/10.1093/nar/gkq1059) |

The three curated glue databases are used together rather than pooled
uncritically: a compound counts as a molecular glue for LM Task B only when at
least two of MGDB, MolGlueDB and MGTbind agree on it, matched by InChIKey
skeleton so that stereochemistry and salt form do not split one compound across
databases. The disagreements are written out to
`data/validation/glue_disagreements.tsv` rather than resolved by fiat.

### Primary sources: where the structures, sequences and annotations come from

| Source | What it supplies | Reference | DOI |
|---|---|---|---|
| The Protein Data Bank | every deposited structure, assembly and chemical component | Berman 2000 | [10.1093/nar/28.1.235](https://doi.org/10.1093/nar/28.1.235) |
| PDBe: searching the Protein Data Bank | assembly definitions and entity cross-references | EMBL-EBI | [10.6019/tol.pdbe-sea-t.2015.00001.1](https://doi.org/10.6019/tol.pdbe-sea-t.2015.00001.1) |
| Chemical Component Dictionary | the dictionary the 11-class chemical component classifier reads | RCSB Protein Data Bank, 2019 | [10.2210/wwpdb/doc_ccd](https://doi.org/10.2210/wwpdb/doc_ccd) |
| AlphaFold Protein Structure Database: massively expanding the structural coverage of protein-sequence space with high-accuracy models | the human proteome models the Degron Scan runs over, with pLDDT in the B-factor column | Varadi *et al.* 2021 | [10.1093/nar/gkab1061](https://doi.org/10.1093/nar/gkab1061) |
| UniProt: the universal protein knowledgebase | the reviewed human proteome, accessions and gene names | UniProt Consortium 2018 | [10.1093/nar/gky092](https://doi.org/10.1093/nar/gky092) |
| InterPro: An integrated documentation resource for protein families, domains and functional sites | the family signatures that place each E3 in a RING, HECT, RBR, F-box, BTB, CULT or VHL-box class | Briefings in Bioinformatics, 2002 | [10.1093/bib/3.3.225](https://doi.org/10.1093/bib/3.3.225) |
| Open Targets Platform: supporting systematic drug–target identification and prioritisation | expression selectivity and tractability for the E3 ranking | Ochoa *et al.* 2020 | [10.1093/nar/gkaa1027](https://doi.org/10.1093/nar/gkaa1027) |
| Europe PMC: a full-text literature database for the life sciences and platform for innovation | the abstracts behind the literature-derived Task B classes | Nucleic Acids Research, 2014 | [10.1093/nar/gku1061](https://doi.org/10.1093/nar/gku1061) |

### Papers the biology and the thresholds rest on

| Paper | What it establishes for BINMAN | Reference | DOI |
|---|---|---|---|
| Lenalidomide Causes Selective Degradation of IKZF1 and IKZF3 in Multiple Myeloma Cells | lenalidomide degrades IKZF1 and IKZF3: the neosubstrate effect the atlas is aimed at | Krönke *et al.* 2014 | [10.1126/science.1244851](https://doi.org/10.1126/science.1244851) |
| Structure of the DDB1–CRBN E3 ubiquitin ligase in complex with thalidomide | the DDB1-CRBN-thalidomide structure, and the asymmetric interface the bridging filter has to tolerate | Fischer *et al.* 2014 | [10.1038/nature13527](https://doi.org/10.1038/nature13527) |
| The Eukaryotic Proteome Is Shaped by E3 Ubiquitin Ligases Targeting C-Terminal Degrons | the C-terminal glycine degron: the geometry the Degron Scan looks for | Koren *et al.* 2018 | [10.1016/j.cell.2018.04.028](https://doi.org/10.1016/j.cell.2018.04.028) |
| Defining the human C2H2 zinc finger degrome targeted by thalidomide analogs through CRBN | **the matched degraded and non-degraded zinc-finger sets spec 9.2 is measured against.** 5,663 domains, 32 depleted by an IMiD, 5,631 assayed and not depleted | Sievers *et al.* 2018 | [10.1126/science.aat0572](https://doi.org/10.1126/science.aat0572) |
| CK1α Degradation Underlies Lenalidomide Activity in del(5q) MDS | CSNK1A1 as a lenalidomide neosubstrate, one of the five calibration degrons | Cancer Discovery, 2015 | [10.1158/2159-8290.cd-rw2015-130](https://doi.org/10.1158/2159-8290.cd-rw2015-130) |
| Anticancer sulfonamides target splicing by inducing RBM39 degradation via recruitment to DCAF15 | DCAF15 and RBM39: a glue that works through an RRM surface rather than a hairpin | Han *et al.* 2017 | [10.1126/science.aal3755](https://doi.org/10.1126/science.aal3755) |
| The CDK inhibitor CR8 acts as a molecular glue degrader that depletes cyclin K | CR8 and cyclin K: a kinase inhibitor that turned out to be a glue, which is the blind spot the project is named for | Słabicki *et al.* 2020 | [10.1038/s41586-020-2374-x](https://doi.org/10.1038/s41586-020-2374-x) |
| Auxin and TIR1 Ubiquitin Ligase | TIR1 and auxin: the plant-hormone glue the size-guarded classifier must not call a buffer | Goodsell 2009 | [10.2210/rcsb_pdb/mom_2009_2](https://doi.org/10.2210/rcsb_pdb/mom_2009_2) |
| Structure of the FKBP12-Rapamycin Complex Interacting with Binding Domain of Human FRAP | FKBP12, rapamycin and FRB: the symmetric reference point, bridging balance 0.88 | Choi *et al.* 1996 | [10.1126/science.273.5272.239](https://doi.org/10.1126/science.273.5272.239) |
| Maximum Allowed Solvent Accessibilites of Residues in Proteins | the maximum accessible surface areas that turn absolute SASA into relative SASA | Tien *et al.* 2013 | [10.1371/journal.pone.0080635](https://doi.org/10.1371/journal.pone.0080635) |
| Systematic and Quantitative Assessment of the Ubiquitin-Modified Proteome | the observed ubiquitylation sites the Degradability reach window is fitted to | Kim *et al.* 2011 | [10.1016/j.molcel.2011.08.025](https://doi.org/10.1016/j.molcel.2011.08.025) |
| PhosphoSitePlus, 2014: mutations, PTMs and recalibrations | curated PTM sites, for the degradability AUC that remains not computed | Hornbeck *et al.* 2014 | [10.1093/nar/gku1267](https://doi.org/10.1093/nar/gku1267) |

### Software and methods

| Tool | Used for | Reference | DOI or URL |
|---|---|---|---|
| FreeSASA: An open source C library for solvent accessible surface area calculations | Lee-Richards solvent accessible surface area at probe 1.4 Å, the basis of every ΔSASA | Mitternacht 2016 | [10.12688/f1000research.7931.1](https://doi.org/10.12688/f1000research.7931.1) |
| Dictionary of protein secondary structure: Pattern recognition of hydrogen‐bonded and geometrical features | secondary structure and antiparallel bridge partners for hairpin detection | Kabsch *et al.* 1983 | [10.1002/bip.360221211](https://doi.org/10.1002/bip.360221211) |
| GEMMI: A library for structural biology | mmCIF parsing and biological assembly expansion | Wojdyr 2022 | [10.21105/joss.04200](https://doi.org/10.21105/joss.04200) |
| Fpocket: An open source platform for ligand pocket detection | pocket detection and druggability scoring for the E3 ranking | Le Guilloux *et al.* 2009 | [10.1186/1471-2105-10-168](https://doi.org/10.1186/1471-2105-10-168) |
| P2Rank: machine learning based tool for rapid and accurate prediction of ligand binding sites from protein structure | pocket scoring cross-check | Krivák *et al.* 2018 | [10.1186/s13321-018-0285-8](https://doi.org/10.1186/s13321-018-0285-8) |
| PLIP 2021: expanding the scope of the protein–ligand interaction profiler to DNA and RNA | interaction typing at both half-interfaces of every bridge | Adasme *et al.* 2021 | [10.1093/nar/gkab294](https://doi.org/10.1093/nar/gkab294) |
| RDKit: Open-source cheminformatics | structural chemistry rules, and InChIKey skeletons for cross-database matching | Landrum *et al.* | [www.rdkit.org/](https://www.rdkit.org/) |
| Open Babel: An open chemical toolbox | chemical format conversion | O'Boyle *et al.* 2011 | [10.1186/1758-2946-3-33](https://doi.org/10.1186/1758-2946-3-33) |
| Biotite: a unifying open source computational biology framework in Python | structure handling in the geometry pipeline | Kunzmann *et al.* 2018 | [10.1186/s12859-018-2367-z](https://doi.org/10.1186/s12859-018-2367-z) |
| DuckDB-wasm | analytical queries over the atlas | Kohn *et al.* 2022 | [10.14778/3554821.3554847](https://doi.org/10.14778/3554821.3554847) |
| Mol* Viewer: modern web app for 3D visualization and analysis of large biomolecular structures | the in-browser structure viewer | Sehnal *et al.* 2021 | [10.1093/nar/gkab314](https://doi.org/10.1093/nar/gkab314) |
| D³ Data-Driven Documents | the interface schematics | Bostock *et al.* 2011 | [10.1109/tvcg.2011.185](https://doi.org/10.1109/tvcg.2011.185) |
| Tabulator: interactive tables and data grids | every data table in the app | Folkerd | [tabulator.info/](https://tabulator.info/) |
| Plotly.js: open source JavaScript charting library | the distribution plots | Plotly Technologies Inc. | [plotly.com/javascript/](https://plotly.com/javascript/) |
| Flask: a lightweight WSGI web application framework | the application server | Ronacher *et al.* | [flask.palletsprojects.com/](https://flask.palletsprojects.com/) |
| MLX: efficient and flexible machine learning on Apple silicon | LoRA fine-tuning on Apple silicon | Hannun *et al.* 2023 | [github.com/ml-explore/mlx](https://github.com/ml-explore/mlx) |
| Qwen2.5-3B-Instruct model card | the base model behind BINMAN-LM | Qwen Team 2024 | [huggingface.co/Qwen/Qwen2.5-3B-Instruct](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct) |

Full machine-readable list: [`data/validation/references.json`](data/validation/references.json) and
`references.bib`. 45 rows, 39 Crossref verified by title match rather than by
DOI string alone, 6 with no citeable paper (software, kept with its canonical URL
rather than dropped), and every licence that could not be determined recorded
as such rather than guessed.

## Current state

All four phases are built and QC'd. See [`PROGRESS.md`](PROGRESS.md) for the
live checklist, [`BUILD_LOG.md`](BUILD_LOG.md) for the event log and
[`DECISIONS.md`](DECISIONS.md) for every judgement call with its reasoning and
how to reverse it.

**52,821 entries, 239,485 bridges, 14,260 of them novel** (appearing in none of
the three curated glue databases), 21,717 degron candidates, 650 E3 ligases.
Section 9: four floors measured and passed, four measured and missed, four not
computed for want of a dataset. Every miss is diagnosed rather than hidden, and
two of them are worth more than a pass would have been: the degron geometry
filter scores AUC 0.44 against a matched published screen and is therefore
relabelled a hypothesis generator (D-024), and the glue recall deficit is
traced to a single spec criterion that no permitted adjustment can rescue
(D-027).

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
