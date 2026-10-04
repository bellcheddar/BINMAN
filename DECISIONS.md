# BINMAN decisions

Every ambiguous choice taken during an unattended build, with the alternatives
considered, the reason, and how to reverse it (spec Section 0 rule 1).

---

## D-001: Gate G4 (publish) authorised at build start

**Decision.** Create a public GitHub repository and push to it.

**Context.** The spec denies `git push` and `gh repo create` and routes any
publication through Gate G4. Marc authorised the public repository explicitly in
the build instruction ("also make the public repo"), which opens G4 up front.

**Alternatives considered.** Keep every commit local and open G4 at the end. Push
to a private repository and leave visibility to Marc.

**Reason.** The authorisation was explicit and unconditional. G4 exists to stop an
unattended agent publishing without consent, and consent was given.

**Scope limit.** G4 covers the repository only. **Gate G3 (deploy) is untouched:**
nothing is rsynced to the droplet, no DNS or nginx change is made, and
`deploy/` is written but never executed.

**Reversal.** `gh repo edit --visibility private`, or delete the repository.

---

## D-002: pixi `system-requirements.macos = "14.5"`

**Decision.** Pin a macOS 14.5 minimum platform in `pixi.toml`.

**Context.** pixi defaults to solving osx-arm64 against a `macos=13.0` minimum
platform. Every available `fpocket` build declares `__osx >=14.5`, so the solve
failed with "no viable options" even though the host runs macOS 27.0.1.

**Alternatives considered.** Drop fpocket and go straight to the documented P2Rank
fallback. Build fpocket from source via Homebrew.

**Reason.** fpocket is the spec's first choice for `pocket_score` and the
requirement is satisfied by the host by a wide margin. Pinning the minimum
platform is the smallest change that reflects reality.

**Reversal.** Remove the `[system-requirements]` table. fpocket then drops out and
`pipeline/pockets.py` falls through to P2Rank.

---

## D-003: `KMP_DUPLICATE_LIB_OK=TRUE` in the pixi activation environment

**Decision.** Set `KMP_DUPLICATE_LIB_OK=TRUE` for the compute environment.

**Context.** `pydssp` pulls PyTorch, which links its own libomp. Importing it
alongside numpy/scipy aborts with "OMP: Error #15: Initializing libomp.dylib, but
found libomp.dylib already initialized."

**Alternatives considered.** Drop pydssp entirely (real `mkdssp` 4.6.1 resolved,
so pydssp is only the fallback). Install PyTorch from conda-forge so a single
OpenMP runtime is shared.

**Reason.** pydssp is retained as the documented fallback for the hairpin scan, and
the flag is the only way to keep both importable in one process. The risk the flag
warns about applies to concurrent OpenMP work; BINMAN's parallelism is
process-level (`ProcessPoolExecutor`), not OpenMP threads, so the exposure is low.

**Reversal.** Remove the `[activation.env]` entry and the `pydssp` dependency.
`mkdssp` remains the primary path and is unaffected.

---

## D-004: `.claude/settings.json` not written by the build

**Decision.** Ship the spec 12.1 permission set as `deploy/claude-settings.json`
and leave installing it to Marc.

**Context.** Writing `.claude/settings.json` modifies the permissions of the agent
performing the build, which the harness blocks as self-modification.

**Alternatives considered.** None available: the write is refused by the harness.

**Reason.** The file is a deliverable, not a build dependency. Nothing in the build
reads it.

**Reversal.** `cp deploy/claude-settings.json .claude/settings.json`. Note that the
spec's original deny list blocks `git push` and `gh repo create`, which D-001
supersedes: the shipped copy reflects D-001.

---

## D-005: UbiBrowser predicted network retained at p < 0.01

**Decision.** Keep only predicted E3-substrate pairs with `Pvalue < 0.01`, and
store four columns rather than the source's eighteen.

**Context.** The full human prediction set is 11,365,676 pairs, 1.4 GB as TSV,
over 710 E3s and 20,228 substrates, with a near-uniform p-value distribution
(median 0.498). Committing it also put a 1.4 GB licence-restricted file into git.

**Alternatives considered.** Keep everything and exclude it from git only. Keep
the top N pairs per E3. Use a score cut on `interScore` instead of `Pvalue`.

**Reason.** A near-uniform p-value distribution over every plausible pair carries
almost no information in its upper range, and spec 9.3 uses the
**literature-curated** set as the reference for substrate-count agreement. The
predicted set exists only to report predicted coverage separately. A p-value cut
is the source's own confidence measure, so it is the defensible axis to cut on.

**Reversal.** Change `PREDICTED_PVALUE_CUT` in `pipeline/acquire_validation.py`
and re-run the stage. The raw bytes are cached, so no re-download is needed.

