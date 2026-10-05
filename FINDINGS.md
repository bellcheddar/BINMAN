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
| 5HXD | DCAF15 (not the sulfonamide ternary) | none | n/a | n/a | n/a |

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
| ROC AUC over `degron_geometry_score` | **0.441** | n/a | below chance |

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

### Testing D-024's reversal condition: sequence beats geometry, and still fails

D-024 named what would make this a classifier: a feature that discriminates
**within** the C2H2 family, since the geometry describes the family itself.
That was tested rather than left as a suggestion.

Every assayed zinc finger was anchored on its C2H2 motif, aligned to 23
positions, and each position encoded as eight overlapping chemical groups
(hydrophobic, aromatic, positive, negative, polar, tiny, glycine, proline).
An L2 logistic regression was evaluated by repeated stratified group k-fold, so
no gene appears in both halves of any split.

| | geometry | sequence model |
|---|---|---|
| ROC AUC | 0.441 | **0.637** (sd 0.089) |
| permutation null | n/a | 0.510 (sd 0.071, p95 0.615) |
| best Youden's J | 0.022 | **0.214** |
| at sensitivity | 0.656 | 0.344 |
| and specificity | 0.366 | 0.870 |
| any cut clears both 9.2 floors | **no** | **no** |

**Sequence carries degradability information that geometry does not.** The AUC
moves from below chance to 0.637, and Youden's J by a factor of ten. The
permutation null matters here: with 32 positives, 184 columns and paralogous
zinc-finger families that grouping by gene cannot fully separate, a model can
score above 0.5 from structure alone. Shuffling the labels through the same
grouped splitter gives 0.510, and the observed score clears that null's 95th
percentile by 1.7 standard deviations. Real, and marginal.

**It is still not a classifier.** No cut satisfies sensitivity 0.70 and
specificity 0.60 together. The best operating point trades almost all
sensitivity for specificity: 0.344 and 0.870. Gate G6 stays open and the module
keeps its label.

Three routes were tried and they converge on the same ceiling:

| approach | AUC | note |
|---|---|---|
| geometry alone (shipped score) | 0.441 | below chance |
| sequence, classifying the 32 FDR-significant labels | **0.636** (sd 0.082) | best |
| sequence, regressing on continuous fold depletion | 0.605 (sd 0.124) | worse, and noisier |
| sequence plus the geometry score as a feature | 0.638 (sd 0.085) | adds nothing |
| permutation null | 0.515 | p95 0.610 |

The regression result is worth stating because it is counter-intuitive. The
binary labels use 32 of 5,663 domains and the continuous depletion uses all of
them, so the regression should have more to learn from. It does worse. Most
domains sit at noise around a fold depletion of 1.0, and the FDR labels have
already done the statistical work of separating signal from that noise;
regressing on the raw values mostly fits the noise.

Adding the geometry score to the sequence features moves the AUC by 0.0015,
which is a fifth of a standard deviation. A score that ranks at chance
contributes nothing even as one feature among 184, which is the cleanest
statement of D-024 available: the geometry is not weakly informative, it is
uninformative.

Why this is the honest ceiling for now: the classic IMiD G-loop is necessary
and not sufficient, and the counterexamples are not subtle. IKZF3 reads
`FQCNQC-G-ASF` and is degraded. ZFP30 reads `YECKEC-G-KAF` and is not. ZN184
and ZN565 carry almost exactly ZFP30's motif and both are degraded. Separating
those needs the CRBN interface, not the substrate alone, and that is a ternary
complex calculation this project does not do.

### The pooled label was the mistake: per-compound models clear the floors

The three routes above all asked one question: which zinc fingers are degraded
by **any** IMiD. That question has no clean answer, because the compounds do
not share substrates. Sievers assayed thalidomide, lenalidomide and
pomalidomide in one screen and pomalidomide, CC-122 and CC-220 in another, and
the union label asks a model to learn a set of incompatible classes at once.

Fitting one model per compound, same features and same grouped evaluation:

| label | positives | AUC | vs null | best Youden J | clears spec 9.2 floors |
|---|---:|---:|---:|---:|---|
| pooled, any IMiD | 32 | 0.636 | +1.7 sd | 0.214 | no |
| **pomalidomide** | 14 | **0.826** | **+2.91 sd** | **0.571** | **yes**, 0.857 / 0.600 |
| lenalidomide | 8 | 0.823 | +1.98 sd | 0.511 | yes, 0.750 / 0.600 |
| CC-122 | 17 | 0.708 | +2.12 sd | 0.362 | yes |
| CC-220 | 17 | 0.664 | +1.70 sd | 0.307 | no |
| thalidomide | 7 | n/a | n/a | n/a | too few positives to fit |

