# BINMAN Build Spec

**Blind-spot INventory of Molecular Adhesives and Neosubstrates**

Spec version: 1.2 (2026-10-03)

> **Changes in 1.2:** adds the About tab (spec 6.6): a generated workflow schematic, a BINMAN-LM model card, a full reference table with DOIs and licences, and a deterministically selected worked example carried through all four modules.
>
> **Changes from 1.0:** every module is now validated against published, independently curated datasets rather than against hand-written controls. The degradability reach window is calibrated and validated against observed ubiquitylation sites rather than assumed. Gate G7 (canary set) is removed: the held-out query set is harvested from published review articles instead. Section 9 is rewritten in full.
Project root: `/Users/dellboy/Documents/Vibe_Coding/binman/`
Target host: `binman.mdeller.com` on mdeller.com
Build machine: Marc's Mac Studio (Apple Silicon), unattended

---

## Section 0: Autonomy Directive

### Continuous Build Rules

1. **Run to completion without asking.** When a choice is ambiguous, pick the most defensible option, write it to `DECISIONS.md` (decision, alternatives considered, reason, how to reverse it) and carry on. Every "ask Marc" step in any skill invoked during this build becomes "decide, log, continue".
2. **Stop only at a Gate** (table below). A failing tool, a missing package or a slow step is a problem to solve, not a reason to stop.
3. **Fallback ladder for any failure:** retry once with a fix, then the documented alternative, then the next-best tool, then degrade gracefully (skip the item, flag it in the data as `status = "failed:<reason>"`, continue). One PDB entry, one ligase or one optional feature never blocks the pipeline.
4. **Resumable and idempotent.** Every stage writes a manifest to `data/manifests/<stage>.jsonl`. On restart, read `PROGRESS.md` and the manifests and skip completed items. Assume the process can be killed at any moment.
5. **Log as you go.** `BUILD_LOG.md` (timestamped, one line per meaningful event) and `PROGRESS.md` (phase checklist with percentages, rewritten after every phase and at least every 30 minutes during long compute).
6. **Never idle.** If a phase depends on long-running compute, build it against the data already available, mark missing fields "pending", and backfill automatically when the manifests show completion.
7. **Commit locally, never push.** `git commit` at the end of every phase with `phase N: <summary>`. No `git push` (Gate G4).
8. **Stay inside the project root.** No writes outside `/Users/dellboy/Documents/Vibe_Coding/binman/` except package caches (pixi, uv, pip, Hugging Face, Homebrew). Never `sudo`.
9. **Keep the Mac awake:** wrap long compute in `caffeinate -dimsu <command>`.
10. **House style everywhere:** British English, no em dashes (colons or parentheses instead), none of: groundbreaking, revolutionary, paradigm-shifting, game-changing, cutting-edge, unprecedented, seamless, leverage (verb), delve.

### Gates

| Gate | Opens when | Needs from Marc |
|------|------------|-----------------|
| **G1 Compute** | The MLX smoke test fails on both MPS and CPU, or the projected pipeline run exceeds `MAX_COMPUTE_HOURS` (default 96) after automatic scope reduction | Accept reduced scope, raise the budget, or supply a cloud GPU |
| **G2 Secrets** | Any credential is needed (Hugging Face token for a gated model, Open Targets key, SSH keys) | The secret via environment variable, never written into files |
| **G3 Deploy** | The app passes QC locally and is ready for the droplet | Approval to rsync, plus DNS, nginx and certbot |
| **G4 Publish** | Any `git push`, repo creation or public release | Approval |
| **G5 Disk** | Free space on the project volume falls below 50 GB | What to prune, or a new data volume |
| **G6 Science** | A Section 9 validation metric misses its stated floor after the fallback ladder and one documented threshold adjustment | Decision to proceed with a flagged caveat |
| **G7 Dataset access** | A Section 9 validation dataset cannot be obtained: download fails, the licence forbids local redistribution, or the format has changed beyond the parser | Confirmation to proceed without it. **Non-blocking:** continue with the datasets that do resolve, record the gap in `FINDINGS.md`, and never substitute a hand-written control in its place |

**Gate protocol:** write `GATE_OPEN.md` (which gate, exactly what is needed, the command or answer that unblocks it, what is already done, what happens next); send

```bash
osascript -e 'display notification "<one line>" with title "BINMAN gate <id>" sound name "Glass"'
```

then keep working on everything the gate does not block, and stop only when nothing unblocked remains.

### Launch recipe

```bash
cd /Users/dellboy/Documents/Vibe_Coding/binman
tmux new -s binman
claude
# then: "Read BINMAN_BUILD_SPEC.md and execute it end to end under Section 0."
```

---

## Section 1: Goals

Every figure, table and feature in this build maps to one of these.

**G-1.** Build an empirical atlas of **bridging ligands** in the PDB: every non-polymer entity that buries meaningful surface against two or more distinct polymer chains simultaneously, classified by evidence type, with the crystallisation furniture stripped out. Nature has been depositing molecular glues for thirty years without labelling them as such; this is the inventory.

**G-2.** Scan the human predicted proteome for **structural degrons**: the β-hairpin-with-exposed-glycine geometry that underlies CRBN neosubstrate recognition, found by geometry rather than by sequence motif, validated against published zinc-finger degradation screens that supply matched degraded and non-degraded sets from the same experiment.

**G-3.** Triage the human **E3 ligase repertoire** on ligandability, structural coverage, expression selectivity and family, to produce a ranked shortlist of under-exploited ligases worth a ligand campaign.

**G-4.** Score **degradability** for any target: surface lysine accessibility and geometry relative to a chosen binding site, which is the question that kills degrader programmes late and is rarely asked at nomination.

**G-5.** Ship a single small language model (**BINMAN-LM**) fine-tuned with mlx-lm that does three text jobs and no arithmetic: natural language to query object, evidence-class triage of entry and abstract text, and structured abstention.

**G-6.** Deliver all of it as an interactive Flask app with Mol* viewers on every module, hosted as a precomputed read-only atlas the droplet can serve.

**G-7.** Validate every module against **independently curated published datasets**, never against controls written for this project. Section 9 defines the datasets, the positive and negative sets drawn from each, the metric and the floor. A module with no external validation is not finished.

**Explicitly out of scope.** The language model never computes, estimates or reports a numeric value. ΔSASA, Cβ–Cβ distances, pocket scores and pLDDT are computed deterministically in Python and passed to the UI. If BINMAN-LM is ever observed emitting a number that was not copied verbatim from a retrieved record, that is a defect, not a feature.

---

## Section 2: Hardware (Mac Studio Performance Rules)

### 2.1 Probe first (Phase 1.0)

`tools/hwprobe.py` writes `config/hardware.toml` from:

- chip: `sysctl -n machdep.cpu.brand_string`
- performance and efficiency cores: `sysctl -n hw.perflevel0.physicalcpu`, `hw.perflevel1.physicalcpu`
- unified memory: `sysctl -n hw.memsize`
- GPU cores: `system_profiler SPDisplaysDataType`
- free disk: `df`
- MPS availability: `torch.backends.mps.is_available()`
- MLX availability: `import mlx.core as mx; mx.default_device()`

**Never hard-code core counts or memory anywhere in this build.**

### 2.2 Derive settings (`config/tuning.toml`)

| Setting | Rule |
|---------|------|
| `cpu_workers` | performance cores minus 2 (minimum 2) |
| `io_workers` | 16 for RCSB and AFDB downloads, with polite rate limits and `tenacity` retries |
| `model_device` | `mps` if the MLX smoke test passes, else `cpu` |
| `model_instances` | 1 resident model, never reloaded per job |
| `freesasa_workers`, `dssp_workers` | `cpu_workers` |
| `memory_headroom_gb` | 24: model plus workers must never exceed total memory minus headroom |
| `mlx_batch_size` | start at 4, halve on allocation failure, log the final value |

Environment for PyTorch jobs:

```bash
export PYTORCH_ENABLE_MPS_FALLBACK=1
export TOKENIZERS_PARALLELISM=false
export OMP_NUM_THREADS=<cpu_workers>
```