---

## D-006: no parsed validation derivative is tracked in git

**Decision.** `.gitignore` excludes every parsed file in `data/validation/`,
including the ones whose source licence would permit redistribution.

**Context.** The first Phase 1.0 commit included `ubibrowser_predicted_e3.tsv`
(1.4 GB) and `biolip2_annotations.tsv` (13 MB), both from sources whose terms do
not grant redistribution. The commit was discarded and rebuilt before any push.

**Alternatives considered.** Ignore only the sources that forbid redistribution,
and track BioLiP2's BSD-2-Clause artefact list.

**Reason.** One pattern that covers the whole directory is enforced by the tool;
a per-source allowance depends on everyone remembering which source permits
what, and the cost of getting it wrong is a licence breach in a public
repository. `data/validation/MANIFEST.md` is tracked, so the provenance, row
counts and licences are all public even though the rows are not.

**Reversal.** Narrow the `data/validation/*` patterns in `.gitignore`.

---

## D-007: the BioLiP2 artefact list is held out of CCD classification

**Decision.** `pipeline/ccd_classes.classify()` does not take the BioLiP artefact
list as an input, and takes no argument that would let a caller pass it.

**Context.** Spec 9.1 scores BINMAN on whether it classes BioLiP2's artefact
ligands as furniture rather than as glue candidates. The 463 codes were available
and using them would have made that metric read 1.00.

**Alternatives considered.** Seed the artefact codes into the furniture classes
and report the metric anyway.

**Reason.** A metric that measures a lookup measures nothing. Holding the list out
keeps artefact precision a genuine test of an independent classifier, and the
number it produces (0.927 on a held-out half) is informative precisely because it
is not 1.00.

**Reversal.** Pass the artefact codes into the seed sets in `ccd_classes.py`. Note
that doing so invalidates the spec 9.1 artefact precision figure.

---

## D-008: references are resolved by Crossref search, never recalled

**Decision.** `pipeline/references.py` holds a bibliographic query and a set of
expected title words per reference, and takes the DOI from Crossref's search
endpoint. No DOI is written by hand.

**Context.** The first revision carried hand-written DOIs. Crossref showed that
several resolved to unrelated works: the DEGRONOPEDIA DOI returned a Reactome
paper, the DCAF15 DOI returned a Zika virus paper, the Open Targets DOI returned
an unrelated gene-association resource, and one entry contained a placeholder
string that was never a DOI at all. Each would have been published as a verified
citation.

**Alternatives considered.** Keep the hand-written DOIs and only check that they
resolve. Drop any reference that cannot be verified.

**Reason.** Checking that a DOI resolves does not check that it resolves to the
right paper, which is the failure that actually occurred. Matching the returned
title against expected words catches it. Conference abstracts and Faculty
Opinions recommendations are filtered out because they carry the right words and
the wrong work, and a journal article is preferred over a preprint.

**Reversal.** Not advisable. If a reference must be pinned to a specific DOI, add
it as a `doi_hint` cross-check rather than as the source of truth.

---

## D-009: `tumour_enriched` cannot be populated from the current Open Targets schema

**Decision.** Leave `ligase.tumour_enriched` at 0 for every row and record the gap,
rather than filling the column with a different quantity.

**Context.** Spec 5.3 defines `tumour_enriched` as "boolean from Open Targets
expression comparison". The current Open Targets GraphQL schema no longer exposes
`Target.expressions`; it offers `Target.baselineExpression.rows`, whose fields are
per-biosample quartiles plus `specificity_score` and `distribution_score`. None of
those is a tumour-against-normal comparison.

**Alternatives considered.** Populate the column from `specificity_score`, which is
available and is a good selectivity measure.

**Reason.** `specificity_score` measures tissue restriction, not tumour enrichment.
Putting it in a column named `tumour_enriched` would mean every downstream reader,
including the UI and the triage weights, silently used the wrong quantity.
`expression_breadth` is still populated per spec, as the count of biosamples with
median expression above the configured threshold.

**Reversal.** If Open Targets restores a tumour comparison, implement it in
`fetch_expression`. To use specificity instead, add it as its own column with its
own name rather than reusing this one.

---

## D-010: the degron hairpin thresholds are calibrated, as the one spec 9.6 adjustment

**Decision.** `min_strand_length` 3 to 2, `max_turn_length` 5 to 6, and
`min_tip_rel_sasa` 0.40 to 0.30. `min_mean_plddt` unchanged at 70.

