# Gate G6 open

Opened at 2026-10-03T17:26:39+00:00.

## What is needed

Spec 9.1 artefact precision measures 0.927 on a held-out half of BioLiP2's artefact ligand list, against a 0.95 floor. Decision needed: proceed with the caveat below, or change the metric definition.

The diagnosis is that the metric as specified assumes BioLiP's `ligand_list` is pure crystallisation furniture. It is not. BioLiP's own curation code treats it as a list of *candidate* artefacts and then checks each one against the entry's PubMed abstract before excluding it, so the list retains genuine ligands. Of the 22 components BINMAN still calls `glue_candidate`, the majority are real pharmacology: nevirapine (an approved NNRTI), IBMX, kainic acid, 10-propargyl-5,8-dideazafolic acid (an antifolate) and a chlorinated indole sulfonamide inhibitor. Classing those as drug-like is the correct answer, not an error, and driving the number to 0.95 would mean deliberately misclassifying approved drugs as furniture.

A short tail of genuine classification gaps also remains: phycocyanobilin (an open-chain bilin the porphyrin pattern does not match), molybdopterin, and tridecane (one carbon below the long-alkane rule's threshold).

## What unblocks it

```bash
# Option A: accept and proceed with the caveat recorded in FINDINGS.md
#   nothing to run, the build already continues past this gate
#
# Option B: restrict the negative set to BioLiP artefact codes that BioLiP
#   itself actually excluded, which needs its per-entry exclusion decisions
#   rather than the candidate list, then re-run:
pixi run python pipeline/validate.py --section 9.1
```

## Already done

The classifier is built and measured. Structural rules over SMILES (RDKit) replaced name matching, which lifted precision from 0.799 to 0.953 overall. Measurement used a deterministic 50/50 split of the 463 artefact codes: rules were developed against the dev half (0.978) and the reported figure comes from the holdout half (0.927). The split is recorded in the measurement script so the result is reproducible.

## What happens next

G6 is reported, not blocking: the build continues. FINDINGS.md carries the measured value, both split halves, and the enumerated residual components so a reader can judge the metric rather than take the headline number. No threshold was loosened to make the figure pass.