### 2.3 Concurrency

```
          ┌──── MLX queue (one resident model) ────┐
RCSB/AFDB ┤                                        ├─► CPU geometry pool ─► Parquet/DuckDB ─► SQLite
 catalogue└─ IO download pool ─► mmCIF prep pool ──┘
```

One long-lived MLX worker process, `ProcessPoolExecutor` for geometry. Communicate only through files and manifests: no shared memory, no queue service. The geometry pool polls manifests and processes new downloads immediately, so analysis finishes minutes after the last download rather than hours.

### 2.4 Budget

Phase 1.0 times a representative entry (download, parse, FreeSASA, contact analysis) and extrapolates. Order the queue in priority tiers so a partial run still yields the headline figures:

1. Entries referenced by the Section 9 validation datasets (curated glues, PROTAC-DB structures, BioLiP2 artefact exemplars)
2. Entries with two or more distinct polymer entities and at least one non-polymer entity over 150 Da
3. Everything else with a non-polymer entity
4. Single-chain entries (needed only for the negative class of the triage corpus)

Within a tier, shortest first. If the projection exceeds `MAX_COMPUTE_HOURS`, reduce tier 4 sampling first, then tier 3, and only then open G1.

---

## Section 3: Environment

Two environments, matching the GOBSMACKED and KINFOLK split.

### 3.1 Compute: pixi (`pixi.toml`, `osx-arm64`)

| Package | Use | Fallback |
|---|---|---|
| `python 3.11` | base | 3.12 |
| `gemmi` | mmCIF parsing, assembly generation, neighbour search | `biotite` |
| `freesasa` | solvent accessible surface, ΔSASA | `biotite.structure.sasa` |
| `biotite` | structure handling, superposition | Biopython |
| `dssp` (`mkdssp`) | secondary structure for hairpin detection | `pydssp` (pure Python, MPS-friendly) |
| `rdkit` | ligand properties, SMILES canonicalisation, MW and heavy-atom counts | OpenBabel |
| `fpocket` | pocket detection on ligase structures | P2Rank (Java) |
| `openbabel` | CIF to PDB conversion in the PLIP path | `gemmi convert` |
| `plip` | interaction typing at the bridging interface | PLIP via pip |
| `duckdb`, `pyarrow` | analytical store | pandas + Parquet |
| `tenacity`, `httpx` | polite retried IO | `requests` + manual backoff |
| `mlx`, `mlx-lm` | the fine-tune (pip into the pixi env if conda-forge lags) | pip install |

**Known trap, carried over from Marc's `cif_to_plip.py` work:** `pdb_tidy` introduces CONECT serial gaps that corrupt OpenBabel bond perception. Reuse `cif_to_plip.py` from the vibe-coding portfolio verbatim where possible; if reimplementing, do not run `pdb_tidy` between `gemmi convert` and OpenBabel, and assert that CONECT serials are contiguous before handing a file to PLIP.

### 3.2 App: uv (`pyproject.toml`)

Flask, Jinja2, gunicorn, `httpx`. No React, Vue, npm or webpack. Vanilla JS with D3 v7 and Mol* vendored and pinned under `app/static/vendor/`.

### 3.3 Vendored front-end libraries (pinned, downloaded in Phase 1.0)

| Library | Path | Use |
|---|---|---|
| Mol* (`molstar.js` + `molstar.css`) | `app/static/vendor/molstar/` | every structure viewer |
| D3 v7 | `app/static/vendor/d3/` | lens graph, ternary triangle |
| Plotly 2.35.2 | `app/static/vendor/plotly/` | distributions, scatter |
| Tabulator 6.3.1 | `app/static/vendor/tabulator/` | the ledger table |

Vendor them. Do not rely on a CDN at serve time: the droplet should work with no outbound requests.

---

## Section 4: Data Acquisition

### 4.1 Sources

| Source | Endpoint | What for |
|---|---|---|
| RCSB Search API | `search.rcsb.org` | entry discovery by entity counts, ligand presence, organism |
| RCSB Data API | `data.rcsb.org` | entry, entity, assembly and ligand metadata |
| RCSB file service | `files.rcsb.org` | mmCIF (`.cif.gz`), biological assemblies |
| PDBe | `ebi.ac.uk/pdbe/api` | ligand chemistry cross-check, validation summaries |
| PDB CCD | chemical component dictionary | ligand classification, formula, parent |
| AlphaFold DB | `alphafold.ebi.ac.uk` | human predicted proteome for the degron scan |
| UniProt | `rest.uniprot.org` | accession mapping, sequence, features, keywords |
| Open Targets | GraphQL API | ligase and target expression, tractability, disease association |
| InterPro / Pfam | `ebi.ac.uk/interpro/api` | ligase family assignment, domain boundaries |
| Europe PMC | `ebi.ac.uk/europepmc/webservices/rest` | abstracts for the triage corpus (Task B) |

Cache every response to `data/cache/<source>/` keyed by request hash. Never re-fetch a cached response unless `--refresh` is passed.

### 4.1b Validation datasets (acquired in Phase 1.0, before any science runs)

These are the external ground truth. Fetch them first, parse them into `data/validation/`, and fail loudly if a parse produces an implausible row count: a silently empty validation set is worse than no validation set.

| Dataset | What it provides | Use |
|---|---|---|
| **BioLiP2** (Zhang group; NAR 2024, D404) | Ligand-protein interactions with ligands flagged as biologically relevant or as crystallisation artefacts | The negative control for the Glue Atlas: BINMAN must classify BioLiP2's artefact ligands as furniture, not as glues |
| **ProtCID** (Dunbrack lab) | Common protein interfaces across crystal forms, distinguishing biological interfaces from crystal packing | Second negative source: a bridging ligand sitting in a ProtCID packing-only interface is not a glue |
| **MGDB** (NAR 2026, D1488) | Curated molecular glues | Glue Atlas recall, set 1 of 3 |
| **MolGlueDB** (NAR 2025, gkaf811) | Curated molecular glues, independent curation | Glue Atlas recall, set 2 of 3 |
| **MGTbind** (NAR 2026, D1500) | Molecular glue ternary interactome | Glue Atlas recall, set 3 of 3; also ternary partner assignments |
| **PROTAC-DB 3.0** (NAR 2025, D1510; Zenodo mirror) | Curated PROTACs | The confusable negative class for LM Task B, and an exclusion set for the Glue Atlas (a PROTAC is bivalent by design, not a glue) |
| **DEGRONOPEDIA** | Degron instances and degron-adjacent features across the proteome | Degron Scan cross-reference |
| **Zinc-finger degradation screens** (Mol Cell 2025, "Expanding the druggable zinc-finger proteome"; Nat Commun 2025, "Unbiased mapping of cereblon neosubstrate landscape") | Zinc fingers scored as degraded or not degraded under IMiD treatment | Degron Scan: the matched positive **and** negative sets, from the same experiment |
| **UbiBrowser** | Human E3-substrate interaction network, literature-curated plus predicted | E3 Triage: substrate counts and the enrichment test |
| **diGly ubiquitylation site data** (PhosphoSitePlus; ProteomeXchange diGly datasets) | Experimentally observed ubiquitylated lysines, proteome-wide | Degradability: calibration and validation of the reach window, with unused surface lysines on the same proteins as the negative set |

**Acquisition rules.** Record for each dataset: URL, version or release date, retrieval timestamp, row count after parsing, and licence. Write all of it to `data/validation/MANIFEST.md`. Where a licence forbids redistribution, keep the parsed derivative local and ship only the computed metrics to the droplet: never bundle a third-party dataset into the atlas. If a dataset cannot be obtained, open G7 and carry on with the rest. **Under no circumstances substitute a hand-written control for a missing published one** (spec 1.0 did that and it is exactly what this revision removes).

**Version pinning.** These databases are actively updated. Pin the release actually used, record it in `FINDINGS.md` beside every number derived from it, and never silently re-fetch a newer release mid-build.