**Context.** The spec 5.2 values applied literally recover **none** of the
canonical CRBN zinc-finger neosubstrates. The diagnosis is specific: in the
AlphaFold model of IKZF1, residues 145 and 146 bridge antiparallel to 153 and 154
(DSSP bridge partners 145 to 154 and 146 to 153) with Gly151 at the turn apex and
pLDDT 72, which is a textbook hairpin degron. It fails three thresholds at once:
the strands are 2 residues against a floor of 3, the turn is 6 residues against a
ceiling of 5, and Gly151's relative SASA is 0.34 against a floor of 0.40.

Measured across five documented degrons (table inline in
`config/thresholds.toml`): strand lengths 2, 2, 2, 8, 8; turn lengths 6, 6, 5;
relative SASA 0.34, 0.15, 0.44, 0.48, 0.43; pLDDT 71.9 to 96.4.

**Alternatives considered.** Keep the spec values and report zero recall. Lower the
SASA floor to 0.10 so IKZF3 is also recovered.

**Reason.** A filter that cannot find the degron class the module exists to find is
not conservative, it is broken, and spec 9.6 allows exactly one documented
adjustment. The values chosen are the measured geometry of real degrons rather than
whatever made a number pass. IKZF3 (relative SASA 0.15) is left as a reported miss:
its degron glycine is largely buried in the monomer model and becomes exposed only
in the ternary complex, and a floor low enough to catch it would fire across most
of the proteome.

**The cost, stated plainly.** Relaxing the strand floor to 2 admits many more
hairpins proteome-wide, so specificity falls. Spec 9.2 exists to measure exactly
that, and its matched zinc-finger screen datasets did not resolve (Gate G7). This
calibration is therefore **not independently validated**, `calibration_validated`
is `false` in the config, and the Degron Scan is presented as a hypothesis
generator rather than a classifier until the screens are obtained.

**Reversal.** Restore 3, 5 and 0.40 in `config/thresholds.toml` and re-run stage
2.1. Recall against the documented degrons returns to zero.

---

## D-011: the degron tip is the apical glycine in the turn, not the geometric apex

**Decision.** `find_hairpins` identifies the tip as the most apical **glycine**
within the turn (widened by `tip_glycine_offsets`), and reports the geometric apex
alongside it as `apex_res` rather than discarding it.

**Context.** Spec 5.2 step 2 defines the tip as the turn residue with the greatest
C-alpha distance from the strand-pair centroid, then step 3 asks whether the tip or
tip +/- 1 is glycine. On a six-residue turn those are different residues. In IKZF1
the geometric apex is Gln149 at 11.1 A from the centroid while the degron glycine,
Gly151, sits at 7.6 A: two positions away and therefore outside the apex-plus-one
window. The canonical degron was detected as a hairpin and then thrown away at the
glycine test.

**Alternatives considered.** Widen `tip_glycine_offsets` to +/- 3, which admits any
glycine within three residues of the apex and is a blunter version of the same
idea. Keep the spec definition and report zero recall.

**Reason.** The degron is defined by its exposed glycine, so the glycine is the
feature of interest and the geometric apex is a proxy for where it should be. Where
the turn holds no glycine the hairpin is still rejected, so the filter has not been
made more permissive about what counts as a degron: it has been made correct about
where to look. Reporting `apex_res` keeps the geometric measurement visible.

**Result.** Recovery of documented degrons went from 1 of 5 to 3 of 5: IKZF1
Gly151, SALL4 Gly416 and CSNK1A1 Gly40 are all found at exactly the documented
position. The two remaining misses are diagnosed rather than hidden (see
FINDINGS.md).

**Reversal.** Restore the apex-based tip in `find_hairpins`. Recovery of documented
degrons falls back to 1 of 5.

---

## D-012: the E3 repertoire was missing the CRL4 substrate receptors

**Decision.** Add the CULT, VHL-box, DCAF15 and DCAF16 InterPro signatures, plus a
name-based DCAF family rule, to `config/thresholds.toml`.

**Context.** The spec 5.3 family list names "Cullin-RING adaptors: F-box, DCAF,
SOCS, BTB", and the first implementation covered RING, HECT, RBR, F-box, BTB,
SOCS, U-box, Cullin and APC/C. It had no DCAF signature. The consequence was
severe and only surfaced through the Section 9.3 validation: **CRBN and VHL were
absent from the E3 repertoire entirely**, along with DCAF15 and DCAF16. Those are
the ligases targeted protein degradation is actually built on, and the module
exists to triage them.

The spec 9.3 enrichment test measured p = 0.069 and failed its p < 0.01 floor,
because the "validated" group contained 12 chemically validated ligases and not a
single clinically validated one: both clinically validated entries were missing
from the repertoire.

