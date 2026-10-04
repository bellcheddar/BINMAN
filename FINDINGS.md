# BINMAN findings

Every number here states its method and its n. Nothing is carried over from the
concept artifact, and no value is estimated.

> **Status: Phase 1 in progress.** Sections fill as their stage completes. A
> metric that cannot be computed because its validation dataset is unavailable
> is reported as "not computed" with the reason, never estimated (spec 4.1b).

---

## Method validation: the bridging filter against canonical glues

Before any catalogue run, the spec 5.1 bridging filter was run against six
structures named in spec 12.3 as methods and background references. This is a
smoke test of the geometry, not a Section 9 metric: these entries were chosen
by the spec's own reference list, not by an independent curator.

| Entry | Complex | Bridging ligand | dSASA A / B (Å²) | Balance | Buried fraction |
|---|---|---|---|---|---|
| 1FAP | FKBP12 + rapamycin + FRB | RAP | 897.5 / 787.6 | 0.878 | 0.87 |
| 5HXB | CRBN + DDB1 + CC-885 + GSPT1 | 85C | 528.5 / 684.9 | 0.772 | 0.95 |
| 6UML | CRBN + DDB1 + thalidomide + SALL4 | Y70 | 518.7 / 188.9 | 0.364 | 0.94 |
| 2P1Q | TIR1 + auxin + IAA7 | IAC | 450.6 / 146.4 | 0.325 | 0.99 |
| 6TD3 | DDB1 + CDK12 + cyclin K + CR8 | RC8 | 287.3 / 850.5 | 0.338 | 0.94 |
| 5HXD | DCAF15 (not the sulfonamide ternary) | none | — | — | — |

Five of the six recovered their bridging ligand. 5HXD is not a ternary glue
complex, so finding no bridge in it is the correct result rather than a miss.

Interface residues agree with the published descriptions: the filter places
rapamycin against Tyr26, Phe46, Trp59 and Tyr82 of FKBP12 and Trp2101, Phe2108
and Tyr2105 of FRB, without being told where to look.

### Finding: a genuine molecular glue is not symmetric

The spec describes a bridging balance near 1.0 as the signature of a genuine
glue. On this panel that holds only for the two glues whose ligand sits between
two comparably sized faces (1FAP, 0.878; 5HXB, 0.772). The three CRBN and
CUL4-family neosubstrate glues land at **0.33 to 0.36**, because the ligand is
buried deep in the ligase pocket and presents only a small face to the
neosubstrate. Buried fraction stays high (0.94 to 0.99) throughout, so the
ligand is enclosed; it is simply enclosed asymmetrically.

**Consequence for the build.** A balance floor above about 0.3 would reject real
IMiD neosubstrate glues, which is the exact class BINMAN exists to find.
`bridging.glue_balance_floor` is therefore held at 0.30 and treated as a
reporting split rather than an acceptance test, and
`bridging.glue_balance_strong` (0.50) is used only by the worked-example
selector, where spec 6.6.4 already allows documented relaxation. Balance is
reported as a column, never used to exclude a candidate.

---

## Section 9.1 Glue Atlas validation

### What the atlas contains

| Quantity | Count |
|---|---:|
| Bridges (entry, ligand instance, chain pair) | 57,758 |
| Entries carrying at least one bridge | 13,793 |
| Bridges whose ligand is a glue candidate | 13,601 |
| Bridges flagged symmetry mediated | 6,556 |

Crystallisation furniture is **classified, not deleted**, so the counts
reconcile. Chemical component classes across the 9,962 components
seen:

| Class | Count |
|---|---:|
| `glue_candidate` | 6,405 |
| `unknown` | 1,031 |
| `cofactor` | 805 |
| `buffer` | 579 |
| `lipid` | 347 |
| `peptide_like` | 227 |
| `detergent` | 206 |
| `cryoprotectant` | 182 |
| `sugar` | 99 |
| `metal` | 60 |
| `covalent_modifier` | 21 |