### 4.2 Units of analysis

- **Glue Atlas:** one row per (entry, non-polymer entity instance, chain pair). A ligand bridging three chains yields three rows plus a summary row.
- **Degron Scan:** one row per (UniProt accession, candidate hairpin).
- **E3 Triage:** one row per ligase (UniProt accession).
- **Degradability:** one row per (UniProt accession, lysine, site definition).

### 4.3 Exclusion and classification policy

Do **not** delete crystallisation additives: classify them. A deleted row cannot train the triage model and cannot be audited. Maintain `data/reference/ccd_classes.tsv` with every CCD code seen, assigned to one of:

`glue_candidate` | `cofactor` | `metal` | `cryoprotectant` | `buffer` | `detergent` | `lipid` | `sugar` | `peptide_like` | `covalent_modifier` | `unknown`

Seed the additive classes from the standard cryo and buffer lists (PEG oligomers, glycerol, ethylene glycol, MPD, sulfate, phosphate, acetate, Tris, HEPES, MES, DMSO, imidazole, citrate, tartrate, formate, chloride and the rest), then let the pipeline add `unknown` codes for later review. Report counts per class in `FINDINGS.md`.

---

## Section 5: Methods and Metrics

Exact definitions. Every threshold here is a named constant in `config/thresholds.toml`, not a literal in the code.

### 5.1 Bridging ligand detection (G-1)

A non-polymer entity instance *L* in a biological assembly is a **bridging ligand** against polymer chains *A* and *B* when all of:

1. ΔSASA buried against *A* ≥ **25 Å²** and against *B* ≥ **25 Å²**, where ΔSASA(X) = SASA(L alone) + SASA(X alone) − SASA(L + X), computed with FreeSASA on the assembly, probe radius 1.4 Å, default Lee-Richards.
2. At least **3 heavy-atom contacts** under **4.0 Å** to each of *A* and *B*.
3. *A* and *B* are distinct polymer entity instances in the same biological assembly (assembly 1 by default). Chains related by crystallographic symmetry are included but flagged `symmetry_mediated = true` and excluded from headline counts.
4. Ligand heavy-atom count ≥ **10** (roughly MW ≥ 150 Da) unless the CCD class is `glue_candidate` by prior assignment.

Derived fields per row: total ΔSASA, the ΔSASA split across chains, buried fraction of the ligand, interface residue lists for both chains, PLIP interaction types at each half-interface, and a **bridging balance** = min(ΔSASA_A, ΔSASA_B) / max(ΔSASA_A, ΔSASA_B). A balance near 1.0 is the signature of a genuine glue; a balance near 0 is a ligand bound to one chain that happens to graze another.

**Cooperativity (α) is not computable from a structure.** Leave `alpha` null unless it is extracted from the literature by Task B, and in that case store the source identifier alongside it. Never estimate it. The demo values in the earlier concept artifact were illustrative placeholders and must not be carried into the database.

### 5.2 Structural degron scan (G-2)

Over the human AlphaFold proteome:

1. Run DSSP. Find β-hairpins: two antiparallel strands of ≥ 3 residues connected by a turn of ≤ **5** residues.
2. Identify the **tip position**: the residue at the apex of the turn, defined as the residue with the greatest Cα distance from the strand-pair centroid.
3. Candidate degron when the tip or tip±1 is **glycine**, tip-region mean pLDDT ≥ **70**, and relative SASA of the tip residue ≥ **0.40** (FreeSASA, Tien et al. maximum accessibility reference).
4. Score by a composite of pLDDT, exposure and hairpin regularity. Record the rank, never a probability: this is a geometric filter, not a calibrated classifier, and the field name must say so (`degron_geometry_score`).
5. Validate against the zinc-finger degradation screens (Section 9.2), which supply a matched positive set (zinc fingers degraded under IMiD treatment) and negative set (zinc fingers assayed in the same experiment and not degraded). Report sensitivity, specificity and the full contingency table in `FINDINGS.md`. The matched negative set is the point: recall alone is meaningless for a geometric filter that could fire on every hairpin in the proteome.

Generalise the same machinery to a `motif_family` column so DCAF-family and other degron geometries can be added later without a schema change.

### 5.3 E3 ligase triage (G-3)

Assemble the human E3 repertoire from InterPro domain signatures (RING, HECT, RBR, Cullin-RING adaptors: F-box, DCAF, SOCS, BTB) cross-checked against UniProt keyword annotation. For each:

| Field | Method |
|---|---|
| `family` | InterPro signature, with the CRL subfamily where applicable |
| `pdb_entries` | count of RCSB entries mapping to the accession |
| `best_structure` | highest resolution X-ray entry, else the AFDB model |
| `pocket_score` | fpocket top-pocket druggability score on `best_structure`; P2Rank fallback |
| `pocket_volume_a3` | fpocket volume, Å³ |
| `has_ligand` | any `glue_candidate` or drug-like CCD bound in any entry |
| `expression_breadth` | Open Targets baseline expression, summarised as tissue count above threshold |
| `tumour_enriched` | boolean from Open Targets expression comparison |
| `substrate_count` | known substrates from UniProt and literature extraction |
| `exploitation_status` | derived: clinically validated, chemically validated, covalent handle only, ligandable unproven, orphan |

Rank by a transparent weighted sum with the weights in `config/thresholds.toml` and every component column visible in the UI. No hidden scoring.

### 5.4 Degradability scoring (G-4)

Given a target structure and a site definition (a bound ligand, a pocket, or user-selected residues):

1. Site centroid = mean position of site-defining heavy atoms.
2. For every lysine: NZ relative SASA (FreeSASA), Cβ–Cβ distance from the nearest site residue, and the straight-line distance from NZ to the site centroid.
3. **Reach verdict.** The window is **learned from data, not assumed.** Map observed diGly ubiquitylation sites (Section 9.4) onto structures, and for every mapped protein label each surface lysine as *used* (an observed ubiquitylation site) or *unused* (a surface lysine on the same protein with no reported site). Fit the window on a training split of proteins and evaluate on a held-out split of proteins, never a held-out split of lysines from the same protein: lysines within one protein are not independent.
4. Write the fitted boundaries into `config/thresholds.toml` with the fitting date, the dataset version and the held-out AUC recorded beside them. The values in spec 1.0 (relative SASA ≥ 0.35, Cβ–Cβ 5 to 18 Å favourable, 18 to 24 Å marginal) are a **starting point for the optimiser only**. They have no empirical standing and must not survive into the shipped config unless the fit independently lands on them.
5. Report counts per verdict plus the single best lysine, and show the held-out AUC in the UI beside the verdict column so the user knows how much weight it carries. Never report an aggregate "degradability score" without the component table beside it.

**Honest limits of this metric**, to be stated in the UI and in `FINDINGS.md`: observed ubiquitylation sites come from native E3 biology, not from induced ternary complexes, so the window is a proxy. Absence of a reported site is weak evidence of a lysine being unusable (detection is incomplete and condition-dependent), which biases the negative set. Report the AUC as a measure of enrichment, not as a probability of degradability.

---

## Section 6: App

### 6.1 Architecture

```
app/
  __init__.py        Flask factory
  routes/            one blueprint per module
  queries.py         the query object parser and executor (deterministic, no LLM)
  lm.py              optional BINMAN-LM client, feature-flagged
  templates/
  static/
    vendor/          Mol*, D3, Plotly, Tabulator (pinned)
    css/binman.css   the design system below
    js/              ledger.js, triangle.js, lens.js, molstar-bridge.js
```

Read-only SQLite at serve time. No folding, no FreeSASA, no fpocket at request time: the droplet serves a precomputed atlas and nothing else.

### 6.2 Design system: "Depot"

Deliberately differentiated from the marcdeller.com house brand, from GOBSMACKED's instrument panel and from KINFOLK's field guide. **The house header and `#1e73be` palette do not apply to this app UI.** They still apply to the README. The direction is municipal waste-depot signage: a concrete ground, stencilled headings, sodium-amber wayfinding, one accent and everything else quiet.