**Alternatives considered.** Add a generic WD40 signature for the DCAF family,
which would have pulled in several hundred unrelated WD40 proteins. Hand-pick the
known degrader ligases by accession.

**Reason.** The signatures were read from each protein's own UniProt InterPro
cross-references rather than recalled, so they are the proteins' real
annotations. The DCAF family has no single distinguishing InterPro signature (a
DCAF is a WD40 protein), so UniProt's own recommended-name annotation,
"DDB1- and CUL4-associated factor", is used instead: a precise published rule
rather than a hand-picked list.

**Result.** The repertoire went from 625 to 650 ligases. The enrichment test now
measures **p = 0.0024** and passes. DCAF15 ranks first, VHL fifth, DCAF16 sixth
and CRBN thirty-second, with `exploitation_status` and `has_ligand` held out of
the score, so the ranking was not told which ligases are validated.

**Reversal.** Remove the added signatures and the `[e3_triage.name_families]`
table. Note that this removes CRBN and VHL from the atlas.

---

## D-013: each model is evaluated with the prompt it was trained on

**Decision.** `lm/evaluate.py` sends the full schema in the system turn only for
the zero-shot baseline. A run with an adapter uses the short system turn the
adapter was fine-tuned with.

**Context.** The first evaluation of the fine-tuned adapters scored parse rate
0.0 and set equality 0.0, worse than the untrained baseline. The cause was a
train/serve mismatch, not a bad fine-tune: training used a short system turn with
no schema, and the evaluation prepended a 6 KB schema the model had never seen.
With the unfamiliar prefix it began omitting `record_type`, which the parser then
rejected. Measured directly on one query: with the training prompt it emits a
complete, valid object; with the schema prepended it emits the same object minus
`record_type`.

**Alternatives considered.** Retrain with the schema in the system turn, which
would cost about 760 extra prompt tokens on every training example and every
inference.

**Reason.** The fine-tune has internalised the schema, which is the point of
doing it: the model needs 83 prompt tokens where the baseline needs 841. Feeding
it a schema it does not need is both slower and measurably worse.

**Result.** Parse rate 0.283 to **0.992**, set equality 0.233 to **0.992**, exact
match to 0.942.

**Reversal.** Remove the `adapter_path` condition on `schema_text` in
`lm/evaluate.py`.

---

## D-014: training runs report to Weights & Biases

**Decision.** Stage 1 passes `--report-to wandb --project-name binman-lm` to
mlx-lm, and the stage 2 DPO loop, which is this project's own code, logs its loss
curve to the same project itself.

**Context.** Marc asked for training runs to be pushed to W&B. mlx-lm supports it
natively; the DPO loop does not go through mlx-lm's trainer and so had to be
instrumented separately.

**Reason.** Both stages belong in the same project or the record of a run is
half missing.

**Safety.** `wandb_available()` checks for a credential in `WANDB_API_KEY` or
`~/.netrc` before enabling reporting, because an uncredentialed run blocks on an
interactive login prompt, which would hang an unattended build. With no
credential, training proceeds unreported.

**Reversal.** Set `BINMAN_WANDB_PROJECT` to change the project, or remove the
`--report-to` arguments to disable it.

---

## D-015: stage 2 preference tuning ships nothing; stage 1 ships alone

**Decision.** Both DPO attempts were rejected and the stage 1 LoRA adapter is what
ships, fused to `models/binman-lm/fused`. This is spec 3.7's third fallback rung:
"if that also fails, ship stage 1 alone and log it."

**Context.** mlx-lm 0.32.0 provides no preference trainer (rung 1), so the DPO
loop was implemented against its LoRA machinery (rung 2). It trained to a
near-zero loss twice and destroyed the model both times.

| Attempt | Learning rate | Steps | Final DPO loss | Generation |
|---|---|---|---|---|
| 1 | 1e-5 | 600 | 0.0018 | collapsed: emitted `ccdccdccdccd…` indefinitely |
| 2 | 5e-7 | 150 | — | degraded: 1 of 6 probes produced a parseable query |

**What made this dangerous.** The per-mode preference win rates measured 0.95 to
1.00 after attempt 1, which reads as a complete success. They were meaningless: a
collapsed policy trivially assigns a higher likelihood to one string than
another, so the metric the preference stage is judged on cannot detect the
failure it is most likely to cause. The adapter would have shipped on the
strength of those numbers.

**The fix that matters is not the learning rate.** `generation_healthy()` now
runs six probe questions through any candidate adapter and requires at least 80%
to produce a query object the real parser accepts, **before** the adapter is
allowed to fuse. An adapter that cannot generate does not ship, whatever its
preference metrics say. The guard was verified against both the collapsed
adapter (0 of 3) and the healthy stage 1 adapter (3 of 3).