### Artefact precision: 0.9449 (floor 0.95)

**Reported before recall, as spec 9.1 instructs**: a tool that finds every known
glue and also calls PEG a glue is useless, while the reverse is merely
incomplete.

Measured over the 345 BioLiP2 artefact CCD codes present in the atlas,
326 of which are correctly not called glue candidates. On a
deterministic held-out half of the full 463-code list, used so the rules could
not be tuned on the number being reported, it measures **0.927**.

Replacing name matching with structural rules over SMILES lifted this from
**0.799 to 0.953** overall. No threshold was loosened.

**The floor is missed, and the reason matters more than the number.** BioLiP's
`ligand_list` is not pure furniture: its own curation code treats the file as a
list of *candidate* artefacts and checks each against the entry's PubMed abstract
before excluding it. The components BINMAN still calls drug-like include
nevirapine, IBMX, kainic acid and an antifolate. Reaching 0.95 would mean
deliberately misclassifying approved drugs as crystallisation furniture. Gate G6
carries the decision.

### Recall: 0.772 against a floor of 0.85, and the whole deficit is one criterion

All three curated glue databases resolved after the bulk routes were found, so
recall is measured rather than suppressed: **247 of 320** curated PDB entries
carry a glue-candidate bridge in the atlas. Spec 4.1b forbids substituting a
hand-written positive set and none was made.

The 73 misses were traced one by one, and they are not alike:

| Where it is lost | Entries | What it means |
|---|---|---|
| In the catalogue, geometry ran, **no bridge** | 46 | the sensitivity bug, below |
| Not in the catalogue | 20 | coverage, not sensitivity |
| Has bridges, none classed `glue_candidate` | 7 | classification: 4 cofactor, 2 detergent, 1 peptide-like |

**Every one of the 46 was rejected by the contact-count criterion, and not one
by ΔSASA.** `data/interim/halves.jsonl` records every half-interface the
pipeline considered, so each rejection can be read off directly. Of the ligand
instances in those entries that touched two chains at all, 48 were rejected;
48 of 48 failed only on contacts.

| Entry | Ligand | Weak-side ΔSASA | Contacts | Min distance |
|---|---|---|---|---|
| 3SML | FW1 | 145.3 Å² | 2 | 3.92 Å |
| 3P1O | FSC (fusicoccin) | 138.8 Å² | 2 | 3.96 Å |
| 8BWX | RZT | 133.9 Å² | 2 | 3.78 Å |
| 6HN2 | GF8 | 109.8 Å² | 2 | 3.44 Å |
| 3OGK | OGK (coronatine) | 87.4 Å² | 1 | 3.69 Å |

The weak side buries 55 to 145 Å², which is two to six times the 25 Å² floor,
at minimum distances of 3.2 to 4.0 Å. These are broad, shallow, long contacts:
the ligand lies against the second chain over a wide area without packing tight
against it. **That is what a glue stabilising a shallow protein-protein
interface looks like**, and the list is dominated by the 14-3-3 fusicoccin and
cotylenin family, the largest published glue class after the IMiDs. Spec 5.1
criterion 2 requires three heavy-atom contacts under 4.0 Å to *each* chain, and
it is that second gate, not ΔSASA, that excludes them.

### Loosening it does not rescue the floor, so the one permitted adjustment is not spent

Because `halves.jsonl` holds every half-interface, the criterion can be swept
exactly, without re-running the geometry:

| Contact floor | Recall | Total bridges | Verdict |
|---|---|---|---|
| 1 | 0.8469 | 337,347 | misses |
| 2 | 0.8219 | 280,239 | misses |
| **3** (spec) | **0.7719** | **239,485** | **misses** |
| 4 | 0.7125 | 211,684 | misses |
| 5 | 0.6594 | 188,013 | misses |