**Pomalidomide is the clean case**: AUC 0.826 against a permutation null of
0.509, clearing it by 2.91 standard deviations, and an operating point at
sensitivity 0.857 and specificity 0.600 that satisfies both spec 9.2 floors
together. The shipped geometry reaches 0.656 and 0.353 and no cut clears both.

**The operating points above did not survive nested validation, and the
discrimination did.** The caveat flagged when they were first reported was the
right one. Choosing the cut on an inner split and measuring it on an outer fold
the model and the threshold have both never seen:

| | non-nested | **nested** |
|---|---|---|
| pomalidomide AUC | 0.826 | **0.832** |
| pomalidomide sensitivity | 0.857 | **0.600** |
| pomalidomide specificity | 0.600 | 0.691 |
| clears both 9.2 floors | yes | **no** |

The AUC holds, so the discrimination is real. The operating point did not,
because the threshold was being chosen with the wrong objective.

**Youden's J optimises the wrong thing here.** It maximises sensitivity plus
specificity symmetrically, and spec 9.2 asks for something asymmetric:
sensitivity at least 0.70 **subject to** specificity at least 0.60. The nested
Youden cut left specificity at 0.691, nine points above its floor, while
sensitivity sat below its own. Selecting the inner-fold cut to maximise
sensitivity subject to the specificity floor, with the objective taken from the
spec rather than from the result:

| compound | objective | AUC | sensitivity | specificity | clears both floors |
|---|---|---:|---:|---:|---|
| pomalidomide | Youden | 0.832 | 0.600 | 0.691 | no |
| **pomalidomide** | **spec 9.2 floors** | 0.832 | **0.800** | **0.614** | **yes** |
| lenalidomide | Youden | 0.820 | 0.500 | 0.803 | no |
| **lenalidomide** | **spec 9.2 floors** | 0.820 | **0.800** | **0.612** | **yes** |

Both objectives are reported because the second was adopted after seeing the
first, which is analytic flexibility and should be visible rather than tidied
away. What makes it defensible: the criterion comes from the spec and was fixed
before the project began, the threshold is still chosen on inner folds the
outer fold never sees, and the AUC, which no threshold can move, is unchanged.

### Independent validation: the grammar transfers across screens

The strongest evidence that the signal is real is not any single screen. A
model trained only on the Slabicki ALV1 degrome, with no Sievers data at all,
predicts the Sievers pomalidomide degrome at **AUC 0.757** and lenalidomide at
0.757. Different laboratory, different library design, different reporter
construct, different compounds, no shared rows.

| trained on | tested on | AUC |
|---|---|---:|
| ALV1 (Slabicki) | pomalidomide (Sievers) | **0.757** |
| ALV1 (Slabicki) | lenalidomide (Sievers) | **0.757** |
| 4-Ac-Phe-Glm (Slabicki) | pomalidomide (Sievers) | 0.436 |
| 4-Ac-Phe-Glm (Slabicki) | lenalidomide (Sievers) | 0.556 |

ALV1's own nested AUC is 0.565, so it transfers better to another screen than
it fits its own, which looks contradictory and is not: its 316 positives
include a promiscuous tail that is hard to fit, while the core degron grammar
it learns is exactly what the selective compounds use. 4-Ac-Phe-Glm transfers
at chance, which is consistent with it addressing a different substrate set.

Lenalidomide clears the null by 1.98 standard deviations and CC-220 by 1.70,
which is weak. Pomalidomide at 2.91 is the only one comfortably clear.

**What it means for the module.** Degradability is compound-specific and the
project had been asking a question with no answer. That is a result about the
biology rather than about the model, and it is consistent with the direction
the field has taken: the 2025 Molecular Cell screen exists precisely because
subtle changes to the glutarimide reprogram degron selectivity.

### The 2025 screen: more data, and the signal disappears

The study spec 9.2 actually named, Slabicki et al. 2025 Molecular Cell
(10.1016/j.molcel.2025.07.019), is a 9,097-reporter library against 29
glutarimide analogs. Its primary-screen table is **truncated at 65,535 rows**,
the legacy Excel limit, so 2 compounds survive in the distributed file. Those
two still give 257 and 316 positives after Benjamini-Hochberg correction,
against pomalidomide's 14, which is finally enough for nested validation.

| compound | source | degraded | nested AUC |
|---|---|---:|---:|
| pomalidomide | Sievers | 14 (0.2%) | **0.832** |
| lenalidomide | Sievers | 8 (0.1%) | **0.820** |
| ALV1 | Slabicki | 316 (4.3%) | 0.565 |
| 4-Ac-Phe-Glm | Slabicki | 257 (2.8%) | 0.535 |