**Alternatives considered.** Lower the learning rate again and keep going; add an
explicit KL penalty to the reference policy; reduce to a handful of steps.

**Reason.** Stage 1 already clears every Section 9.5 floor it is measured against
(parse rate 0.992 against 0.99, set equality 0.992 against 0.90), so the
preference stage was an improvement on an already-passing model rather than a
requirement. Spending further compute chasing it, on a hand-rolled DPO loop that
exists only because the library ships none, is not a good trade against the rest
of the build. The ladder exists for this.

**What is lost.** The spec 3.8 per-corruption-mode win rates are not meaningfully
reported: the only numbers produced came from a collapsed model. The behaviours
the preference stage was meant to install (unit discipline, operator direction,
clause completeness, closed-world entities) are therefore trained only by the
supervised stage, which does cover all seven corruption modes as positives.

**Reversal.** Raise `DPO_MAX_STEPS`, adjust `DPO_LEARNING_RATE` and re-run
`lm/train.py`. The guard will still refuse to ship a broken adapter, which is the
behaviour to keep.

---

## D-016: BINMAN-LM serves as base model plus adapter, not as a fused model

**Decision.** Do not ship a fused model. `deploy/serve_lm.sh` runs
`mlx_lm.server --model <base> --adapter-path models/binman-lm/adapters`.

**Context.** Spec 3.7 asks for the adapters to be fused to
`models/binman-lm/fused/`. The fuse completed without error and produced a model
that does not carry the fine-tune. Measured on ten held-out test questions:

| Artefact | Parsed |
|---|---|
| base model + stage 1 adapter | **10 of 10** |
| the fused model | **0 of 10** |

The fused model invents its own output schema
(`{"PDB":"unspecified","Ligand":"ligases",...}`) rather than producing a BINMAN
query object. The base is a 4-bit quantised checkpoint and the fused config still
reports `{"group_size": 64, "bits": 4}`, so the most likely cause is the LoRA
merge against quantised weights.

**Alternatives considered.** Fuse with `--dequantize`, which produces a model
several times larger and changes the numerics the adapter was trained against.
Ship the fused model anyway, which would ship a model that does not work.

**Reason.** The adapter demonstrably works and `mlx_lm.server` loads an adapter
directly, so fusing buys nothing here but a broken artefact. The broken fused
directory was deleted rather than left in place to be picked up by a later
script.

**Reversal.** `pixi run python -m mlx_lm fuse --model <base> --adapter-path
models/binman-lm/adapters --save-path models/binman-lm/fused --dequantize`, then
check it with `generation_healthy()` before letting it serve anything.

---

## D-017: a per-entry work cap on the bridging geometry

**Decision.** Entries whose assembly exceeds
`bridging.max_chain_ligand_pairs` (20,000 chain-ligand pairs) are recorded as
`failed:too_complex:<chains>x<ligands>` and skipped.

**Context.** The bridging test is O(ligand instances x polymer chains). The
catalogue is ordered shortest-first, so the tail of the queue is the enormous
assemblies: 6NK6 has 960 chains and 720 ligand instances, 691,200 pairs, and took
20 minutes on its own. With roughly 1,600 such entries left, the run was
projecting past eight hours for the last 9% of the queue, having already taken
three.

**Alternatives considered.** Let it run. Cap on chain count alone, which would
also exclude legitimate large ternaries. Sample the giant entries.

**Reason.** This is a compute budget, not a scientific claim: nothing is asserted
about whether those assemblies contain glues, and the skip is recorded in the
`entry` and manifest tables so the counts reconcile and the set is re-runnable by
raising the cap. For scale, a CRBN-DDB1 neosubstrate ternary is about 5 chains and
3 ligands, 15 pairs, so the cap sits roughly a thousand times above the structures
the project exists to find.

**Result.** The remaining 17,353 entries finished in **6.2 minutes** at 46 entries
per second, with **235 entries skipped (0.4% of the catalogue)**.

**Reversal.** Raise `max_chain_ligand_pairs` in `config/thresholds.toml` and
re-run with `--retry-failed`.

---

## D-018: each record type names its own default sort direction

**Decision.** `RecordType` carries a `default_direction`, and the UI follows it.

**Context.** Every table defaulted to descending. For `bridge` (sorted on ΔSASA)
and `degron` (sorted on a geometry score) that is right, but `ligase` sorts on
`triage_rank`, which counts upward from the best. The E3 Triage table therefore
opened on rank 638, the worst ligase in the repertoire, with the ranked shortlist
the module exists to produce buried at the far end. `lysine` had the same problem
on distance to the site.

**Reason.** The direction is a property of the field's meaning, so it belongs
beside the field rather than as a single global default.