A floor of 1 is the loosest setting the criterion can take, and it still reaches
only 0.847 against a floor of 0.85, while inflating the bridge count by 41%.
Spec 9.6 allows one documented threshold adjustment before Gate G6. It is **not
spent here**, because the sweep shows it cannot make the metric pass: it would
buy 7.5 points of recall, still miss, and add 97,862 bridges whose
false-positive cost cannot be priced, since the packing-specificity metric that
would price it is the one ProtCID does not publish. Gate G6 carries the
decision (DECISIONS D-027).

The residual 20 not-in-catalogue entries and the 35 ligand instances that
contact only one chain are a different problem. The latter are largely
water-mediated: in the abscisic acid receptors (3KB3, 3JRQ, 3UJL) the hormone
sits in the PYL pocket and reaches the phosphatase through an ordered water,
so a direct-contact definition will never see it. BINMAN measures direct
contact and says so.

Packing specificity is also not computed: ProtCID does not publish bulk
interface data (DECISIONS D-023).

## Section 9.2 Degron Scan validation

| Metric | Measured | Floor | Verdict |
|---|---|---|---|
| Sensitivity on the degraded set | **0.656** (21/32) | 0.70 | **misses** |
| Specificity on the matched non-degraded set | **0.353** (1,932/5,476) | 0.60 | **misses** |
| ROC AUC over `degron_geometry_score` | **0.441** | — | below chance |

**The geometric degron filter has no specificity, and the honest reading is that
it is detecting the C2H2 fold rather than degradability.** Gate G6 is open
(DECISIONS D-024). The Degron Scan ships as a **hypothesis generator, not a
classifier**, which is what spec 9.2 instructs for exactly this case.

### The matched set