The labels are not the problem: ALV1's positives include IKZF1, IKZF3, SALL4,
ZFP91, PATZ1, ZNF276 and ZNF653, which are the canonical neosubstrates. Nor is
the encoding: these are 58-residue tandem constructs and 5,201 of 9,097 carry
two C2H2 motifs, so both fingers are encoded separately, which lifted the AUC
by about 0.02 and no more.

**The pattern that seemed to fit was promiscuity.** The two compounds where
sequence predicted degradation degrade 0.1% and 0.2% of the library. The two
where it did not degrade 2.8% and 4.3%, twenty times as many. The reading was
that a selective degrader picks substrates by a readable sequence feature and a
promiscuous one does not. It was recorded as a hypothesis rather than a
conclusion, and it needed the other 27 compounds to test.

**It was then tested on all 29, and it is wrong.** See the next section. Two
compounds are not a trend, and this one did not survive twenty-seven more.

### All 29 compounds: breadth does not predict readability

The 27 missing compounds were not missing. The truncated table is supplement 4,
the primary screen. Supplement 5, the validation screen, is a modern `.xlsx`,
is not truncated, and assays all 29 analogs against 57 constructs the primary
screen had already shown to be degrons. The test the hypothesis asked for was
possible on data already on disk.

One model is fitted on the Sievers pomalidomide degrome and scored against each
compound's own labels, with every Sievers row from a panel gene held out so no
panel protein contributes its own label.

| | value |
|---|---:|
| compounds with an estimable AUC | 24 of 29 |
| mean AUC | **0.779** |
| median / min / max | 0.769 / 0.671 / 0.954 |
| above chance | **24 of 24** |
| permutation p, 2,000 shuffles | **0.0005** |
| breadth against AUC, Spearman | **+0.175 (p=0.41)** |

The correlation is not negative, which is what the hypothesis required. ALV1,
the broadest compound in the panel at 54% of its constructs, transfers at 0.726.
A pomalidomide model reads degrons for compounds it never saw.

**Both earlier numbers still stand.** ALV1's own nested AUC really is 0.565. The
two experiments ask different questions: that one fits each compound a model on
its own screen, this one fits pomalidomide and tests the transfer. What fails
for ALV1 is fitting its 316 positives across 9,097 reporters, not reading its
degrons. The reconciliation that fits is the weak tail near the FDR cut, which a
panel of already-validated degrons does not contain. That is a hypothesis too,
and a narrower one.

**What the transfer leans on.** 69 of the panel's 72 anchored cores also occur
in the Sievers library, because C2H2 fingers repeat across the proteome. Barring
those rows as well as the genes drops the training positives from 12 to 5 and
the mean AUC to 0.579 at p=0.16. A size-matched control separates the two
causes: 200 gene-disjoint fits subsampled to 5 positives, shared cores still
allowed, average 0.716, putting the core-disjoint result at the 6.5th percentile.
Most of the drop is the smaller training set and a real residual is the core
sharing. Both numbers ship, because 57 constructs cannot separate them cleanly.

**And the panel's own limit.** These are validated degrons, so breadth across
them is selectivity within known degrons and not a proteome hit rate:
pomalidomide degrades 42% of the panel and 0.1% of the primary library. The
ordering is right and the range is compressed, which weakens a null correlation
as evidence while leaving the positive finding intact.

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

### Every zinc finger in the proteome, not only those with a hairpin

`degron.imid_degradation_score` is per hairpin candidate, so a protein whose
geometry scan never placed a candidate on its degron finger has no row to carry
the answer. That cost two real substrates: ZNF653 and ZNF692 are both
pomalidomide-degraded, and both scored low because the rows that existed
described the wrong finger. A `zinc_finger` table now scores every C2H2 motif in
every cached model with no geometry filter in front of it, as a separate column
with per-protein semantics.

**7,452 fingers over 1,123 proteins, and 2,792 of them (37.5%) overlap no
hairpin candidate**, so they were unreachable at any score before. Both misses
are closed: ZNF653 556-578 scores 0.982 where the per-candidate column gave
0.106 and 0.011, and ZNF692 417-439 scores 0.957 where it gave 0.046. 13 of the
screen's 14 pomalidomide-degraded fingers are in the table, 2 of them reachable
only because the prefilter is gone.

**What the hit list is worth is less than it looks.** Five of the seven canonical
substrates audited are genes in the scorer's training set, so their 0.907 to
0.991 are partly memory. Two are genuinely held out and it gets one: IKZF1
scores 0.907, SALL4 scores 0.264 on its documented degron and 0.485 on its best
finger, which is a miss. The gene-disjoint evidence for this scorer is the
29-compound transfer test above, not this table.