**Result.** E3 Triage now opens on DCAF15 (rank 1), with VHL fifth and CRBN
thirty-second, which is the shortlist.

**Reversal.** Set every `default_direction` to `desc`.

---

## D-019: the three curated glue databases, and a classification bug they exposed

**Decision.** MGDB, MolGlueDB and MGTbind are wired into `acquire_validation.py`.
MGTbind fetches from direct static URLs; MGDB and MolGlueDB serve their downloads
as client-side blobs, so they use a `file://` route that reads a hand-placed file
from `data/validation/raw/` and the manual step is recorded in the manifest.

**Context.** All three were previously unresolved (Gate G7), which suppressed the
spec 9.1 recall, the misses list and the **novel-bridge set**, the headline
result. MGTbind turned out to be at `mgtbind.pkumdl.cn`, not the idruglab host
the first revision guessed at, and is the only curated source carrying PDB
identifiers: 320 ternary complexes with an entry, both partners' UniProt
accessions and the bridged chain ids.

**Result.** Validation datasets went from 4 of 10 resolved to 8 of 11. Recall,
the misses list and the novel-bridge set all became computable:
**14,260 novel bridges**, which is what the project name promises.

### The bug the recall misses exposed

Diagnosing the first 85 misses split them cleanly: 46 with no bridge detected, 20
not in the catalogue, and **19 where the bridge was found and the ligand was then
classified as furniture**. Among those: 2P1Q, 2P1N and 2P1O, the TIR1 auxin
co-receptor structures. **Auxin (IAC) was classified as a buffer**, because the
name rules match substrings and "INDOLE-3-ACETIC ACID" contains "acetic acid".
The canonical plant molecular glue, dismissed as a buffer by substring match.

Buffers, cryoprotectants and simple salts are small by nature, so a name match
for one of those classes is now rejected on a molecule above
`MAX_FURNITURE_HEAVY_ATOMS` (12), where only the curated seed sets may assign a
furniture class. 539 components changed class, 520 of them out of furniture.

**Recall went 0.734 to 0.772 and the misses fell from 85 to 73.** Artefact
precision fell 0.945 to 0.939, which is the real trade and is reported rather
than hidden: the same change that stops auxin being called a buffer also lets a
few genuine additives through.

### A second bug: the classification was not reaching the Glue Atlas

The geometry worker stamps a class onto each bridge row as it runs, so the
interim file carried whatever the rules said at the time. Re-running
classification updated the ligand table and changed nothing in the Glue Atlas.
`build_atlas.py` now re-derives `bridge.ccd_class` from the ligand table, which is
the single source of truth, and recomputes `novel_bridge` afterwards.
`pipeline/reclassify.py` re-runs classification without redoing the geometry.

**Reversal.** Remove the size guard in `ccd_classes.classify`, or drop the
datasets from the registry.

---

## D-020: Task C was never broken; the evaluation was

**Decision.** No Task C rebalance. The corpus and training are left as they are.

**Context.** Task C measured an abstention rate of 0.00 with a fabrication rate of
0.00, which read as "it never fabricates because it never refuses either, it just
answers with a query object". The planned fix was to over-weight Task C in the
interleaved SFT mix, which spec 3.5 explicitly suggests.

**What it actually was.** Spec 3.7 distinguishes the three tasks by a task tag in
the system turn. `evaluate_abstention` called the shared `generate_one`, which
uses the **`<task>query</task>`** prompt. So the model was being told to write a
query object and then measured on whether it refused. It did exactly what it was
told.

Prompted with `<task>abstain</task>`, the tag it was trained with, on the same
held-out set:

| Metric | Measured with `<task>query</task>` | Measured with `<task>abstain</task>` | Floor |
|---|---:|---:|---:|
| Abstention rate | 0.00 | **1.00** | reported |
| Fabrication rate | 0.00 | **0.00** | 0.00 |

Task C is the strongest part of BINMAN-LM. Given only a ligase pinned it replies
`{"answerable":false,"missing":["glue","target"],...}` and names precisely what is
absent.

**The pattern worth noting.** This is the third defect of the same class in this
build: the model evaluated under a prompt it was not trained with. The first cost
a reported 0.0 on the whole of Task A (D-013), the second was the baseline
comparison, and this one nearly triggered an unnecessary retrain. A model must be
evaluated exactly as it is served, and the task tag is part of that.

**Reversal.** Not applicable: nothing was changed except the evaluation, which is
now correct.

---

## D-021: PROTAC-DB licence accepted by Marc

**Decision.** Marc accepted the PROTAC-DB terms of use himself, on 2026-10-03,
with the reasoning recorded here in his words: the model is not distributed, only
used; the source will be referenced; and the work is not for profit.

