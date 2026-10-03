# BINMAN open gates

Three gates are open. **None of them blocks the build**: the pipeline ran to
completion past all three, and each is recorded here with exactly what it needs.

| Gate | State | Blocks? | What it needs |
|---|---|---|---|
| **G7** Dataset access | open | no | 6 of 10 validation datasets need a manual download |
| **G6** Science | open | no | one measured floor missed, with the diagnosis below |
| **G3** Deploy | open | yes, by design | approval to rsync, plus DNS, nginx and certbot |

Gates **G1** (compute), **G2** (secrets) and **G5** (disk) never opened. Gate
**G4** (publish) was authorised by Marc at build start and the repository is live.

---

## G7: six validation datasets could not be obtained automatically

`data/validation/MANIFEST.md` carries the full record: every route tried, the
outcome of each, the licence, and the manual route for each gap.

| Dataset | What it blocks |
|---|---|
| MGDB, MolGlueDB, MGTbind | Glue Atlas **recall**, the three-way agreement Venn, the misses list, and the **novel-bridge set** |
| ProtCID | Glue Atlas **packing specificity** |
| PROTAC-DB 3.0 | LM Task B (the confusable negative class) and the Glue Atlas exclusion set |
| DEGRONOPEDIA | Degron Scan cross-reference |
| Zinc-finger degradation screens | Degron Scan **sensitivity and specificity** |
| PhosphoSitePlus / ProteomeXchange diGly | Degradability **reach window fit** and its held-out AUC |

Each publishes through a JavaScript front end with no documented bulk-export
endpoint, or sits behind registration. **No hand-written control was substituted
for any of them** (spec 4.1b), so the dependent metrics are reported as "not
computed" with the reason rather than estimated.

**The most consequential gap is the novel-bridge set.** Spec 9.1 calls it the
headline result, and it is defined as a bridge appearing in *none* of the three
curated glue databases. With none resolved the set is undeterminable, so the
atlas column reads 0 and the UI says in words that this is not a real zero.

### What unblocks it

```bash
# download each file by hand from the homepage in data/validation/MANIFEST.md,
# drop it in data/validation/raw/<dataset_name>, then:
pixi run python pipeline/acquire_validation.py --refresh
pixi run python pipeline/build_atlas.py
pixi run python pipeline/validate.py
```

---

## G6: artefact precision measures 0.945 against a 0.95 floor

**The measured value.** 0.9449 over the 345 BioLiP2 artefact CCD codes that
appear in the atlas (326 of them correctly not called glue candidates). On the
deterministic held-out half of the full 463-code list, used so the classification
rules could not be tuned on the number being reported, it measures **0.927**.

**The diagnosis, which matters more than the number.** The metric assumes
BioLiP's `ligand_list` is pure crystallisation furniture. It is not. BioLiP's own
curation code (`script/rmligand.cpp` in `kad-ecoli/mmCIF2BioLiP`) treats that file
as a list of *candidate* artefacts and then checks each against the entry's
PubMed abstract before excluding it, so the list retains genuine ligands. The
components BINMAN still calls drug-like include **nevirapine** (an approved
NNRTI), **IBMX**, **kainic acid**, **10-propargyl-5,8-dideazafolic acid** (an
antifolate) and a chlorinated indole sulfonamide inhibitor. Classing those as
drug-like is correct. Reaching 0.95 would mean deliberately misclassifying
approved drugs as crystallisation furniture.

A short tail of genuine classification gaps also remains: phycocyanobilin (an
open-chain bilin the porphyrin pattern does not match), molybdopterin, and
tridecane (one carbon below the long-alkane rule).

**What was already done.** Structural rules over SMILES replaced name matching,
which lifted precision from 0.799 to 0.953 overall. No threshold was loosened to
make the figure pass.

### The decision needed

- **Option A (recommended): accept and proceed with the caveat.** It is recorded
  in `FINDINGS.md` and nothing further runs.
- **Option B: restrict the negative set** to the codes BioLiP actually excluded,
  which needs its per-entry exclusion decisions rather than the candidate list,
  then re-run `pixi run python pipeline/validate.py`.

## G6, second item: BINMAN-LM parse rate 0.987 against a 0.99 floor

Two queries of 150 failed to parse: one omitted a `value`, one used an
`exploitation_status` outside the closed vocabulary. Both are the parser
correctly refusing invalid output. Set equality, the primary Task A metric,
measures **0.98** against a 0.90 floor and passes comfortably.

## G6, third item: the register-mismatch gap

Not a floor miss, because the specified metric could not be computed, but the
more serious result. BINMAN-LM scores **0.98** set equality on phrasing shaped
like its training generator and **0.067** on fifteen hand-written questions
against the same schema in ordinary prose.

The spec 3.6 external query set could not be built: of 463 sentences harvested
from open-access reviews, 18 are genuinely interrogative and **none** asks
something BINMAN's schema can answer. Review articles pose mechanistic questions,
not database queries. The metric is reported as not computed rather than measured
on mis-paired rows.

**This is why the natural-language box is a feature flag.** The deterministic
query builder is the primary interface and always works; the model is an
accelerator for users who phrase questions the way the corpus does.

### Decision needed

Accept, or commission a hand-written external query set from a working scientist
who is not the author, which is the only way to measure register mismatch
properly for this schema.

### Floors that were measured and passed

| Metric | Measured | Floor |
|---|---|---|
| E3 Triage rank enrichment | **p = 0.0024** | p < 0.01 |
| E3 Triage pocket coverage | **0.982** | 0.80 |
| BINMAN-LM set equality (synthetic) | **0.98** | 0.90 |
| BINMAN-LM fabrication rate | **0.00** | 0.00 |

The enrichment initially measured p = 0.069 and failed. The cause was a genuine
repertoire bug, not a threshold: the InterPro signature list omitted the CRL4
substrate receptors, so **CRBN and VHL were absent from the E3 repertoire
entirely**. With the CULT, VHL-box, DCAF15, DCAF16 and DCAF families added, the
known degrader ligases rank DCAF15 first, VHL fifth, DCAF16 sixth and CRBN
thirty-second, **without exploitation status being an input to the score**, and
the enrichment passes.

---

## G3: deploy

`deploy/` is written and has **never been run**. `deploy/rsync.sh` refuses to
start without an explicit confirmation variable, so no unattended invocation can
reach the droplet.

### What is needed

1. Approval to transfer the atlas bundle to `binman.mdeller.com`.
2. DNS for `binman.mdeller.com` pointing at the droplet.
3. nginx and certbot on the droplet.

### What unblocks it

```bash
./deploy/preflight.sh            # already passes: 0.07 GB, no third-party rows, no weights
BINMAN_DEPLOY_CONFIRM=yes BINMAN_HOST=deploy@mdeller.com ./deploy/rsync.sh
```

Then, on the droplet, the systemd and nginx steps in `deploy/README.md`.