**Precision belongs in enrichment, because the prevalence is 0.24%.** Of the
5,513 fingers the screen assayed, 13 are degraded. In sample, since those labels
trained the scorer:

| cut | caught | screen-negative above it | precision | enrichment |
|---|---:|---:|---:|---:|
| 0.9 | 7 of 13 | 9 | 0.438 | **186x** |
| 0.7 | 12 of 13 | 80 | 0.130 | 55x |
| 0.5 | 13 of 13 | 255 | 0.049 | 21x |

So it ranks, it does not call. At its top band it concentrates the degrome
roughly two-hundredfold while still being wrong more often than right in
absolute terms, which is what a 0.24%-prevalence problem does to the
specificity 0.60 the spec asks for. Five high-scoring fingers that no candidate
reached were never assayed at all and are the actual new hypotheses: CTCFL
259-279, ZNF407 1688-1708, ZFP64 525-546, HIVEP3 1756-1776 and HIVEP1 88-108.
Five more above 0.9 are called not degraded by the screen (HIC1, ZNF821, IKZF5,
HIVEP2, PRDM15), which is that false-positive rate made concrete.

### The geometry score is anti-predictive on the assayed set

`degron_geometry_score` scores 0.4407 by ROC AUC over all assayed C2H2 fingers,
which is below chance. That number hides two separate failures, and separating
them is what this section is for.

The score is zero when no candidate overlaps an assayed window, and the lowest
real score is 0.4676, so the not-called fingers sit in a block beneath every
called one. That block is close to label-neutral (11 of 32 degraded, 1,932 of
5,476 not), so it is not what drags the figure down. Splitting the two
questions apart:

| Question | Measure | AUC |
|---|---|---|
| Does the scan call degraded fingers more often? | called vs not, 3,565 calls over 5,508 fingers | 0.5045 |
| Given a call, does the score rank it? | called subset, 21 degraded, 3,544 not | **0.3498** |

Calling is noise. Ranking is inverted, and not marginally: a 20,000-shuffle
permutation test on the called subset puts the null 95% band at [0.3767,
0.6244] and the observed 0.3498 outside it, two-sided p = 0.0167 (seed
20261005).

The two components that reach the atlas are inverted in the same direction and
neither is significant on its own: `mean_plddt` 0.3875 (p = 0.0775) and
`tip_rel_sasa` 0.3850 (p = 0.0670). Only the composite clears significance.

**The score has not been inverted, and should not be on this evidence.** Twenty
one positives is not a basis for flipping a shipped score, a composite can be
significant while no component is for ordinary reasons of power, and a measure
that is backwards on one screen is a result to reproduce rather than a
correction to apply. What it does establish is that the geometry composite as
weighted carries no usable signal for this benchmark, and that the sequence
model's 0.6368 is not merely better than geometry but better than something
measurably worse than guessing.

### A quarter of the score was never persisted

`degron_geometry_score` is `0.35·(pLDDT/100) + 0.40·tip_rel_sasa +
0.25·regularity`. The first two are columns in the atlas. The third was
computed in the scan, used in the sum and then dropped: it is in neither
`data/interim/degrons.jsonl` nor the `degron` table, so a quarter of the
shipped score could not be audited, ablated or direction-checked without
re-running the whole scan over 20,431 proteins.

`regularity` is now emitted by the scan, carried in the schema and loaded by
the atlas. The rescan that filled it reproduced the original run exactly:
21,717 candidates from 20,279 proteins with 570 failures, the same counts to
the row, which is what a scan that gained a field and changed no behaviour
should produce.

### What the third component turned out to be

A constant.

| component | weight | AUC on the called subset | p |
|---|---:|---:|---:|
| `mean_plddt` | 0.35 | 0.3875 | 0.0775 |
| `tip_rel_sasa` | 0.40 | 0.3850 | 0.0670 |
| `regularity` | 0.25 | **0.5001** | 1.0000 |
| the composite | | **0.3498** | 0.0167 |

The permutation test on `regularity` returns a null 95% band of [0.5001,
0.5001], with no width at all. A shuffle cannot move an AUC whose inputs are
tied, and they are: 83.3% of all 21,717 candidates carry regularity exactly
1.0, and across the 3,565 assayed fingers the scan calls, the score takes two
distinct values in total, 0.6667 and 1.0.

So a quarter of `degron_geometry_score` is 0.25 added to every row it ranks.
The score is

    0.25 + 0.35 x (pLDDT / 100) + 0.40 x tip_rel_sasa

for all practical purposes, and both surviving terms are inverted. That is the
whole of the composite's 0.3498: a weighted sum of two features that point the
wrong way, plus an offset that points nowhere.