**Why this is recorded.** The PROTAC-DB agreement is a formal contract with the
Hou Tingjun group at Zhejiang University. Clause 2.4 restricts both the raw data
and any derivative to the user and their colleagues internally. Accepting it is a
representation the person makes, not something an agent decides, so the decision
and its reasoning belong in writing beside the data it governs.

**What it binds the build to.**

- BINMAN-LM weights are never distributed. They already never ship: the model is
  served from the Studio and `deploy/rsync.sh` excludes `models/`.
- The parsed derivative stays in `data/validation/`, which is gitignored, and
  only computed metrics reach the atlas or the repository.
- PROTAC-DB is cited in `references.bib` and appears in the About tab's reference
  table with its licence stated.

**Reversal.** Delete `data/validation/raw/protacdb_protacs.*` and the parsed
derivative, and re-run `pipeline/acquire_validation.py`. Task B loses its `protac`
and `bivalent_inhibitor` label sources and returns to not buildable.

---

## D-022: Task B classes are not balanced; every unique label is kept

**Decision.** Marc's instruction: "don't pin to the smallest, treat them all as
unique data." Spec 3.4 asks for the classes to be balanced by sampling, and that
is overridden here.

**Context.** Balancing by sampling pins every class to the smallest. The smallest
was `protac` at 38 structural examples, because PROTACs are large and floppy and
almost none are crystallised: 15,502 in PROTAC-DB, 57 with any PDB entry, 32
whose chemical component reaches the atlas. Balancing would have produced a
152-example corpus and discarded roughly 20,000 real curated labels.

**What was done instead.** Two things, together:

1. **Abstract inputs**, which spec 3.4 already allows ("entry title plus ligand
   list, **or a Europe PMC abstract**"). 1,214 abstracts were harvested from the
   curated databases' own cited references, each inheriting the class of the
   database that cited it, so the label still comes from a published source.
   This lifted `protac` from 38 to 598 and `molecular_glue` from 296 to 656: the
   two starved classes, and exactly the ones abstracts can reach.
2. **No class balancing.** Every unique example is kept.

| Class | Structural | With abstracts | In training |
|---|---:|---:|---:|
| crystallisation_artefact | 10,146 | 10,146 | 8,021 |
| native_cofactor | 9,771 | 9,771 | 6,389 |
| molecular_glue | 296 | 787 | 656 |
| protac | 38 | 761 | 598 |

The residual imbalance is about 13 to 1, not the 250 to 1 it would have been
without the abstracts.

**How the imbalance is handled honestly.** It is reported rather than corrected:
`evaluate_triage` returns **per-class precision, recall, F1 and support**, the
full confusion matrix, and the glue-against-PROTAC cell called out as spec 9.5
requires. A macro-F1 on its own would hide which class is failing, so it is
reported as a summary of the per-class figures and never alone.

**Splits.** Grouped by chemical component for structural rows and by article for
abstract rows, so neither a component nor a paper appears on both sides.

**Reversal.** Set a `target_per_class` and restore the sampling block in
`lm/build_task_b.py`.

---

## D-023: ProtCID publishes no bulk interface data

**Decision.** Spec 9.1 packing specificity stays **not computed**, and the reason
is now specific rather than "the download failed".

**Context.** ProtCID's own navigation offers Home, Search, Browse, Statistics,
Help and About. There is no download page: the only bulk files on the site belong
to PDBfam (`PDBfam.txt.gz`, `ChainPfamArch.txt.gz`, the unassigned-sequence
lists), which are Pfam domain assignments per PDB chain, not the interface
clusters. The interface classification that distinguishes a biological interface
from crystal packing is reachable only by browsing or searching one Pfam pair at
a time.

**Alternatives considered.** Scrape the browse interface for the 17,536 entries
that carry a bridge.

**Reason.** That is thousands of requests against an academic server for a
metric that is one of several, and the site offers no bulk route by design. The
honest outcome is to say the resource does not publish what the metric needs.

**Reversal.** If ProtCID publishes a bulk interface table, add it to the registry
with a direct route; the parser slot already exists.

## D-024: the degron geometry filter has no specificity, and Gate G6 is opened

**Decision.** Spec 9.2 is now **measured** against a matched published screen,
and it **fails both floors**: sensitivity 0.656 (floor 0.70) and specificity
0.353 (floor 0.60), ROC AUC 0.441. Gate G6 is opened. The degron module is
relabelled in `FINDINGS.md`, the README and the app as a **hypothesis
generator, not a classifier**, which is what spec 9.2 instructs for exactly
this case. No second threshold adjustment is made.

**Context.** The screens spec 9.2 names (Molecular Cell 2025, Nature
Communications 2025) never resolved. Sievers et al. 2018
(10.1126/science.aat0572) is the same experimental design (one
flow-cytometry screen supplying both arms) and its supplementary data files
are open. Data files S2 and S6 are pooled rather than intersected, per the
instruction to treat each screen as unique data: 5,663 zinc-finger domains,
32 depleted under at least one of thalidomide, lenalidomide, pomalidomide,
CC-122 or CC-220 at FDR < 0.05, and 5,631 assayed in the same screens and not
depleted. 155 were excluded because their protein never reached the AlphaFold
scan; 5,476 matched negatives and 32 positives were scored.

Contingency table (rows the screen, columns the filter): TP 21, FN 11,
FP 3,544, TN 1,932.

**Why no second adjustment.** Spec 9.6 allows one documented threshold
adjustment before G6 and D-010 already spent it: calibrated on five
documented degrons, with no matched negative set in existence at the time,
which is precisely how a filter with no specificity gets built. A sweep of
every attainable cut on `degron_geometry_score` was run to test whether a
second adjustment could help at all: **no cut clears both floors together**,
and the best Youden's J over the whole curve is **0.022**. At cut 0.717 the
filter reaches specificity 0.594 at sensitivity 0.281; to reach specificity
0.60 it gives up all but a quarter of the positives. Moving the cut would be
tuning against the test set for a gain of two points of J.

**The finding is the AUC.** 0.441 is *below* chance: the score ranks degraded
zinc fingers marginally worse than non-degraded ones. The canonical IMiD
neosubstrates are recovered (IKZF3 146-168 at 0.697, ZFP91 400-422 at 0.662,
E4F1 220-242 at 0.678), but twelve non-degraded zinc fingers score above all
three. Recovering the textbook cases while ranking at chance is the signature
of a filter that fires on the fold rather than on the degron: a C2H2 zinc
finger *is* a short antiparallel hairpin with an exposed turn, so the geometry
spec 5.2 describes is a description of the domain family, not of
degradability.

**Alternatives considered.** (a) Spend a second adjustment: rejected on the
sweep above. (b) Add the beta-hairpin glycine as a hard requirement rather
than a scored term: already required, and the 3,544 false positives all carry
it. (c) Withhold the metric as not computed: rejected, because a measured failure
against a published matched set is a result, and spec 9.2 asks for it plainly.

**Reversal.** The module becomes a classifier again only with a feature that
separates degraded from non-degraded zinc fingers *within* the C2H2 family:
the degron sequence context, CRBN-interface complementarity, or the
Zn-coordination geometry, validated on this same matched set. The set is now
wired in as `sievers_zf_screen`, so that test is one command away.

## D-025: MGTbind added to the reference set, and its DOI corrected

**Decision.** MGTbind is now a Crossref-verified reference rather than an
uncited dataset, and its DOI is corrected from `10.1093/nar/gkaf1013` to
`10.1093/nar/gkaf1075`.

**Context.** The acquisition registry carried MGTbind with a citation that
`pipeline/references.py` had never checked, because MGTbind had no Candidate
entry. Adding one and running the Crossref title search returned "MGTbind: a
comprehensive database of molecular glue ternary interactome", Zhu et al.
2025, Nucleic Acids Research, at a different DOI from the one recorded.

**Reason.** The same failure mode as D-014: a DOI string that was never
resolved against the paper it claims to cite. Three of the three curated glue
databases now carry a verified reference, which matters because the Task B
glue label is their intersection.

**Reversal.** None needed. If MGTbind issues a corrected DOI, update the
Candidate and re-run `pipeline.references`.

## D-026: a partial validation run must not truncate results.json

**Decision.** `pipeline.validate` now starts from the sections already on disk
and overwrites only what the current run recomputes. A regression test pins
both directions: a partial run keeps the sections it did not run, and a full
run replaces stale ones rather than merging into them.

**Context.** `run()` built a fresh results dict and wrote it over
`data/validation/results.json`. `--section 9.2`, used three times while
building the Sievers metric, therefore deleted 9.1, 9.3, 9.4 and 9.5 from the
file each time, and `build_about` rebuilt the About tab from the truncated
result. The atlas and the metrics themselves were never wrong: the loss was in
the reporting file, and it was silent.

**Reason.** A validation report that quietly drops the sections it did not
recompute is worse than one that fails loudly, because the About tab and
FINDINGS both read from it. The `--section` flag exists precisely so a single
metric can be iterated on, which is the case where the damage is likeliest.

**Reversal.** None wanted. If a section ever needs clearing deliberately,
delete `results.json` and run the full validation.