The screens spec 9.2 names (Molecular Cell 2025, Nature Communications 2025)
never resolved. Sievers et al. 2018 ([10.1126/science.aat0572](https://doi.org/10.1126/science.aat0572))
is the same experimental design (one flow-cytometry screen supplying both arms,
which is the entire point of the test) and its supplementary data are open.
Data files S2 and S6 are **pooled rather than intersected**, so each screen
contributes its own domains:

| Screen | Drugs | Domains | Statistic |
|---|---|---|---|
| S2 | thalidomide, lenalidomide, pomalidomide | 5,609 | t-test FDR |
| S6 | pomalidomide, CC-122, CC-220 | 3,206 | bootstrap FDR + fold change |
| pooled | all five | **5,663** | depleted in any, FDR < 0.05 |

**32 depleted, 5,631 assayed and not depleted.** 155 were excluded because their
protein never reached the AlphaFold scan, leaving 32 positives and 5,476 matched
negatives scored. A zinc finger counts as *called* when a degron candidate on
its AlphaFold model shares at least one residue with the assayed window.

| | filter calls it | filter does not |
|---|---|---|
| **depleted in the screen** | 21 | 11 |
| **assayed, not depleted** | **3,544** | 1,932 |

### The filter fires on 65% of the matched negatives

That is the result. It is not a threshold problem, and the sweep says so: every
attainable cut on `degron_geometry_score` was tested and **none clears both
floors together.** The best Youden's J over the whole curve is **0.022**.

| Cut | Sensitivity | Specificity |
|---|---|---|
| 0.000 (any candidate) | 0.656 | 0.353 |
| 0.703 | 0.375 | 0.513 |
| 0.717 | 0.281 | 0.594 |
| 0.721 | 0.250 | **0.621** |
| 0.735 | 0.125 | 0.702 |
| 0.776 | 0.000 | 0.892 |

To reach the 0.60 specificity floor the filter gives up all but a quarter of the
positives. Spec 9.6 allows one documented threshold adjustment before G6 and
D-010 already spent it: calibrated on the five documented degrons below, with
no matched negative set in existence at the time, which is precisely how a
filter with no specificity gets built. A second adjustment is not made: on this
curve it would be tuning against the test set for two points of J.

### Why: a C2H2 zinc finger *is* a short hairpin with an exposed turn

The AUC of 0.441 is the diagnostic. It is *below* chance (the score ranks
degraded zinc fingers marginally worse than non-degraded ones) while the
canonical IMiD neosubstrates are nonetheless recovered:

| Gene | Window | Score | Degraded by |
|---|---|---|---|
| IKZF3 | 146–168 | 0.697 | LEN, POM |
| E4F1 | 220–242 | 0.678 | CC-122, LEN, POM |
| ZFP91 | 400–422 | 0.662 | CC-122, POM, THAL |
| ZN517 | 452–474 | 0.736 | CC-122, CC-220, LEN, POM |
| ZN787 | 178–200 | 0.732 | CC-220, LEN, POM, THAL |

Twelve *non-degraded* zinc fingers score above IKZF3, E4F1 and ZFP91. Recovering
the textbook cases while ranking at chance is the signature of a filter keyed to
the domain family. The geometry spec 5.2 describes, a two-residue antiparallel
hairpin with an exposed glycine-bearing turn, is a description of C2H2 itself.
All 3,544 false positives carry the hairpin glycine, so requiring it harder
changes nothing.

Of the 11 misses, 9 have at least one degron candidate elsewhere on the same
protein (ZN526 has 7, ZN501 has 6): the filter fired, in the wrong place. Only
ZN292 1947–1973 has no candidate anywhere on its protein.

### The calibration history, which stands

What follows is the method sanity check that preceded the matched set. It
established that the filter can find the geometry it was built to find, and it
is **not** a substitute for the numbers above: the set is five proteins, it was
used to calibrate the thresholds, and it contains no negatives.

### The spec 5.2 thresholds, applied literally, recover no zinc-finger degron

Run as written, the filter found none of IKZF1, IKZF3, SALL4 or RBM39. The
diagnosis is specific and reproducible. In the AlphaFold model of IKZF1,
residues 145 and 146 form an extended strand that bridges antiparallel to 153
and 154 (DSSP bridge partners 145 to 154 and 146 to 153), with Gly151 in the
connecting turn at pLDDT 72. That is a textbook hairpin degron, and it failed
three thresholds at once:

| Criterion | Spec value | IKZF1 measures | Outcome |
|---|---|---|---|
| Strand length | ≥ 3 residues | 2 and 2 | rejected |
| Turn length | ≤ 5 residues | 6 | rejected |
| Tip relative SASA | ≥ 0.40 | 0.34 at Gly151 | rejected |

Measured across five documented CRBN and DCAF neosubstrate degrons:

| Gene | Degron Gly | pLDDT | Relative SASA | Strand A | Strand B | Turn |
|---|---|---|---|---|---|---|
| IKZF1 | 151 | 71.9 | 0.34 | 2 | 2 | 6 |
| IKZF3 | 155 | 86.4 | 0.15 | 2 | 1 | – |
| SALL4 | 416 | 85.5 | 0.44 | 2 | 2 | 6 |
| CSNK1A1 | 40 | 96.4 | 0.48 | 8 | 8 | 5 |
| RBM39 | 268 | 91.1 | 0.43 | 0 | 8 | – |

**The zinc-finger degron is a two-residue β-hairpin with a six-residue turn.**
The thresholds were calibrated to that measurement as the single adjustment spec
9.6 permits (DECISIONS D-010), and the tip definition was corrected to find the
glycine in the turn rather than the turn's geometric apex (DECISIONS D-011),
because on a six-residue turn those are two residues apart.

### Recovery after calibration

| Gene | Documented Gly | Found | Score | Relative SASA | pLDDT |
|---|---|---|---|---|---|
| IKZF1 | 151 | **Gly151** | 0.632 | 0.34 | 70.6 |
| SALL4 | 416 | **Gly416** | 0.725 | 0.44 | 85.3 |
| CSNK1A1 | 40 | **Gly40** | 0.718 | 0.48 | 96.7 |
| IKZF3 | 155 | miss | – | 0.15 | – |
| RBM39 | 268 | miss | – | – | – |

**3 of 5**, with both misses diagnosed rather than hidden:

- **IKZF3 Gly155** has relative SASA 0.15: its degron glycine is largely buried
  in the monomer model and becomes exposed only in the ternary complex. A floor
  low enough to catch it would fire across most of the proteome.
- **RBM39 Gly268** sits in a helix in the monomer model, with no hairpin at all.
  Its recruitment to DCAF15 involves an RRM surface rather than a hairpin
  degron, so a hairpin filter is the wrong instrument for it.

### What the calibration established, and what the screen then showed

The calibration established that the filter can find the geometry it is meant to
find, and that the spec's literal thresholds could not. It established nothing
about specificity, and the concern recorded at the time, that relaxing the
strand floor from 3 to 2 "admits far more hairpins proteome-wide, and the cost is
unmeasured", is now measured: the cost is 3,544 false positives on 5,476 matched
negatives. `calibration_validated = false` in `config/thresholds.toml` was the
right flag, and it stays set.

**What would make this a classifier.** Not a different cut on this score, but a
feature that separates degraded from non-degraded zinc fingers *within* the C2H2
family: degron sequence context, complementarity to the CRBN interface, or
Zn-coordination geometry. The matched set is now wired in as
`sievers_zf_screen`, so that test is one command away:
`pixi run python -m pipeline.validate --section 9.2`.

## Section 9.3 E3 Triage validation

| Metric | Measured | Floor | Verdict |
|---|---|---|---|
| Rank enrichment of validated ligases (one-sided Mann-Whitney) | **p = 0.002422** | p < 0.01 | **passes** |
| Ligases with a pocket score rather than a failure status | **0.9815** | 0.8 | **passes** |
| Substrate-count agreement with UbiBrowser (Spearman) | not computed | 0.5 | see below |

The enrichment compares 17 clinically or
chemically validated ligases against the other
633, with `exploitation_status` and `has_ligand`
**held out of the ranking weights**, so the test is not circular.

### The repertoire was wrong, and the validation is what found it

The enrichment first measured **p = 0.069** and failed. The cause was not the
threshold: the InterPro signature list had no DCAF entry, and **CRBN and VHL were
absent from the E3 repertoire entirely**, along with DCAF15 and DCAF16. The
"validated" group contained twelve chemically validated ligases and not one
clinically validated ligase, because both were missing.

Adding the CULT, VHL-box, DCAF15, DCAF16 and DCAF families (signatures read from
each protein's own UniProt cross-references, and UniProt's own name annotation
for the DCAF family, which has no distinguishing signature) took the repertoire
from 625 to 650 ligases and the enrichment to p = 0.0024.

Where the known degrader ligases now rank, with their status held out of the
score:

| Ligase | Family | Triage rank | Pocket score | Status |
|---|---|---:|---:|---|
| DCAF15 | DCAF15 | **1** | 0.988 | chemically validated |
| VHL | VHL-box | **5** | 0.693 | clinically validated |
| DCAF16 | DCAF16 | **6** | 0.921 | chemically validated |
| CRBN | CULT | **32** | 0.532 | clinically validated |
| KEAP1 | BTB | 85 | 0.219 | chemically validated |

### A tautology in the specified metric

Spec 9.3 asks for a Spearman correlation between the atlas's `substrate_count`
and UbiBrowser. The atlas column **is populated from UbiBrowser**, so the
correlation is 1 by construction and tests nothing. It is reported as not
computed, with that reason. A genuine version needs a second, independent
substrate source.

## Section 9.4 Degradability validation

| Metric | Measured | Floor | Verdict |
|---|---|---|---|
| Held-out AUC, accessibility only | **0.5458** | 0.65 | **misses** |
| Protein-level split honoured | yes, 135 of 403 proteins held out | required | satisfied |
| Reach window fitted | **no**, and deliberately not written back | | |

**Lysine exposure barely predicts whether a lysine is ubiquitylated.** Training
Youden's J is 0.09 and the held-out AUC is 0.55, which is a result about the
feature rather than a failure to fit it.

### Where the data came from

PhosphoSitePlus requires registration, PLMD is offline and dbPTM returns 403,
so spec 9.4 sat at not computed. The open route was in the project already:
UniProt records an observed ubiquitylation as a `CROSSLNK` feature reading
"Glycyl lysine isopeptide (Lys-Gly) (interchain with G-Cter in ubiquitin)" at
an exact residue, with an evidence code and a PubMed ID. That is the same
observation a diGly survey reports, curated, with provenance, under CC-BY-4.0.

**976 ubiquitylation sites on 404 reviewed human proteins**, 718 of them direct
experimental assertions (ECO:0000269) rather than large-scale combinatorial
ones. SUMO1, SUMO2, NEDD8 and ISG15 crosslinks share the feature type and are
excluded: 5,945 of them, which would all have been false positives. 403 of the
404 AlphaFold models were already cached from the degron scan, so no new
downloads were needed.

### What was fitted, and what was not

Only `min_nz_rel_sasa`. The three Cb-Cb reach boundaries describe distance from
a chosen ligand site, and an AlphaFold monomer carrying an observed
ubiquitylation site has no ligand site to measure from, so the data is silent
on them. They stay flagged unfitted rather than being blessed by a fit that
never touched them, and **no reach verdict is emitted**.

950 positive and 11,755 negative lysines, split so that a protein contributes
wholly to train or wholly to test. The threshold was chosen on the training
half alone by Youden's J, landing at 0.241, and evaluated on 338 held-out
observed sites.

**The fitted value was not written back.** Spec 5.4 says a starting value must
not survive into a shipped config unless the protein-level-split fit
independently lands on it. A fit scoring 0.55 has landed on nothing, and a
blessed threshold carrying that AUC would read as evidence it is not.
`fitted = false` stands, and `pipeline/degradability.py` now gates the
write-back on the floor rather than on the fit merely having run.

### What the negatives are worth

Less than 9.2's. UniProt lists sites that were *seen*; a lysine with no
annotation was not assayed and found unmodified. The negative set is therefore
an assumption, where the Sievers screen gave 9.2 a genuinely matched one.
PhosphoSitePlus would have had the same property, so this is a limit of the
question rather than of the route taken to it.

That caveat cuts both ways and is worth stating plainly: a biased negative set
would tend to *depress* measured performance, since unlabelled positives sit in
the negative pile. An AUC of 0.55 is low enough that the bias does not explain
it. Exposure is necessary for ubiquitylation and nothing like sufficient:
site selection is driven by E3 recruitment and sequence context, which is
exactly what the Degradability module does not yet model. Gate G6 carries it
(DECISIONS D-028).

## Section 9.5 BINMAN-LM

Measured against the **complete** atlas, with the corpus regenerated from it
(the ligase vocabulary went from 10 to 650 once the E3 stage finished).

### Task A: natural language to query object

| Metric | Baseline (zero-shot) | Fine-tuned | Floor | Verdict |
|---|---:|---:|---:|---|
| Parse rate, synthetic held out | 0.5133 | **0.9867** | 0.99 | misses by 2 of 150 |
| Set equality, synthetic held out | 0.3467 | **0.98** | 0.90 | **passes** |
| Exact match | 0.12 | 0.9333 | reported | — |
| Prompt tokens needed | 841 | **83** | — | — |
| Set equality, externally phrased | — | **not computed** | 0.80 | see below |

The two parse failures are both the model producing a filter the parser refuses:
one omitted a `value`, one used an `exploitation_status` outside the closed
vocabulary. Both are the parser doing its job.

### The register-mismatch finding, and why the specified metric could not be computed

Spec 3.6 calls for 12 to 15 query-set entries whose **phrasing was written by
working scientists**, harvested from published reviews, because the synthetic
test set shares a generator with the training set and so cannot detect a model
that only understands its own generator's register.

463 candidate sentences were harvested from open-access molecular-glue and
degrader reviews via Europe PMC. Of those, **18 are genuinely interrogative**
rather than declarative prose that happens to contain the word "which". Reading
those 18: **none asks a question BINMAN's schema can answer.** They ask about
linker composition in eTPD degraders, the architecture of attached ubiquitin
chains, whether IMiD treatment changes alternative splicing of CRBN, and whether
5-hydroxythalidomide mediates teratogenicity. Review articles pose mechanistic
questions, not database queries.

So the spec 9.5 external metric is reported as **not computed**. An earlier
revision did produce a number by pairing each hand-written gold query to
whichever harvested sentence shared three or more words, which produced pairs
where the sentence did not ask what the gold answered. That number measured
nothing and was removed.

**The signal itself is still visible, and it is severe.** Fifteen questions
written by hand against the schema, in ordinary prose rather than generator
phrasing, score:

| Set | Parse rate | Set equality |
|---|---:|---:|
| Synthetic held out (generator phrasing) | 0.9867 | **0.98** |
| Hand-written, same schema, ordinary phrasing | 0.1333 | **0.0667** |

A drop from 0.98 to 0.0667 is the register
mismatch spec 3.6 exists to catch. **BINMAN-LM is excellent on phrasing shaped
like its training generator and close to useless on anything else.** That is the
number worth watching, and it is why the natural-language box is a feature flag
rather than the primary interface: the app's manual query builder is
deterministic and always works.

### Task C: structured abstention

| Metric | Measured | Floor |
|---|---:|---:|
| Fabrication rate | **0.0** | 0.00 |
| Abstention rate | 0.0 | reported |

The fabrication floor passes: on 40 held-out partial triads and unanswerable
questions the model invented no numeral and no identifier that was not in its
input. But the abstention rate of 0.0 says it is not
abstaining either: it answers with a query object instead of a structured
refusal. The task is trained but not learned, and the honest reading is that
**Task C works as a fabrication guard and not as an abstention mechanism**.

### Task B: not built

Three of its five classes have no published label source in this build. Reported
rather than substituted. See the Gates section.

### Training

| Round | Stage | Outcome |
|---|---|---|
| `binman-qwen-2.5-3b-4bit-round01` | LoRA SFT on the partial atlas | superseded |
| `binman-qwen-2.5-3b-4bit-round02` | DPO, lr 1e-5, 600 steps | rejected: collapsed the model |
| `binman-qwen-2.5-3b-4bit-round03` | DPO, lr 5e-7, 150 steps | rejected: still degraded |
| `binman-qwen-2.5-3b-4bit-round04` | LoRA SFT on the complete atlas | **shipped** |

Round 04: rank 16, 16 layers, lr 1e-5, 1,200 iterations, 4,752 train and 574
valid examples, validation loss to 0.004, around 420 tokens/s, 6 GB peak on the
M2 Ultra. Tracked in Weights & Biases under `binman-lm`.

Both DPO rounds reached a near-zero loss by collapsing the policy rather than
learning the preference, and the per-mode win rates could not detect it: they
measured 0.95 to 1.00 on a model that emitted `ccdccdccd…` indefinitely, because
a degenerate policy trivially scores one string above another. A generation guard
now runs held-out test questions through any candidate adapter and requires 80%
to produce a parseable query object before it may ship. Stage 1 scores 10 of 10;
the DPO adapters scored 6 of 10 and 0 of 10 and were refused.

**The spec 3.8 per-corruption-mode win rates are therefore not meaningfully
reported.** The only numbers produced came from a collapsed model.

BINMAN-LM serves as base model plus adapter: fusing against the 4-bit base
produced a model that parsed 0 of 10 held-out questions and invented its own
output schema, so that artefact was deleted rather than shipped.