This could not have been seen before. The value was computed in the scan, used
in the sum and discarded, so the only way to learn that a quarter of the score
was inert was to persist it and measure it. The hairpin filter admits a
candidate only when its strands are already well paired, so by the time
regularity is computed it has been selected to its ceiling: the filter and the
score are measuring the same thing twice, and the second time carries no
information.

### The Slabicki truncation is recoverable in principle, and not yet in practice

`degron_slabicki.py` reads `Screen.Primary_Ratio_pval` from supplement 4, which
Excel truncated at 65,535 rows, so 2 of the screen's drugs survive and the rest
do not. That has been recorded as a limit. What had not been checked is whether
the data behind it survived.

It did. The same workbook carries `Screen.Primary_Read.Count`, 9,098 constructs
by 256 columns, untruncated, and its column names name **18 compounds** where
the derived table has 2:

    ALV1, ALV2, AMINO.5.EM12, AMINO.5.THAL, AMINO.6.EM12, AMINO.7.EM12,
    AVA, Ace.4.Ph.Glu.Amide, Br.4.Ph.Glu.Amide, CC885, CC90009, CC92480,
    CPD946, EM12, FPFT, HY.4.EM12, HY.4.THAL, and DMSO as the control
    across 60 columns.

**Rebuilding the labels from them was attempted and failed its own check.**
Counts per million, drug against DMSO within a gate, log2: correlated with the
published LFC at r = -0.08 for ALV1 and +0.04 for Ace.4.Ph.Glu.Amide, over
6,569 and 8,271 matched constructs. That is no relationship, so the method is
wrong and nothing was extended to the other compounds on the strength of it.

The diagnosis is in the table's own `Gate` column, which holds `A` and `A.B.C`
rather than a single gate. The published statistic is a shift across a sorted
population, not a ratio between two conditions, so reproducing it needs the
methods text in supplement 1 or 2 rather than a guess at the arithmetic.

**Two routes, both open.** Reproduce the published statistic from the methods,
which gives labels directly comparable to the 2 that survived; or define a
depletion statistic of our own from the read counts and validate it against the
positive calls of those 2 rather than against their LFC values. The second does
not need the paper's arithmetic and is checkable, but it would produce labels
that are ours rather than theirs, and that distinction would have to travel with
every number built on them.

Either route turns 2 compounds into 17 on a full library of 9,098 constructs,
which is the data the per-compound result needs and the 57-construct validation
panel cannot provide.

### Why artefact precision stops at 0.9401, and why it should

377 of 401 artefact CCDs are correctly not called glue. The floor is 0.95, so
four more would clear it. All 24 misses were read.

**Ten of them never bridge anything.** CB3, D01, IBM, IPL, KAI, LXB, LXZ, NGZ,
TCA and TG1 are classified `glue_candidate` and appear in zero bridge rows, so
they cost the classifier's precision and cost the atlas nothing. The metric
measures the classification rule, not the data a user sees, and on this half of
the gap those are different things.

**The remaining fourteen are mostly what BioLiP says they are**, and the triage
head agrees independently on ten of them: four small aromatic acids (PHB, SAL,
DHB, HC4), a sulfonic acid, tridecane, two phytanyl lipids, N-oxalylglycine and
a glycerol ester. They are 138 to 885 Da, so no size rule separates them from a
real glue without taking real glues with them.

**The gap must not be closed by consulting the artefact list.**
`pipeline/ccd_classes.py` never reads BioLiP: the classifier is structural, and
BioLiP is the independent ground truth it is scored against. Feeding that list
into the rules would move precision to about 1.0 and make the number mean
nothing, which is the tautology this project already refused for the E3
substrate Spearman. Tuning the structural rules until these particular 24 fall
out is the same fault wearing a slower disguise: it is fitting the rule to the
test set.

So 0.9401 stands, and the honest reading is that it is a real 0.94 rather than
a 0.95 that could be bought. One of the 24 is probably BioLiP's error anyway:
CYC is phycocyanobilin, a light-harvesting chromophore the triage head calls a
native cofactor, and it carries 5,504 of the bridges in this set.

### Combining geometry with sequence adds nothing

D-075 left one route open. Geometry is inverted, and an inverted feature is not
an empty one: a model free to give it a negative weight can use what a
fixed positive-weighted sum throws away. So the question was whether a model
that knows geometry is backwards beats one that never sees it.

`pipeline/degron_combined.py` runs the protocol `degron_sequence.py` already
uses, on the same 5,663 fingers with the same 32 positives and the same seeds:
StratifiedGroupKFold over four folds grouped by gene, 25 repeats.