```css
:root{
  --bg:#E9EAE5;        /* concrete */
  --surface:#F7F7F4;
  --surface-2:#DFE1DA;
  --ink:#15171A;
  --muted:#6A6F68;
  --line:#C9CBC3;
  --accent:#D65B0A;    /* sodium amber */
  --accent-soft:#F6E3D3;
  --good:#2C6D60;
  --warn:#9A7B10;
  --bad:#A33A2A;
  --display:'Archivo', 'Helvetica Neue', Arial, sans-serif;
  --body:'Spline Sans', system-ui, -apple-system, sans-serif;
  --data:'IBM Plex Mono', ui-monospace, Menlo, monospace;
}
```

Dark theme: `--bg:#131512; --surface:#1C1F1B; --surface-2:#252923; --ink:#E7E9E2; --muted:#8D938A; --line:#2F342D; --accent:#FF8A33; --accent-soft:#3A2415; --good:#5CBCA3; --warn:#D4AC3A; --bad:#E07A62;` with `color-scheme: dark`. Define every token on bare `:root` first, redefine under `@media (prefers-color-scheme: dark)` and under `[data-theme="dark"]`. Self-host the three fonts under `app/static/vendor/fonts/` with real fallback stacks.

### 6.3 Navigation: three idioms, one shared selection

The selection state is a single object `{glue, e3, target, site}` held in one place and shared by every module and every viewer. Changing it anywhere updates everything.

**Primary layout: Split Ledger.** A narrow left rail holds the four modules. Beneath it, an accumulating **query stack** renders every active filter as a readable line. Switching module re-runs the whole stack against the new record type rather than resetting it. The right pane is a dense Tabulator table. The query stack has a copy button and is the app's audit trail: it should paste cleanly into a methods section.

**Header glyph: Ternary Triangle.** A small persistent SVG in the app header, three corners (glue, ligase, target) plus a centre. Corners fill as they are pinned; edges light when a real structural link exists between the pinned pair; the centre resolves a degradability readout only when all three are pinned. It is also a control: clicking a corner jumps to that module. This is the answer to "what am I currently looking at" and it is always visible.

**Secondary view: Lens Graph.** A full-page D3 force-directed E3-to-substrate network, reachable from any module, where the four modules act as lenses that recolour the same graph and change the side panel. Clicking a node sets the shared selection. Prune aggressively: default to the pinned ligase's neighbourhood at depth 2, with an explicit "expand" control, and never render more than 400 nodes without the user asking.

### 6.4 Mol* viewers (required on every module)

One shared wrapper, `static/js/molstar-bridge.js`, exposing `mountViewer(el, spec)` and `applySelection(viewer, selection)`. Every viewer is a real Mol* instance, not an image. Structures are served gzipped from `app/static/structures/` as trimmed mmCIF: the biological assembly reduced to the chains of interest plus everything within 8 Å, and representatives only.

| Module | Viewer content | Required presentation |
|---|---|---|
| **Glue Atlas** | The ternary complex | Two polymer chains in distinct cartoon colours, bridging ligand as ball-and-stick, interface residues on both chains shown as sticks and coloured by which chain they belong to, buried surface shown as a semi-transparent molecular surface clipped to the interface, PLIP interactions as dashed measurement lines with labels |
| **Glue Atlas (compare)** | Two ternaries side by side | Linked cameras, superposed on the ligase chain, a toggle to superpose on the ligand instead. This is how you see whether two glues present the same face |
| **Degron Scan** | The AFDB model | Cartoon coloured by pLDDT on the standard AlphaFold four-band scale, candidate hairpin highlighted, tip glycine as spheres, a one-click zoom to the hairpin |
| **E3 Triage** | The ligase | Best structure, top fpocket pocket rendered as a mesh or surface, any bound `glue_candidate` ligand shown, pocket volume and score in an overlay label |
| **Degradability** | The target | Surface representation, every lysine NZ as a sphere coloured by verdict (`good` / `warn` / `bad` tokens), site centroid marked, a measurement line from the selected lysine to the centroid showing the distance in Å, and a table row that highlights on hover in both directions |
| **Lens Graph** | On node click | A compact viewer in the side panel showing that node's representative structure |

Viewer requirements that apply everywhere: a reset-camera control, a representation toggle (cartoon, surface, ball-and-stick), a label toggle, a spin toggle, the PDB or AFDB identifier shown and linked out, and a graceful empty state that says what to pin rather than showing a black box. The viewer must respond to the shared selection without a page reload.

### 6.5 Performance targets

| Target | Budget |
|---|---|
| First contentful paint, ledger page | < 1.2 s on the droplet |
| Query stack re-run, 10k-row table | < 300 ms |
| Mol* first structure interactive | < 2.5 s |
| Lens graph, 400 nodes, settled | < 3 s |
| Total data bundle shipped to the droplet | ≤ 2.5 GB |
| Per-entity JSON | ≤ 150 KB |
| About tab, schematic interactive | < 1.5 s |

### 6.6 About tab

A fifth destination alongside the four analysis modules, reachable from the header on every page, in the same Depot design system.

**Governing rule: the About tab is generated, never authored.** Every number, version, citation and count on it is read at build time from artefacts the pipeline already produces (`data/validation/MANIFEST.md`, `references.bib`, `data/validation/results.json`, `config/thresholds.toml`, `config/tuning.toml`, `data/manifests/*.jsonl`) and written to `app/static/about.json` by `pipeline/build_about.py`. A hand-written About page is wrong within one build and nobody notices. If a value cannot be read from an artefact, the page shows "not recorded" rather than a plausible-looking guess, and the build logs it.

#### 6.6.1 Workflow schematic

An inline SVG, drawn by `pipeline/build_about.py` from the stage manifests so the figure cannot drift from the pipeline. Shows the four stages (acquisition, geometry, scan and triage, model) as columns, with the data sources entering on the left and the four modules leaving on the right.

- Every node carries its **real counts** from the manifests: entries processed, bridges found, degrons scanned, ligases triaged, items failed. A node with failures shows the failure count in the `--bad` token, not hidden.
- Every node names the **software that does that step** and links to its row in the reference table (6.6.3).
- Clicking a node opens a short panel: what the step does, its thresholds pulled live from `config/thresholds.toml`, and its acceptance criteria from Section 9.
- The validation datasets appear as a distinct input shape, visually separated from the primary data sources, so a reader can see at a glance what is evidence and what is ground truth.
- Theme-aware: both palettes, text coloured from tokens, nothing legible in only one theme. Provide a plain-text structural description for screen readers rather than relying on the SVG alone.

#### 6.6.2 Model card for BINMAN-LM

Rendered from `data/validation/results.json` and the training config. Nothing on this panel is typed by hand.

| Section | Content |
|---|---|
| Identity | Base model and exact revision, quantisation, adapter rank and layer count, fused or adapter-only, build date |
| Training | Corpus composition per task with counts, the seven corruption modes with counts, stage 1 and stage 2 hyperparameters, iterations run, early-stopping point, wall-clock time, and the hardware it ran on from `config/hardware.toml` |
| What it does | The three tasks in plain language, with one real input and output example each, taken from the held-out set |
| Results | Every Section 9.5 metric: parse rate, set equality on both the synthetic and the external query sets with the gap between them stated, Task B macro-F1 with the confusion matrix rendered as a heatmap, per-corruption-mode win rates as a bar chart, Task C fabrication rate |
| Baseline | The step 3.0 zero-shot baseline beside the fine-tuned number, so the reader sees what the fine-tune actually contributed. If the baseline won and no fine-tune shipped, say that plainly |
| Limits | Stated prominently, not in a footnote: the model never computes, estimates or reports a numeric value; all numbers in BINMAN come from deterministic Python. Also the closed vocabulary, the training cutoff of the underlying databases, and the register-mismatch gap measured in 9.5 |
| Availability | Whether the LM endpoint is live for this deployment, and that the app is fully functional without it |

#### 6.6.3 Reference table

