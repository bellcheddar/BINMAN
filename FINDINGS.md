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

### Recall, the misses list and the novel-bridge set: not computed

All three curated glue databases (MGDB, MolGlueDB, MGTbind) publish through
JavaScript front ends with no documented bulk-export endpoint, and none resolved
(Gate G7). Spec 4.1b forbids substituting a hand-written positive set, so none
was made.

**This suppresses the headline result.** A novel bridge is defined as one
appearing in *none* of the three databases, so the set is undeterminable. The
`novel_bridge` column reads 0 throughout the atlas, and both the UI and the
atlas builder state in words that this is not a real zero.

Packing specificity is also not computed: ProtCID did not resolve.

## Section 9.2 Degron Scan validation

**The spec 9.2 metric cannot be computed.** It requires the matched degraded and
non-degraded zinc-finger sets from the Molecular Cell 2025 and Nature
Communications 2025 screens, and neither resolved (Gate G7). Sensitivity and
specificity are therefore **not computed**, not estimated. Without the matched
negative set there is no way to know whether a hairpin-plus-glycine filter is
selecting anything, so the Degron Scan ships as a **hypothesis generator, not a
classifier**, exactly as spec 9.2 instructs for this case.

What follows is a method sanity check against degrons documented in the
structural literature. It is **not** a substitute for 9.2: the set is small, it
was used to calibrate the thresholds, and it contains no negatives.

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

### What this does and does not establish

It establishes that the filter can find the geometry it is meant to find, and
that the spec's literal thresholds could not. It establishes nothing about
specificity. Relaxing the strand floor from 3 to 2 admits far more hairpins
proteome-wide, and the cost is unmeasured because the matched negative set is
unavailable. `calibration_validated = false` in `config/thresholds.toml` records
that, and the module's UI says so on its face.

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

Not computed yet: the stage has not run. The reach window in
`config/thresholds.toml` is still flagged `fitted = false` and its spec 1.0
starting values carry no empirical standing.

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