| model | AUC mean | sd | min | max |
|---|---:|---:|---:|---:|
| sequence only, 184 features | 0.6334 | 0.0772 | 0.4174 | 0.8097 |
| geometry only, 5 features | 0.5564 | 0.0751 | 0.3931 | 0.7302 |
| **both, 189 features** | **0.6348** | 0.0794 | 0.3619 | 0.8236 |
| permutation null, 200 rounds | 0.5080 | 0.0677 | p95 | 0.6075 |

**Freeing the weights recovers most of what the shipped score throws away.**
Geometry goes from 0.4407 as a fixed positive sum to 0.5564 when a model can
choose the signs, which is the inversion being used rather than suffered. It is
still inside the null band, so geometry alone remains indistinguishable from
chance, but the gap between 0.4407 and 0.5564 is the cost of the hand-chosen
weights rather than a property of the features.

**Combining adds 0.0014, which is 0.02 of one standard deviation.** Geometry
carries nothing the sequence does not already have. That is not surprising
after the fact: both describe the same C2H2 domain, one through its residues
and one through the shape those residues produce, and the shape is the more
lossy description of the two.

So the combination route is closed, and closed on a measurement. What remains
is the sequence model at 0.6334 against the shipped geometry score at 0.4407,
on a module that currently ships something worse than chance.

**It is a weak result and should be read as one.** 32 positives, a spread of
0.077 across splits, and a null whose 95th percentile is 0.6075: the sequence
model clears chance, and not by much.

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
| Best within-protein AUC, 18 features | **0.6258** | 0.65 | **misses** |
| Protein-level split honoured | yes, 135 of 403 proteins held out | required | satisfied |
| Reach window fitted | **no**, and deliberately not written back | | |

**Lysine exposure barely predicts whether a lysine is ubiquitylated.** Training
Youden's J is 0.09 and the held-out AUC is 0.55, which is a result about the
feature rather than a failure to fit it.

**And exposure is not uniquely weak.** That left a question worth settling:
one good feature away from shipping, or unanswerable from a monomer? Eighteen
features were measured for all 12,705 lysines of the 403 proteins, with whole
proteins held out. Nothing clears the floor, so the answer is the second.

| feature set | pooled AUC | within-protein AUC |
|---|---:|---:|
| exposure only, as shipped | 0.545 | 0.544 |
| every per-lysine feature, boosted | 0.629 | 0.598 |
| everything including protein-level, boosted | **0.714** | **0.626** |

**The pooled 0.714 clears the floor and is not usable.** The two strongest
single features are the protein's lysine count (pooled 0.707) and its chain
length (pooled 0.692), and both are constant within a protein, so each scores
exactly 0.500 once the AUC is computed inside one protein. That arithmetic is
the proof: they rank proteins by the fraction of lysines the catalogue annotates,
which is annotation prevalence, and the module's question is always within one
protein. The within-protein column is therefore the one that decides, and
`pipeline/degradability_features.py` prints both side by side so the pooled
figure cannot be picked up by accident later.

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

### The shipped criterion against negatives that were measured

D-067 retired `min_nz_rel_sasa` on 12,705 lysines whose negatives were assumed.
The question has now been asked of negatives that were assayed: 405,207 lysines
seen in identified peptides across 17,974 proteins, 107,653 of them
ubiquitylated and 297,554 seen and never modified. Thirty-two times the data,
and a negative set that was measured rather than inferred from silence.

| feature set | model | within-protein AUC | clears 0.65 |
|---|---|---:|---|
| `rel_sasa`, the shipped criterion | logistic | **0.4971** | no |
| `rel_sasa` | boosted | 0.5071 | no |
| all 16 per-lysine features | logistic | 0.5576 | no |
| all 16 per-lysine features | boosted | **0.6662** | **yes** |
| adding protein-level terms | boosted | 0.6678 | yes |

Exposure alone is at chance, 0.4971, which reproduces D-067's 0.5020 at scale
and settles it. Every single feature is within 0.055 of chance within protein,
`frac_acidic` highest at 0.5452 and `frac_hydrophobic` lowest at 0.4829.

What is new is the row that clears. A boosted model over the sixteen
per-lysine features reaches 0.6662 within protein, above the 0.65 floor, using
nothing but what an AlphaFold monomer provides. It does not depend on the
protein-level terms that rank proteins by annotation prevalence: adding those
moves it to 0.6678, a gain of 0.0016, which is the point. The signal is in the
combination of weak per-lysine features, not in any one of them and not in
knowing which protein a lysine belongs to.

**It is reported and not shipped.** Spec 5.4 defines a reach window as four
thresholds, and a model is not a window: emitting its score would answer a
different question from the one the module asks, and the four numbers it
defines still have no fit (D-068). What this does establish is that the floor
is reachable from a monomer, which was open until now, and that the thing
blocking a degradability verdict is the shape of what spec 5.4 asks for rather
than the absence of signal in the data.