One sortable, filterable Tabulator table covering every database, model, dataset and piece of software the build touched. Generated by joining `references.bib` (Crossref-verified, spec 12.3) with `data/validation/MANIFEST.md`.

Columns: **Name · Type** (database, dataset, model, software) · **Version or release** · **Retrieved** · **Used for** (which module, linked) · **Licence** · **DOI** (resolver link) · **Home page** · **Repository**.

Rules: a row Crossref could not verify is marked `unverified` in that column and is never silently dropped. A row with no DOI shows the canonical URL instead and says so. Licence is a required field: if it could not be determined, the cell reads "not determined" and the build logs it, because this is the table someone will read before reusing the atlas. Add a BibTeX export button and a "how to cite BINMAN" block giving the project's own citation plus the instruction to cite the underlying resources separately.

#### 6.6.4 Worked example

One record carried end to end through all four modules, so a first-time visitor understands what BINMAN does without pinning anything themselves.

**Selection is deterministic and automatic, never hardcoded.** `pipeline/build_about.py` picks the highest-scoring record satisfying all of: present in at least two of the three curated glue databases; passes the bridging filter with balance > 0.5; its substrate has a degron found by the Phase 2 scan; its ligase has a pocket score; its target has mapped lysines with at least one `favourable` verdict. Among the candidates, take the highest-resolution structure. Record the choice and the full candidate list in `DECISIONS.md`. If no record satisfies every criterion, relax the conditions in the documented order (resolution, then two-database agreement, then balance), log which were relaxed, and display on the page which criteria the example meets. A worked example that quietly stops being true is worse than none.

The example runs as four short steps down the page, each with its real numbers and a live Mol* viewer using the shared wrapper from 6.4:

1. **Found in the atlas.** The ternary complex viewer. ΔSASA split across both chains, bridging balance, PLIP interaction types. One sentence on why this passes the bridging filter and a PEG oligomer does not.
2. **Its substrate carries a degron.** AFDB model coloured by pLDDT, hairpin highlighted, tip glycine as spheres. The geometry score and where it sits in the distribution.
3. **Its ligase in context.** Pocket mesh, pocket score and volume, triage rank, and the ligase's position in the ranked list.
4. **Is the target degradable?** Surface lysines coloured by verdict, measurement line from the best lysine to the site centroid with the distance in Å, and the held-out AUC stated beside the verdict so the reader knows the weight it carries.

Close with a **"try it yourself"** control that loads this record into the live selection and jumps to the Glue Atlas, so the example hands straight off into the real app. Each step is deep-linkable by URL fragment.

Add one honest paragraph below the example: this record was chosen because every stage worked on it, and a reader should look at the misses list and the novel-bridge set in `FINDINGS.md` for the cases where stages did not.

---

## Section 7: Data Model (SQLite)

Read-only at serve time. Index every foreign key and every column used in a filter.

```sql
CREATE TABLE entry (
  pdb_id TEXT PRIMARY KEY, title TEXT, method TEXT, resolution REAL,
  deposit_date TEXT, release_date TEXT, organism TEXT, assembly_id TEXT
);

CREATE TABLE ligand (
  ccd_id TEXT PRIMARY KEY, name TEXT, formula TEXT, mw REAL,
  heavy_atoms INTEGER, smiles TEXT, ccd_class TEXT, parent_ccd TEXT
);

CREATE TABLE polymer_entity (
  id INTEGER PRIMARY KEY, pdb_id TEXT, asym_id TEXT, auth_asym_id TEXT,
  uniprot_acc TEXT, name TEXT, organism TEXT, is_e3 INTEGER,
  FOREIGN KEY (pdb_id) REFERENCES entry(pdb_id)
);

CREATE TABLE bridge (                      -- the Glue Atlas, one row per chain pair
  id INTEGER PRIMARY KEY, pdb_id TEXT, ccd_id TEXT,
  entity_a INTEGER, entity_b INTEGER,
  dsasa_a REAL, dsasa_b REAL, dsasa_total REAL,
  bridging_balance REAL, buried_fraction REAL,
  contacts_a INTEGER, contacts_b INTEGER,
  symmetry_mediated INTEGER, evidence_class TEXT,   -- Task B label
  alpha REAL, alpha_source TEXT,                    -- null unless extracted
  interface_residues_a TEXT, interface_residues_b TEXT,  -- JSON
  plip_types_a TEXT, plip_types_b TEXT,             -- JSON
  structure_file TEXT, status TEXT
);

CREATE TABLE degron (
  id INTEGER PRIMARY KEY, uniprot_acc TEXT, afdb_id TEXT,
  start_res INTEGER, end_res INTEGER, tip_res INTEGER, tip_aa TEXT,
  turn_length INTEGER, mean_plddt REAL, tip_rel_sasa REAL,
  degron_geometry_score REAL, motif_family TEXT,
  is_known_neosubstrate INTEGER, structure_file TEXT, status TEXT
);

CREATE TABLE ligase (
  uniprot_acc TEXT PRIMARY KEY, gene TEXT, name TEXT, family TEXT, subfamily TEXT,
  pdb_entries INTEGER, best_structure TEXT, pocket_score REAL, pocket_volume_a3 REAL,
  has_ligand INTEGER, expression_breadth INTEGER, tumour_enriched INTEGER,
  substrate_count INTEGER, exploitation_status TEXT, triage_rank INTEGER, status TEXT
);

CREATE TABLE lysine (
  id INTEGER PRIMARY KEY, uniprot_acc TEXT, structure_id TEXT, site_id TEXT,
  res_num INTEGER, nz_rel_sasa REAL, cb_cb_distance REAL, nz_centroid_distance REAL,
  verdict TEXT, status TEXT
);

CREATE TABLE edge (                        -- the lens graph
  id INTEGER PRIMARY KEY, source_acc TEXT, target_acc TEXT,
  ccd_id TEXT, edge_type TEXT, evidence TEXT, pdb_id TEXT
);

CREATE TABLE provenance (                  -- every derived row traces back
  id INTEGER PRIMARY KEY, table_name TEXT, row_id INTEGER,
  source TEXT, retrieved_at TEXT, tool TEXT, tool_version TEXT, params TEXT
);
```

Every table carries `status`. A row that failed any stage stays in the table with `status = "failed:<reason>"` so the UI can show what was attempted and the counts always reconcile.

---

## Section 8: Phase Plan

Four phases. Each ends with a local `git commit`, a `PROGRESS.md` rewrite and the acceptance criteria below met or explicitly logged as degraded.

### Phase 1: Foundations and the Glue Atlas

**1.0 Setup.** `tools/hwprobe.py` writes `config/hardware.toml` and `config/tuning.toml`. Create pixi and uv environments. Vendor and pin Mol*, D3, Plotly, Tabulator and the three fonts. `git init`. Write `.claude/settings.json` and `CLAUDE.md` from the appendices. Smoke test: download one positive-control entry, run the full geometry path on it, time it, extrapolate the queue and write the projection to `BUILD_LOG.md`.

**1.1 Catalogue.** Query the RCSB Search API for all entries with ≥ 2 distinct polymer entities and ≥ 1 non-polymer entity. Write `data/manifests/catalogue.jsonl` with the priority tier per entry.

**1.2 Download and prepare.** Biological assemblies as mmCIF, cached and gzipped. Parse with gemmi.

**1.3 Geometry.** FreeSASA ΔSASA per ligand-chain pair, neighbour-search contacts, bridging balance. PLIP interaction typing at each half-interface via the `cif_to_plip.py` path, with the CONECT assertion from 3.1.

**1.4 Classification.** Build `ccd_classes.tsv`. Populate `entry`, `ligand`, `polymer_entity`, `bridge`.

**1.5 Trimmed structures.** Write per-bridge trimmed, gzipped mmCIF to `app/static/structures/`.

