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

Not computed yet: the stage has not run.

**Recall against curated glue databases cannot currently be computed.** All
three curated sources named in spec 4.1b (MGDB, MolGlueDB, MGTbind) publish
through JavaScript front ends with no documented bulk-export endpoint. Gate G7
is open and the gap is recorded in `data/validation/MANIFEST.md` with the
verified manual route for each. Spec 4.1b forbids substituting a hand-written
control, so no substitute has been made.

**Artefact precision can be computed.** BioLiP2's artefact ligand list resolved
(463 CCD codes, BSD-2-Clause, confirmed against `script/rmligand.cpp` in
`kad-ecoli/mmCIF2BioLiP`, which documents the file as the artefact ligand list).
Spec 9.1 asks for artefact precision to be reported before recall, and that is
the metric that is available.

## Section 9.2 Degron Scan validation

Not computed yet: the stage has not run. The matched zinc-finger screen sets
have not yet been acquired.

## Section 9.3 E3 Triage validation

Not computed yet: the stage has not run. UbiBrowser resolved (3,158
literature-curated human E3-substrate pairs plus the predicted network), so the
substrate-count agreement and enrichment tests are computable once the ligase
table exists.

## Section 9.4 Degradability validation

Not computed yet: the stage has not run. The reach window in
`config/thresholds.toml` is still flagged `fitted = false` and its spec 1.0
starting values carry no empirical standing.

## Section 9.5 BINMAN-LM

Not computed yet: Phase 3 has not run.