### The abstain head, wired to the box

Task C scored a 0.0 fabrication rate over 40 unanswerable questions and was
called by nothing. A question the atlas cannot answer went to the query head,
came back as a query object naming a field that does not exist, and reached the
user as "the model proposed an invalid query: field 'binding_affinity' is not a
field of bridge". That is the parser's complaint about the model, not an answer
to the person who asked.

`/api/nl` now asks the abstain head when the parser rejects a proposal.
Measured over 20 held-out unanswerable questions:

| outcome | before | after |
|---|---:|---:|
| explained to the user | 0 | **16** |
| raw parser error | 16 | 0 |
| schema-valid but wrong query | 4 | 4 |

What the user reads instead: *"A degradability readout needs all three corners
pinned. Missing: ligase."* and *"Cooperativity is not computable from a
structure. BINMAN stores no measured cooperativity values."*

**The 4 that remain are the honest limit, and they are the dangerous ones.**
Those questions produce a query the schema accepts. Asked for a binding
affinity in nanomolar the model filtered on ΔSASA and molecular weight; asked
which compounds passed phase II it filtered on tier and evidence class. Both
are wrong and neither is catchable by a parser, because every field named
exists. The abstain head is never consulted on them, since nothing failed.

Closing that gap means asking the abstain head first on every question, which
doubles the model calls per query on a time-boxed ZeroGPU allocation. The
measurement is here; the trade is not taken.

### The triage head, applied to the atlas

Task B was trained and scored and then used for nothing. `evidence_class`, which
spec line 467 defines as its label, was NULL on all 285,996 bridge rows. It is
now filled for the 6,510 entry-ligand pairs whose ligand is classed as a glue
candidate: 27,590 bridge rows, 6,498 pairs classified and 12 unparseable, which
are left NULL rather than guessed.

| predicted class | pairs | |
|---|---:|---:|
| molecular_glue | 3,257 | 50.0% |
| native_cofactor | 2,575 | 39.6% |
| crystallisation_artefact | 578 | 8.9% |
| protac | 88 | 1.4% |
| unparseable, left NULL | 12 | 0.2% |

**Agreement on components the model had never seen: 14 of 15.** Task B is split
by chemical component, so the overlap between these predictions and
`task_b_test` is the out-of-sample check, and 93% sits where spec 9.5's 0.9336
macro F1 says it should.

The first measurement of this said **14.4%**, and the error is worth keeping.
Agreement was counted per entry-ligand pair rather than per component, and one
component, CYC, appears in 119 of the 139 overlapping pairs. Counting per pair
when the split was made per component lets a single common ligand outvote
fourteen others. The unit of a generalisation check has to be the unit the
split was made on.

**The one disagreement is probably the label, not the model.** CYC is
phycocyanobilin, the light-harvesting chromophore of phycobiliproteins. BioLiP
lists it as a crystallisation artefact, which is what makes it the curated
label here; the model calls it a native cofactor, which is what it is. BINMAN's
own structural classifier independently disagrees with BioLiP too, calling it a
glue candidate, which is why it is in this set at all. Three classifiers, three
answers, and the published one is the least defensible.

**This is the only model-derived column in the atlas.** Its FieldSpec
description says so, in the text that reaches the column tooltip and the query
builder, because the number beside it is 0.9336 and not 1.

## Section 9.5 BINMAN-LM

Measured against the **complete** atlas, with the corpus regenerated from it
(the ligase vocabulary went from 10 to 650 once the E3 stage finished).

### Task A: natural language to query object

Reported for the **shipped adapter, round 07**: 32 LoRA layers at rank 8,
14,152 iterations. `config/tuning.toml` names the stage, so these floors follow
the model on the Hub rather than whichever evaluation ran last.

| Metric | Baseline (zero-shot) | Shipped (round 07) | Floor | Verdict |
|---|---:|---:|---:|---|
| Parse rate, synthetic held out | 0.5133 | **1.000** | 0.99 | **passes** |
| Set equality, synthetic held out | 0.3467 | **1.000** | 0.90 | **passes** |
| Triage macro-F1 (Task B) | n/a | **0.9336** | 0.85 | **passes** |
| Fabrication rate (Task C) | 0.30 | **0.000** | 0.00 max | **passes** |
| Abstention rate (Task C) | 0.00 | **1.000** | reported | n/a |
| Exact match | 0.12 | 0.975 | reported | n/a |
| Prompt tokens needed | 841 | **83** | n/a | n/a |
| Set equality, externally phrased | n/a | **not computed** | 0.80 | see below |