| Acceptance criteria |
|---|
| `config/hardware.toml` and `config/tuning.toml` exist; nothing hard-coded anywhere |
| All Section 4.1b validation datasets fetched, parsed and recorded in `data/validation/MANIFEST.md` with version, licence and row count; any failure logged at G7 |
| Section 9.1 run: recall ≥ 0.85, artefact precision ≥ 0.95, packing specificity ≥ 0.90, or G6 opened with the measured values |
| The misses list and the novel-bridge set both enumerated in `FINDINGS.md` |
| `bridge` table populated with ΔSASA, balance and PLIP types for at least tiers 1 to 3 |
| Crystallisation furniture classified rather than deleted; class counts in `FINDINGS.md` |
| Trimmed structures load in a standalone Mol* test page in under 2.5 s |
| Pipeline is resumable: kill it mid-run, restart, and it skips completed manifests |

### Phase 2: Degron Scan, E3 Triage and Degradability

**2.1** Download the human AFDB proteome. DSSP, hairpin detection, tip identification, exposure. Populate `degron`.

**2.2** Build the human E3 repertoire from InterPro and UniProt. fpocket or P2Rank on each best structure. Open Targets expression pull. Populate `ligase` with the transparent weighted rank.

**2.3** Lysine geometry for every target with a defined site. Calibrate the reach window against the positive-control ternaries as described in 5.4 and write the calibrated thresholds back to `config/thresholds.toml`. Populate `lysine`.

**2.4** Build the `edge` table for the lens graph from the bridge, degron and ligase tables.

**2.5** Write `FINDINGS.md` v1: class counts, degron recall against known neosubstrates, the ranked orphan-ligase shortlist, and the calibrated reach window with the evidence for it.

| Acceptance criteria |
|---|
| Section 9.2 run: sensitivity ≥ 0.70 **and** specificity ≥ 0.60 on the matched screen sets, with the contingency table and ROC in `FINDINGS.md`, or G6 |
| Section 9.3 run: enrichment p < 0.01 with `exploitation_status` and `has_ligand` held out of the weights, or G6 |
| Section 9.4 run: held-out AUC ≥ 0.65 on a protein-level split, or G6 |
| Every ligase row has either a pocket score or an explicit `status = "failed:<reason>"` |
| The reach window in `config/thresholds.toml` is **fitted**, with dataset version, fit date and held-out AUC recorded beside it; the spec 1.0 starting values do not survive unless the fit independently reproduces them |
| `edge` table non-empty and connected: the CRBN neighbourhood renders as a graph |
| `FINDINGS.md` states every number with its method and its n |

### Phase 3: BINMAN-LM

One Qwen model, three tasks, distinguished by a task tag in the system turn: `<task>query</task>`, `<task>triage</task>`, `<task>abstain</task>`.

**3.0 Baseline first.** Run the chosen base model zero-shot with the schema in the prompt against the held-out query set. **If it already reaches ≥ 0.85 set-equality, do not fine-tune for Task A**: ship grammar-constrained decoding instead, log the decision in `DECISIONS.md`, and spend the budget on Tasks B and C. This check is mandatory and must be run before any training.

**3.1 Base model.** `Qwen2.5-3B-Instruct` 4-bit via mlx-lm. Fallbacks in order: `Qwen2.5-1.5B-Instruct`, `Llama-3.2-3B-Instruct`. If the model is gated, open G2.

**3.2 Task A corpus: natural language to query object.** Generate, do not curate. Enumerate the real schema from Section 7: the filterable fields, six operators (`eq, ne, gt, gte, lt, lte`), the real value ranges, and the closed vocabularies (ligase accessions and gene names, CCD codes, families, verdict enums) read directly out of the built SQLite. Cross with ~40 phrasing templates, then paraphrase-expand. Every generated pair is validated by the same parser the app uses, so the corpus has zero label noise by construction. Target 4,000 training pairs, 500 validation, 500 test.

**3.3 Preference pairs.** For each chosen sample, generate exactly one rejected sample per corruption mode, tagged with the mode:

| Mode | Corruption | Teaches |
|---|---|---|
| `hallucinated_field` | swap a field for a plausible non-existent one | stay inside the schema |
| `operator_inversion` | `gt` becomes `lt` | above against below |
| `unit_confusion` | ΔSASA in Å rather than Å², distance in nm | domain units are not interchangeable |
| `dropped_constraint` | three clauses in, two out | completeness |
| `invented_entity` | a ligase not in the vocabulary | closed-world discipline |
| `wrong_question` | valid JSON, different intent | semantic fidelity |
| `prose_not_json` | a chatty explanation | format discipline |

Equal counts per mode. Target 1,400 preference pairs for Task A.

**3.4 Task B corpus: evidence-class triage.** Five classes: `molecular_glue`, `protac`, `bivalent_inhibitor`, `native_cofactor`, `crystallisation_artefact`. Inputs are entry title plus ligand list, or a Europe PMC abstract. Output is a single class token.

**Every label comes from a published curated source, never from this project's judgement:**

| Class | Label source |
|---|---|
| `molecular_glue` | MGDB, MolGlueDB, MGTbind: use the **intersection of at least two** for training labels |
| `protac` | PROTAC-DB 3.0 |
| `native_cofactor` | BioLiP2 biologically-relevant ligands in cofactor CCD classes |
| `crystallisation_artefact` | BioLiP2 artefact-flagged ligands |
| `bivalent_inhibitor` | Two sites within one chain from the pipeline's own geometry, cross-checked against the absence of any degrader annotation in all four databases above |

Where the three glue databases disagree about a record, hold it out of training and write it to `data/validation/glue_disagreements.tsv`. Disagreement between expert curators is not noise to be averaged away: it is a labelled hard set, and model behaviour on it belongs in `FINDINGS.md`.

Balance the classes by sampling, never by weighting. Target 3,000 training examples. Preference-stage negatives are the **confusable neighbour class**, not a random one: PROTAC against glue is the pair that matters, and bivalent inhibitor against glue is second.

**3.5 Task C corpus: structured abstention.** Inputs are partial triads and genuinely unanswerable questions. Chosen output is a structured refusal naming exactly what is missing. Rejected output is a confident fabrication: an invented ligase, an invented PDB ID, or a number. Target 800 pairs. This is the task that keeps the model honest and it is the one to over-weight if the budget is tight.

**3.6 Splits and the external query set.** Hold out **compositions, not tokens**: every field, operator and class appears in training; the test set holds out unseen combinations.

