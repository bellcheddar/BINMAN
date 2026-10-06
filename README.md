# 🗑️ BINMAN

> **Molecular glues have been sitting in the PDB for thirty years, deposited without being labelled as such. This is the inventory.**

![python](https://img.shields.io/badge/python-3.11-3776AB?logo=python&logoColor=white) ![environment](https://img.shields.io/badge/environment-pixi%20%2B%20uv-1e73be) ![bridges](https://img.shields.io/badge/bridges-283131-2C6D60) ![validation](https://img.shields.io/badge/validation-published%20datasets%20only-D65B0A) ![licence](https://img.shields.io/badge/licence-code%20reusable-6A6F68) ![author](https://img.shields.io/badge/author-Marc%20C.%20Deller,%20D.Phil.-1C244B)

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
| **Degron Scan** | Which human proteins carry a zinc finger a glutarimide will degrade? | Two columns with different jobs. `imid_degradation_score` is a sequence model on C2H2-anchored chemical groups, weighted by a measured alanine scan: nested AUC **0.830**, and gene-disjoint it transfers above chance to **24 of 29** glutarimide analogs. Remove every training row sharing an anchored core with the panel and that transfer falls to 0.579 at p=0.16, so it is partly carried by core identity rather than a learned grammar. `degron_geometry_score` ranks hairpin shape and is a hypothesis generator, not a classifier |
| **E3 Triage** | Which E3 ligases are under-exploited and worth a ligand campaign? | InterPro family assignment, fpocket druggability, expression selectivity, substrate counts, ranked by a transparent weighted sum with every component visible |
| **Degradability** | Does this target have a usable lysine near the binding site? | Lysine NZ accessibility and Cβ-Cβ geometry from a chosen site, measured against **419,405 lysines assayed by mass spectrometry**, 110,108 ubiquitylated and 309,297 seen and found unmodified. The window is not fitted and no verdict is emitted, because the measurement says it should not be |

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

## What it found

**55,449 entries, 285,996 bridges, 15,804 of them novel**, meaning they appear
in none of the three curated glue databases. 27,605 bridges carry a ligand
classed as a glue candidate; the remaining crystallisation furniture is
classified rather than deleted, so the counts reconcile. 21,717 degron
candidates over 8,983 proteins, 7,452 C2H2 zinc fingers scored individually,
650 E3 ligases ranked, 30,057 edges in the shared network.

**The atlas surfaced the RAS(ON) tri-complex glues unprompted.** 30 entries and
19 ligands of the zoldonrasib and elironrasib series, which glue a KRAS mutant
to cyclophilin A and are in clinical development, rank at the top of the novel
bridges by buried area. Three independent signals had to agree: the geometric
bridging filter found them with no knowledge of what they are, the novelty flag
says no curated glue database lists them, and BINMAN-LM's triage head, reading
only a title and a ligand name, called them molecular glues. Finding is not
predicting, since these were deposited by people who already knew: what it
measures is that the pipeline agrees with that knowledge without being given it,
on a class the databases have not yet absorbed.

Three further results are worth stating on their own.

**A real CRBN neosubstrate glue is strongly asymmetric.** Bridging balance 0.33
to 0.36, against 0.88 for rapamycin. An intuitive symmetry threshold would have
rejected exactly the class the project exists to find.

**The glutarimide degron grammar is shared across the chemical series.** A model
trained on pomalidomide alone transfers above chance to 24 of the 29 analogs of
a published screen, gene-disjoint, mean AUC 0.779 at permutation p=0.0005. The
obvious hypothesis, that promiscuous compounds should be less predictable, was
tested across all 29 and is not supported.

**Lysine exposure does not predict ubiquitylation.** Against 309,297 lysines
assayed and found unmodified, rather than lysines nobody had annotated, exposure
scores 0.502: chance. The two labellings disagree on 41% of lysines. Reach from
the ligand site, measured in 43 induced ternary complexes, scores 0.42 to 0.48,
because the ligand site is where a substrate is recruited and not where
ubiquitin is transferred.

### What the first rule costs

The rule above has a price, and it is paid in public. Of the twenty-one spec
Section 9 metrics: ten pass, seven miss their floor and four are not computable
for want of a dataset. The misses are diagnosed rather than hidden, and the
diagnosis is usually the useful part.

**The miss count went up because the metrics got more honest.** Three figures
had no floor they could fail against. Task C's abstention rate is measured on
unanswerable questions only, so a model that refuses everything scores
perfectly; it does refuse everything, and the complement now carries a floor and
reads 0.000. Task A's headline figures are measured on questions from the same
generator that wrote the training set and read 1.000, while the fifteen phrased
as a person would ask them read 0.067 and carried no floor at all. They do now.
A metric that cannot fail is not a check.

Glue recall used to be one of them, at 0.825 against a 0.85 floor, and the
diagnosis was that the gap was dominated by homo-oligomeric glues the inclusion
criterion excluded by construction: a homodimer is one entity whatever its
chain count, so FKBP12 with FK1012 and transthyretin with tafamidis were never
fetched. Widening the catalogue to those entries took recall to **0.8781**, 281
of 320 curated glues, and the floor is met. That is what the diagnoses are for.

Full accounting in [`FINDINGS.md`](FINDINGS.md), with every judgement call and
how to reverse it in [`DECISIONS.md`](DECISIONS.md).

## 🎓 BINMAN-LM

The model does three text jobs and no arithmetic. Every number in BINMAN is
computed deterministically in Python; the model's only numeric output is a
filter threshold the user then sees in the query stack.

**What ships.** `Qwen2.5-3B-Instruct` at 4 bit, LoRA over the last 32 layers,
through `mlx-lm` on an M2 Ultra. 3B is deliberate: the tasks are structured
translation against a closed schema, not open-ended reasoning.

| Task | Metric | Score | Floor |
|---|---|---:|---:|
| Natural language to query object | parse rate | **1.000** | 0.99 |
| | set equality | **1.000** | 0.90 |
| Ligand triage from an abstract | macro F1 | **0.9336** | 0.85 |
| Structured abstention | fabrication rate | **0.000** | 0.00 |

**All three heads now do work.** Query drives the "Ask in words" box. Triage
fills `evidence_class` for 6,510 entry-ligand pairs across 27,590 bridge rows,
the only model-derived column in the atlas, agreeing with the curated label on
14 of 15 chemical components it had never seen. Abstention answers questions
the atlas cannot: of 20 held-out unanswerable questions, 16 that used to return
a parser error now return an explanation naming what is missing.

Four of those 20 still produce a query the schema accepts and the atlas cannot
support. Asked for a binding affinity in nanomolar the model filters on buried
area and molecular weight. Nothing fails, so nothing catches it, and the only
defence is that the query it built is shown to the user. That is the sharpest
limit on this box and it is measured rather than hedged.

The baseline decides whether to train at all. Zero-shot with the full schema in
context the base model reached set equality 0.233, well under the 0.85 at which
fine-tuning would have been skipped for grammar-constrained decoding. Training
turned that into 1.000, and the model internalised the schema well enough that
inference needs 83 prompt tokens where the baseline needed 841.

**Depth is the lever.** An ablation over layers, rank and epochs found that
training more layers is what moves the metrics, that rank and epoch count do
not, and that combining them loses. Scale was then tested directly: a 32B
trained for a full epoch matches the 3B on parse, set equality and abstention,
all at ceiling, and is behind by two classifications out of 240 on triage. Ten
times the parameters bought nothing measurable, so the 3B ships (D-071).

**Serving.** Base model plus adapter rather than a fused model, behind a
feature flag. With `BINMAN_LM_URL` unset the natural-language box is hidden and
nothing else changes, which is why the live deployment runs without it.

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