**Every spec 9.5 floor that can be measured now passes.** Parse rate was the
last to clear: round 05 reached 0.9867 and missed by two queries out of 150,
and round 07 parses all 120 held-out queries and returns the right row set for
every one.

Two things are worth stating about how this number came to exist at all. The
floors were not machine-checked until round 07: `section_95` dumped the raw
evaluation file into the results without a single pass or fail, so the LM was
the only module whose floors no gate ever saw. And Task B was never evaluated
in any round before this one, because `evaluate_triage` sat below the
`__main__` guard and was unreachable (DECISIONS D-034).

The gain came from LoRA depth, not from more data. See the ablation below.

### The ablation: depth is the lever, epochs are not, and the knobs do not compound

Four rounds, each varying one thing against the round 06 control, all scored on
the same class-balanced 240-sample triage set at a fixed seed:

| round | LoRA layers | rank | batch | Task B macro-F1 | glue F1 | Task A set eq | train |
|---|---:|---:|---:|---:|---:|---:|---:|
| 06 control | 16 | 8 | 4 | 0.8862 | 0.849 | 0.9833 | ~170 min |
| **07, shipped** | **32** | 8 | 4 | **0.9336** | 0.958 | **1.000** | 221 min |
| 08 | 16 | **32** | 4 | 0.9293 | **0.967** | 0.9917 | 173 min |
| 09 | 32 | 32 | **2** | 0.8711 | 0.869 | 1.000 | 133 min |

**Epochs are not the lever.** Round 05 saw 0.23 epochs and round 06 saw two, an
eightfold difference in exposure, and Task B moved from 0.8956 to 0.8862, which
is within sampling noise at n=240. Coverage was never the bottleneck.

**Capacity is.** Either knob alone lifts macro-F1 by about 0.045, and the gain
lands on `molecular_glue`, the rarest class and the one the project exists to
find: recall rises from 0.750 to 0.950 with depth and to 0.983 with rank. Width
is the cheaper route, reaching within 0.004 of depth for 48 fewer minutes.

**They do not compound.** Round 09 combined both and fell to 0.8711, below the
control, with the loss concentrated exactly where the single knobs gained. That
comparison is confounded and is labelled rather than reported flat: round 09
ran at batch 2 with gradient checkpointing because batch 4 at that capacity
exhausted swap and collapsed to three iterations a minute, so it differs in two
ways rather than one. Since epochs were already ruled out, batch size is the
likelier confound, and the model with four times the trainable parameters is
the least able to absorb noisier gradients. A clean re-run needs memory this
machine does not have (DECISIONS D-038).

**A hyperparameter that was never applied.** `LORA_RANK` appeared in the W&B
config, the run notes and `training.json` for rounds 01 to 06, and never in the
training command: `mlx_lm lora` has no `--lora-rank` flag and defaults to 8.
Rank became a real knob only once a YAML config was passed (DECISIONS D-033).
Every published figure stands, because the model that produced them is the
model that trained; what was wrong was the recorded hyperparameter.

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
| `binman-qwen-2.5-3b-4bit-round05` | LoRA SFT, rank 8, 16 layers, 1,200 iterations | superseded |
| `binman-qwen-2.5-3b-4bit-round06` | rank 8, 16 layers, 14,152 iterations | evaluated |
| `binman-qwen-2.5-3b-4bit-round07` | rank 8, 32 layers, 14,152 iterations | **shipped** |
| `binman-qwen-2.5-3b-4bit-round08` | rank 32, 16 layers | evaluated, not shipped |
| `binman-qwen-2.5-3b-4bit-round09` | rank 32, 16 layers | evaluated, not shipped |
| `binman-qwen-2.5-3b-4bit-round10` to `round13` | rank 32 and rank 8 at 32 layers | trained, not in the evaluated set |
| `binman-qwen-2.5-32b-4bit-round14` | the 32B experiment | rejected, see above |

**This table was wrong until 2026-10-05.** It named round 04 as shipped at rank
16 over 16 layers, and round 04 has no artefact left: `models/binman-lm/runs/`
begins at round 05. What ships is round 07, confirmed twice over. The adapter
repository the Space loads reports `r: 8` over 32 transformed layers, and
`results.json` 9.5 reports its evaluated stage as `round07-32layers`. The
parameters in the old entry matched neither.

Round 07: rank 8, 32 layers, lr 1e-5, 14,152 iterations, 4,752 train and 574
valid examples, on the M2 Ultra. Tracked in Weights & Biases under `binman-lm`.

Rounds 10 to 13 exist as runs and are not in `results.json`'s evaluated stage
list. They are recorded here as trained rather than given an outcome, because
no measurement of them survives to support one.

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