The synthetic test set shares a generator with the training set, so it cannot detect register mismatch (a model that only understands phrasing shaped like its own generator's). The defence is an **externally authored** query set, harvested rather than written:

1. Pull the full text of recent molecular-glue and degrader discovery reviews via Europe PMC.
2. Extract the research questions they pose: sentences in the introduction, outlook and figure captions that state something a researcher wants to find out ("which E3 ligases show tumour-restricted expression", "how many deposited ternary structures involve a non-IMiD chemotype").
3. Keep those that BINMAN's schema can actually answer. Target 12 to 15.
4. Normalise lightly (strip citation markers, resolve pronouns) and record the source DOI and the verbatim original sentence for every one.
5. Write the gold query object for each by hand against the schema and validate it with the parser.

Store as `data/validation/external_queries.jsonl` with fields `source_doi`, `original_sentence`, `normalised_query`, `gold_object`. This phrasing was written by working scientists in the field, by neither the generator nor the project. Report set-equality on it separately from the synthetic held-out set: a large gap between the two is the register-mismatch signal, and it is the number worth watching.

**3.7 Training.** Stage 1: LoRA SFT on positives only, all three tasks interleaved, rank 16, ~16 layers, lr 1e-5, batch from `tuning.toml`, 600 to 1200 iterations with early stopping on validation loss. Stage 2: preference tuning on the pairs, β 0.1, one short pass, starting from the stage 1 adapter. Use whichever preference trainer the installed mlx-lm provides; if it provides none, fall back to the mlx-examples DPO loop, and if that also fails, ship stage 1 alone and log it. Save adapters to `models/binman-lm/adapters/`, fuse to `models/binman-lm/fused/`.

**3.8 Evaluation.** Three numbers, reported per task and per corruption mode:

- **Parse rate.** Fraction of outputs that parse. If this is not ~1.0 after stage 1, stop and fix the corpus before touching stage 2.
- **Set equality.** Execute both the gold query and the predicted query against the real SQLite and compare the returned row sets. Two syntactically different queries that select the same rows are both correct. This is the primary metric for Task A.
- **Per-mode win rate.** For each corruption mode, how often the model prefers the correct form. A failing mode names the behaviour that did not take.

Task B: macro-F1 plus the full confusion matrix, with the glue-against-PROTAC cell called out. Task C: fabrication rate, which must be 0 on the held-out set.

Write `FINDINGS.md` section "BINMAN-LM" with all of it, including the baseline from 3.0 so the fine-tune's actual contribution is visible.

**3.9 Serving.** `mlx_lm.server` on the Studio behind a thin `app/lm.py` client. The droplet ships the deterministic parser and the query-builder UI; the LM endpoint is a feature flag (`BINMAN_LM_URL`). When it is unset or unreachable, the UI falls back to the manual query builder with no error and no degraded functionality beyond losing the natural-language box. Do not ship model weights to the droplet.

| Acceptance criteria |
|---|
| Baseline from 3.0 recorded before any training |
| Parse rate ≥ 0.99 on held-out Task A |
| Set equality ≥ 0.90 on the synthetic held-out set **and** ≥ 0.80 on `external_queries.jsonl`, reported separately; the gap between them is the register-mismatch signal and must be stated |
| Task B macro-F1 ≥ 0.85 with the full confusion matrix and the glue-against-PROTAC cell called out |
| Behaviour on `glue_disagreements.tsv` reported |
| Every corruption mode reported individually; no mode below 0.80 without a logged explanation |
| Task C fabrication rate = 0 on held-out |
| The app works fully with `BINMAN_LM_URL` unset |
| No numeric value anywhere in the app's output originates from the model |

### Phase 4: App, QC and delivery

**4.1** Build the Flask app: Depot design system, split ledger, header triangle, lens graph, all five Mol* viewers from 6.4, and the About tab from 6.6.

**4.1b** Write `pipeline/build_about.py`, which generates `app/static/about.json` and the workflow SVG from the manifests, `references.bib`, `data/validation/MANIFEST.md`, `data/validation/results.json` and the config files, and selects the worked-example record by the deterministic rule in 6.6.4. It runs as the last pipeline step before the atlas bundle, so the About tab always describes the build that shipped.

**4.2** Wire the shared selection object across every module and viewer. Deep-link each state to a plain URL fragment.

**4.3** Build the precomputed atlas bundle for the droplet: SQLite, trimmed gzipped structures, per-entity JSON, within the 2.5 GB budget.

**4.4** QC per Section 10.

**4.5** Icons, non-interactively: invoke `marcs-vibe-icon` for the blog mark (`binman_icon.svg`, `binman_icon_300.png`) and design an independent favicon (a different idea, not the blog mark minus its wordmark), generating the full set to both the project root and `app/static/`. Check it at 16px.

**4.6** README to house standard via `readme_forge.py`, using the site palette, not the app's Depot palette.

**4.7** Write `deploy/` (rsync script, gunicorn service, nginx config) but **do not execute it**. Open G3.

| Acceptance criteria |
|---|
| Playwright screenshots of every page at 1440×900 and 390×844, no console errors |
| axe-core: zero serious or critical violations |
| Every Mol* viewer loads, responds to the shared selection, and has a working empty state |
| About tab generated, not authored: assert that every displayed metric, version and count matches its source artefact, and that no value on the page is a literal in the template |
| Reference table covers every database, dataset, model and software package the build touched, with licence and DOI or canonical URL on every row |
| Worked example satisfies its selection criteria, all four viewers render, the "try it yourself" control loads the record into the live selection, and the relaxation log is accurate if any criterion was relaxed |
| Both themes pass: no colour defined only inside a media or `[data-theme]` block |
| Data bundle ≤ 2.5 GB; all performance targets in 6.5 met or logged |
| Both icons present, favicon legible at 16px, `apple-touch-icon.png` opaque |
| All commits local, nothing pushed, deploy script written but not run |
| `GATE_OPEN.md` states G3 |

---

## Section 9: Validation Against Published Datasets

Every module is judged against externally curated data. **No control in this section was written for this project**, and none may be. If a dataset is unavailable, open G7 and report the gap: do not fill it with a hand-written substitute.

All validation runs through `pipeline/validate.py`, which writes `data/validation/results.json` and the corresponding `FINDINGS.md` sections. It runs at the end of Phases 1, 2 and 3 and again in Phase 4 against the shipped atlas, so a regression between the pipeline and the serving bundle cannot hide.

### 9.1 Glue Atlas

**Positives:** the union of MGDB, MolGlueDB and MGTbind, mapped to PDB entries where the record carries a structure. **Negatives:** BioLiP2 ligands flagged as crystallisation artefacts, plus bridging ligands whose interface ProtCID classifies as crystal packing only, plus PROTAC-DB records (bivalent by design, so a correct pipeline does not call them glues).

| Metric | Definition | Floor |
|---|---|---|
| Recall | Fraction of curated glues with a structure that BINMAN's bridging filter recovers | 0.85 |
| Artefact precision | Fraction of BioLiP2 artefact ligands correctly classed as furniture rather than glue candidates | 0.95 |
| Packing specificity | Fraction of ProtCID packing-only interfaces not reported as glue interfaces | 0.90 |
| Three-way agreement | Overlap structure of the three glue databases, reported as a Venn with counts | reported, no floor |

**On circularity.** The curated glue databases are built partly from the same PDB entries BINMAN mines, so raw recall is partly self-fulfilling and is the *secondary* readout. The two primary readouts are the complements:

- **Misses:** curated glues with a deposited structure that BINMAN fails to recover. Each one is a sensitivity bug. Enumerate them individually in `FINDINGS.md` with the reason (which filter rejected it, and by how much).
- **Novel bridges:** bridging ligands passing every filter that appear in **none** of the three glue databases, are not in PROTAC-DB, and are not BioLiP2 artefacts. This set is the product. It is what the project name promises, and its size and composition are the headline result.

Report the artefact precision before the recall. A tool that finds every known glue and also calls PEG a glue is useless; the reverse is merely incomplete.

### 9.2 Degron Scan

**Positives and negatives come from the same experiments**, which is what makes this test meaningful: zinc fingers scored as degraded under IMiD treatment against zinc fingers assayed in the same screen and not degraded. Sources: the Molecular Cell 2025 druggable zinc-finger proteome study and the Nature Communications 2025 cereblon neosubstrate mapping. Cross-reference DEGRONOPEDIA for degron instances outside the zinc-finger class.

| Metric | Floor |
|---|---|
| Sensitivity on the degraded set | 0.70 |
| Specificity on the matched non-degraded set | 0.60 |
| Full contingency table and ROC over `degron_geometry_score` | reported |

Specificity is the metric that matters and the one spec 1.0 had no way to measure. A hairpin-plus-glycine filter will fire across the proteome; without the matched negative set there is no way to know whether it is selecting anything. If specificity is at chance, say so plainly in `FINDINGS.md` and present the module as a hypothesis generator rather than a classifier.

### 9.3 E3 Triage

**Reference:** the UbiBrowser human E3-substrate network. **Test:** validated and chemically-exploited ligases should be enriched at the top of BINMAN's ranking without the ranking having used that status as an input.

| Metric | Floor |
|---|---|
| Rank enrichment of clinically or chemically validated ligases (one-sided Mann-Whitney against the rest) | p < 0.01 |
| Substrate-count agreement with UbiBrowser (Spearman) | 0.5 |
| Coverage: ligases with a pocket score rather than a failure status | 0.80 |

Run the enrichment with `exploitation_status` and `has_ligand` **held out of the ranking weights**, otherwise the test is circular. Log the held-out weight configuration in `DECISIONS.md`.

### 9.4 Degradability

**Positives:** lysines with observed diGly ubiquitylation sites (PhosphoSitePlus and the ProteomeXchange diGly datasets), mapped onto structures. **Negatives:** surface lysines on the same proteins with no reported site.

| Metric | Floor |
|---|---|
| Held-out AUC of the reach window at separating used from unused lysines | 0.65 |
| Protein-level split honoured (no protein in both train and test) | assert in tests |
| Calibrated boundaries recorded with dataset version and fit date | assert in tests |

The negative set is biased: detection of ubiquitylation sites is incomplete and condition-dependent, so "no reported site" is weak evidence of unusability. State this in `FINDINGS.md` and in the UI. An AUC of 0.65 to 0.75 here is a genuine and useful result; anything above 0.9 should be treated as suspected leakage and investigated before it is believed.

### 9.5 BINMAN-LM

| Task | Validation set | Metric | Floor |
|---|---|---|---|
| A: query parsing | `external_queries.jsonl` (harvested from published reviews, spec 3.6) | Set equality against the real SQLite | 0.80, reported beside the synthetic held-out number |
| B: triage | Held-out records from the curated databases, stratified by class | Macro-F1, plus the full confusion matrix | 0.85 macro-F1; the glue-against-PROTAC cell reported explicitly |
| B: hard set | `glue_disagreements.tsv` (records the three glue databases disagree about) | Behaviour reported, no floor | reported |
| C: abstention | Held-out partial triads and unanswerable questions | Fabrication rate | 0.00 |

### 9.6 What a failure means

If a floor is missed: apply the fallback ladder, make **one** documented threshold adjustment within bounds recorded in `DECISIONS.md`, re-run. If it still misses, open G6 with the measured value, the dataset version and the specific records that failed. Do not quietly loosen a threshold until a metric passes: the adjustment history is part of the result and belongs in `FINDINGS.md`.

---

## Section 10: QC

**pytest** (`tests/`): geometry functions against hand-computed cases; the query parser against the full operator and field grid; the corruption generator (every mode produces a genuinely different and genuinely wrong output); the atlas bundle builder; schema integrity (no orphan foreign keys, every `status` value parseable).

**Playwright** (use the preinstalled Chromium, never `playwright install`): screenshots of every page at 1440×900 and 390×844, light and dark; zero console errors; Mol* reaches interactive state on every module; the shared selection propagates (pin a ligase in E3 Triage, assert the Glue Atlas table filters and the header triangle corner fills).

**axe-core:** zero serious or critical violations on every page.

**Science sanity:** `pipeline/validate.py` re-run against the **shipped atlas** (not the working database) and every Section 9 floor re-asserted as a test, so a regression introduced while building the serving bundle cannot hide. Protein-level split integrity asserted for 9.4. The number of bridges reported in the UI equals the number in the database. No `alpha` value present without an `alpha_source`. No validation dataset bundled into the atlas where its licence forbids redistribution.

**Model sanity:** a fixed probe set asserting BINMAN-LM never emits a numeral that is not copied from its input; abstention fires on every incomplete triad in the probe set.

**Performance:** the targets in 6.5, measured and logged.

---

## Section 11: Deliverables

| Deliverable | Path |
|---|---|
| Flask app | `app/` |
| Compute pipeline | `pipeline/` |
| Fine-tune corpus and training scripts | `lm/` |
| Model adapters and fused model | `models/binman-lm/` |
| SQLite atlas and trimmed structures | `data/atlas/`, `app/static/structures/` |
| `FINDINGS.md` | project root |
| README (house standard, site palette) | project root |
| Blog mark and favicon set | project root and `app/static/` |
| Deploy scripts (written, not run) | `deploy/` |
| `DECISIONS.md`, `BUILD_LOG.md`, `PROGRESS.md`, `GATE_OPEN.md` | project root |

---

## Section 12: Appendices

### 12.1 `.claude/settings.json`

```json
{
  "permissions": {
    "allow": [
      "Edit", "Write", "Read", "Glob", "Grep", "WebFetch", "WebSearch",
      "Bash(pixi:*)", "Bash(uv:*)", "Bash(python:*)", "Bash(python3:*)", "Bash(pytest:*)",
      "Bash(caffeinate:*)", "Bash(git init:*)", "Bash(git add:*)", "Bash(git commit:*)",
      "Bash(git status:*)", "Bash(git diff:*)", "Bash(git log:*)",
      "Bash(curl:*)", "Bash(wget:*)", "Bash(brew install:*)", "Bash(brew list:*)",
      "Bash(sysctl:*)", "Bash(system_profiler:*)", "Bash(df:*)", "Bash(osascript:*)",
      "Bash(tar:*)", "Bash(gzip:*)", "Bash(gunzip:*)", "Bash(mkdir:*)", "Bash(ls:*)",
      "Bash(mv:*)", "Bash(cp:*)", "Bash(gunicorn:*)", "Bash(flask:*)",
      "Bash(sqlite3:*)", "Bash(duckdb:*)", "Bash(npx playwright test:*)",
      "Bash(mkdssp:*)", "Bash(fpocket:*)", "Bash(java:*)", "Bash(obabel:*)",
      "Bash(freesasa:*)", "Bash(mlx_lm.lora:*)", "Bash(mlx_lm.server:*)",
      "Bash(mlx_lm.generate:*)", "Bash(mlx_lm.fuse:*)", "Bash(huggingface-cli:*)"
    ],
    "deny": [
      "Bash(git push:*)", "Bash(gh repo create:*)", "Bash(ssh:*)", "Bash(scp:*)",
      "Bash(rsync:*)", "Bash(sudo:*)", "Bash(rm -rf /:*)", "Bash(rm -rf ~:*)",
      "Bash(playwright install:*)"
    ]
  }
}
```

### 12.2 Project `CLAUDE.md`

```markdown
# BINMAN

This project is built from BINMAN_BUILD_SPEC.md, which is authoritative.

- Never stop except at a Gate (spec Section 0). Decide, log to DECISIONS.md, continue.
- Logging: BUILD_LOG.md (events), PROGRESS.md (phase checklist), DECISIONS.md (choices).
- Every stage writes data/manifests/<stage>.jsonl and is resumable and idempotent.
- Commit locally at the end of every phase. Never push (Gate G4).
- Hardware settings come from config/tuning.toml. Never hard-code cores or memory.
- Thresholds come from config/thresholds.toml. Never hard-code a cutoff in Python.
- UI design system: "Depot" (spec 6.2). The marcdeller.com house header and palette do
  NOT apply to this app UI. They do apply to the README.
- The language model never computes, estimates or reports a number. All numeric values
  are computed deterministically in Python.
- House style: British English, no em dashes (colons or parentheses), and none of:
  groundbreaking, revolutionary, paradigm-shifting, game-changing, cutting-edge,
  unprecedented, seamless, leverage (verb), delve.
```

### 12.3 References to verify at build time

Verify every one via Crossref before citing it in `FINDINGS.md` or the README. Do not cite from memory, and do not invent a DOI.

**Validation datasets (cite the version actually used):** BioLiP2; ProtCID; MGDB; MolGlueDB; MGTbind; PROTAC-DB 3.0; DEGRONOPEDIA; the Molecular Cell 2025 druggable zinc-finger proteome study; the Nature Communications 2025 cereblon neosubstrate mapping; UbiBrowser; PhosphoSitePlus and the ProteomeXchange diGly datasets used.

**Methods and background:** the original CRBN-IMiD neosubstrate degradation reports; the structural basis of the IMiD-induced CRBN-zinc-finger interface; DCAF15 with aryl sulfonamides and RBM39; the CDK-inhibitor-induced DDB1-cyclin K complex; the TIR1-auxin co-receptor structure; FKBP12-rapamycin-FRB; the glycine-degron rule for CRBN substrates.

**Software:** FreeSASA, DSSP, gemmi, RDKit, fpocket, P2Rank, PLIP, Mol*, AlphaFold DB, Open Targets, mlx-lm.

Record each as `title | authors | year | DOI` in `references.bib`. Mark anything Crossref cannot resolve as unverified rather than including it. For every dataset, also record the release identifier and retrieval date: a citation without a version is not reproducible for an actively updated database.

---

*End of spec.*
