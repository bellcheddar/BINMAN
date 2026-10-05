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
| 2 | 5e-7 | 150 | n/a | degraded: 1 of 6 probes produced a parseable query |

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

## D-027: the 9.1 recall deficit is the contact criterion, and the one permitted adjustment is not spent on it

**Decision.** `bridging.min_heavy_atom_contacts` stays at **3**, the value spec
5.1 criterion 2 mandates. Recall stays at 0.772 against a floor of 0.85, Gate
G6 carries it, and the diagnosis goes in `FINDINGS.md` with the sweep that
justifies leaving the threshold alone.

**Context.** Each of the 73 recall misses was traced. 20 are not in the
catalogue (coverage, not sensitivity), 7 carry bridges classed as something
other than a glue candidate, and 46 ran through geometry and produced no bridge
at all. `data/interim/halves.jsonl` records every half-interface considered, so
the rejection of each can be read off rather than inferred: of the ligand
instances in those 46 that contacted two chains, **48 of 48 were rejected on
the contact count alone, and none on ΔSASA**. The weak side buries 55 to 145
Å², two to six times the 25 Å² floor, at minimum distances of 3.2 to 4.0 Å.

The affected set is not random. It is dominated by the 14-3-3 fusicoccin and
cotylenin glues (3P1O, 3SML, 3SMM, 3SMO, 4FR3, 6HN2, 8AXE, 8BWJ, 8BWX, 8BX3,
8BX4, 8BXI, 8BYF, 8BYO, 8BYY, 8C0K and others), with coronatine at COI1-ASK1
(3OGK) alongside. These are glues that stabilise shallow protein-protein
interfaces over a wide, loose contact area, which is precisely the geometry a
three-atoms-under-4 Å gate rejects.

**Why the adjustment is not spent.** Sweeping the criterion over the recorded
half-interfaces gives recall 0.8469 at a floor of 1, 0.8219 at 2 and 0.7719 at
3. A floor of 1 is the loosest the criterion can take and **still misses 0.85**,
while taking the bridge count from 239,485 to 337,347. Spending spec 9.6's one
adjustment would therefore fail to rescue the metric and would add 97,862
bridges whose false-positive cost cannot be measured, because the
packing-specificity metric that would measure it is the one ProtCID does not
publish (D-023). An adjustment that cannot make the metric pass is not a
fallback, it is just a looser headline number.

**Alternatives considered.** (a) Drop the contact criterion and rely on ΔSASA
alone, which is the physically meaningful quantity: rejected for the same
reason, with the added problem that it deviates from spec 5.1 without a
measurement to justify it. (b) Make the criterion adaptive, requiring three
contacts only where ΔSASA is marginal: rejected as an unvalidated invention
of this project rather than a published rule, which spec 4.1b forbids.

**Reversal.** If ProtCID or an equivalent ever supplies bulk interface
classifications, run the sweep again with packing specificity measured at each
floor. That turns the question from "how much recall do we buy" into "what does
it cost", which is the form in which it can actually be decided.

## D-028: UniProt crosslinks unlock spec 9.4, and the fit fails honestly

**Decision.** Observed ubiquitylation sites are taken from UniProt `CROSSLNK`
annotations as the `digly_sites` dataset. The accessibility component of the
reach window is fitted against them on a protein-level split and scores a
held-out AUC of **0.5458** against a 0.65 floor. **Nothing is written back**,
`fitted = false` stands, no verdict is emitted, and Gate G6 carries it.

**Context.** PhosphoSitePlus requires registration, PLMD is offline and dbPTM
returns 403, so 9.4 had been not computed since the build started. UniProt
annotates an observed ubiquitylation as a Cross-link feature at an exact
residue with an evidence code and a PubMed ID, which is the same observation a
diGly survey reports. It is CC-BY-4.0, needs no account, and was already a
verified project reference. 976 sites on 404 proteins, 718 with direct
experimental evidence; 5,945 SUMO, NEDD8 and ISG15 crosslinks excluded. 403 of
the 404 AlphaFold models were already cached from the degron scan.

**What is fitted.** `min_nz_rel_sasa` only. The Cb-Cb reach boundaries measure
distance from a ligand site, and an AlphaFold monomer with an observed
ubiquitylation site has no ligand site, so the data cannot speak to them. They
stay unfitted rather than being blessed by a fit that never touched them.

**Why nothing is written back.** Spec 5.4 states that the starting values must
not survive into a shipped config unless the fit independently lands on them. A
fit scoring 0.55 has landed on nothing. `fit_accessibility` now gates the
write-back on the spec 9.4 floor rather than on the fit having merely run, so
the failure cannot quietly bless a threshold.

**Why this is still worth having.** A blank became a measured failure, which is
the same trade D-024 made for 9.2 and the one this project is built to prefer.
Metrics not computed fell from 4 to 2. The number also says something: lysine
exposure barely separates an observed ubiquitylation site from an unobserved
lysine, so site selection is driven by E3 recruitment and sequence context
rather than accessibility, which is precisely what the module does not model.

**The negatives are weaker than 9.2's.** UniProt lists sites that were seen, so
an unannotated lysine was not assayed and found unmodified. That bias depresses
rather than inflates the measured AUC, since unlabelled positives sit in the
negative pile, and 0.55 is too low for the bias to explain. PhosphoSitePlus has
the same property, so this is a limit of the question, not of the route.

**Reversal.** A matched set would settle it: a proteome-wide diGly experiment
reporting both detected and confidently undetected lysines. Failing that, the
module becomes predictive only by modelling E3 recruitment, at which point the
reach boundaries can be fitted against ternary-complex geometry rather than
against native ubiquitylation.

## D-029: the model is served from a private adapter repository, not published

**Decision.** BINMAN-LM is served on a HuggingFace ZeroGPU Space that reads a
**private** adapter repository with a token. The weights are not published.

**Context.** Marc asked for ZeroGPU serving. Gate G4 authorised a public code
repository at build start; it did not authorise publishing the model, and the
licence basis for using PROTAC-DB was his own words: "we are not distributing
the model, just using it, so i make the decision this is ok as we will
reference the source and we are not for profit" (D-021). PROTAC-DB's terms
permit internal use including derivatives and prohibit redistribution. The
adapter is trained on Task B data derived from it, so a public weights
repository would be redistribution and would contradict the basis the data was
accepted on.

**Reason.** A private adapter repository that only the Space can read serves
inference without publishing weights, which is the thing the licence turns on.
The sources are cited in the Space README, the repository README and
`data/validation/MANIFEST.md`.

**What is served.** The three text jobs only: query translation, evidence
triage and abstention. The atlas is not served. It is 142 MB and several
source datasets carry licences that do not permit redistribution, so the Space
shows what the model produces and the repository shows what the pipeline
computes.

**The conversion risk is not resolved by this decision.** The adapter is
trained with mlx-lm against a 4-bit quantised base and must be applied to a
16-bit base on CUDA. `lm/export_hf.py --verify` runs the real held-out test
questions through the converted adapter and prints the metrics
`lm/evaluate.py` reports, so the two can be compared. If the converted adapter
scores materially lower, the options are to train a LoRA against the 16-bit
base for serving or to serve from Apple hardware. Shipping a degraded adapter
beside the MLX numbers is not one of them.

**Reversal.** If the PROTAC-DB class were rebuilt from a source that permits
redistribution, or dropped, the adapter could be published. Task B would then
be three classes rather than four, and the glue-against-PROTAC confusion that
the confusion matrix exists to expose would no longer be measurable.

## D-030: the adapter is published, and the term it runs against is named

**Decision.** The BINMAN-LM adapter is published to a **public** HuggingFace
model repository and served from a public ZeroGPU Space. This supersedes D-029,
which had it private.

**Context.** Marc: "the huggingface can go public as the input data source is
not shared." That premise is correct as far as it goes, and it is not the thing
the restriction turns on, which is worth recording rather than smoothing over.

**The term.** PROTAC-DB ships under "internal use only, **derivatives
included**; redistribution prohibited" (Hou group terms, 2024-09-29). A LoRA
adapter trained on Task B data derived from PROTAC-DB is a derivative. The
clause therefore reaches the weights whether or not the source CSV is shared,
so not sharing the data does not by itself clear it. D-021 accepted the data on
the basis "we are not distributing the model, just using it"; publishing the
model is a change to that basis, not an application of it.

**Reason it proceeds anyway.** This is Marc's project, his licence call, and he
made it after the term was put in front of him twice. The work is
non-commercial, every source is credited with a DOI in the repository README,
the Space card and `data/validation/MANIFEST.md`, and no source dataset is
redistributed. The exposure is his to carry and he has chosen to carry it.

**What would remove the question.** Rebuilding Task B's `protac` class from a
source that permits redistribution, or dropping it. Task B would become three
classes, and the glue-against-PROTAC confusion that the confusion matrix exists
to expose would stop being measurable, which is a real cost rather than a
formality: that cell is where the model's errors concentrate.

**Reversal.** Making the repository private again restores D-029 exactly. The
Space reads `HF_TOKEN` if it is present, so nothing in the code changes.

## D-031: the base model is Qwen Research licensed, not Apache-2.0

**Decision.** The Space card and the adapter model card both declare
`license: other` with `license_name: qwen-research`, the adapter repository
ships the Agreement as `LICENSE` and the required attribution as `NOTICE`, and
both cards state that use is non-commercial only.

**Context.** The deployment scaffold declared `license: apache-2.0` on the
Space. That was wrong. Most Qwen2.5 sizes are Apache-2.0, but **3B and 72B are
not**: `Qwen/Qwen2.5-3B-Instruct` carries `license: other` on the Hub and ships
the **Qwen RESEARCH LICENSE AGREEMENT**, which grants rights "FOR
NON-COMMERCIAL PURPOSES ONLY" (section 2a). The error was caught by checking
the base model's own metadata before writing the model card rather than by
assuming the family licence.

**What section 3 requires of a redistributed derivative**, all now satisfied:
give recipients a copy of the Agreement (3a, `LICENSE`); carry prominent
notices of what was changed (3b, `NOTICE` names the LoRA rank, layers, targets
and the MLX-to-PEFT conversion); retain the attribution string "Qwen is
licensed under the Qwen RESEARCH LICENSE AGREEMENT, Copyright (c) Alibaba
Cloud. All Rights Reserved." in a Notice file (3c); own copyright may be added
(3d).

**Reason it is compatible.** The Agreement permits distributing derivative
works, so publishing the adapter is allowed where publishing it under a claimed
Apache-2.0 would have misrepresented the terms to anyone downstream. The
non-commercial restriction matches Marc's own stated basis for the project,
"we are not for profit" (D-021, D-030), so nothing about the project changes.
What changes is that the restriction is now stated to people who might reuse
the weights, rather than being silently dropped.

**Reversal.** Serving a base whose licence is Apache-2.0 would remove the
restriction. Qwen2.5-7B-Instruct is Apache-2.0 and would need a retrain rather
than a relabel, so this is a real choice and not a metadata edit.

## D-032: the MLX-to-PEFT conversion silently randomised 20 of 36 layers

**Decision.** `lm/export_hf.py` writes `layers_to_transform` and
`layers_pattern` into the PEFT config, derived from the layer indices actually
present in the adapter, and refuses a non-contiguous range rather than guessing.
Verification runs in a separate process, and a non-zero exit from it fails the
export.

**Context.** mlx-lm's `--num-layers 16` trains the **last** 16 layers, so on
36-layer Qwen2.5-3B the adapter covers layers 20 to 35 and nothing below. PEFT
matches `target_modules` against every layer, so the first conversion built
LoRA weights for layers 0 to 19 as well, found nothing for them in the
checkpoint, and left them **randomly initialised**. PEFT warns and continues:
the model loads cleanly, reports no error, and generates from twenty layers of
noise. Nothing downstream would have caught it, and it would have shipped to a
public Space with the MLX metrics on the card.

**How it surfaced.** Only by running the real held-out questions through the
converted adapter. The conversion itself reported 224 tensors, rank 8, alpha
160 and 16 layers, all correct, because the tensors it wrote were right. What
was wrong was the config describing where they go.

**Two smaller faults found alongside.**

* The first verification run appeared to pass with exit code 0. It had
  segfaulted: the command was piped through `tail`, so the shell reported
  `tail`'s status. A pipeline hides the exit code of every stage but the last,
  which is worth remembering whenever a check "passes" without output.
* Converting with safetensors' numpy backend and then loading a torch model in
  the same interpreter segfaults on this machine. Both work alone and in either
  import order; only the sequence crashes. Verification therefore re-execs, via
  `--verify-only`, which also means it tests the artefact on disk rather than
  anything `convert` is still holding.

**Reason this matters beyond the bug.** The quantisation-transfer risk recorded
in D-029 was the known unknown, and it is not what nearly shipped. The failure
was a config field that no amount of reading the conversion report would have
revealed. A conversion is not verified by inspecting what it wrote; it is
verified by running the model.

**Reversal.** None wanted. If mlx-lm ever trains a non-contiguous layer set,
the export fails loudly and the config needs a `layers_to_transform` list
rather than a range.

## D-033: LoRA rank never reached mlx, so every round so far trained at rank 8

**Decision.** `lm/train.py` now writes a `lora_config.yaml` per run and passes
it with `--config`, so `LORA_RANK` changes the training rather than only the
label. The constant is corrected to **8**, which is what rounds 01 to 06
actually used, and rank, layers, base model and batch size are exposed as CLI
arguments for the overnight sweep.

**Context.** `mlx_lm lora` has no `--lora-rank` flag. Rank, scale and dropout
are only reachable through a YAML config file given to `-c/--config`, and the
default rank is 8. `LORA_RANK = 16` appeared in the W&B config, in the run
notes and in `training.json`, and never in the training command. Confirmed
directly: the round 05 adapter's own `adapter_config.json` records
`"rank": 8`, and a two-iteration smoke test with `rank: 32` in a YAML config
produced `lora_a` of shape `[11008, 32]`.

**Consequence.** Every published figure stands, because the model that produced
them is the model that was trained. What was wrong is the recorded
hyperparameter: W&B says rank 16 for rounds 01 to 06 and the truth is 8. The
W&B configs are not rewritten, because editing a logged config to match a later
discovery is worse than a note that says which value was real.

**Why it matters tonight.** Marc asked whether more layers would help. Rank is
the other half of LoRA capacity and it was pinned at the library default the
whole time. Rank 8 over 16 layers is a very small number of trainable
parameters for three tasks, one of which has four classes, so the overnight
sweep varies rank as its own round rather than treating depth as the only
capacity knob.

**Reversal.** None wanted. If mlx-lm ever adds a `--lora-rank` flag the YAML
can go, but the YAML is also a per-run artefact beside the adapter, which is
better provenance than a flag in a shell history.

## D-034: Task B was never evaluated, and when wired in it sampled the wrong rows

**Decision.** `evaluate_triage` is now reachable and called from `run()`, and
the triage test set is sampled **stratified at 60 per class with a fixed seed**
rather than taken from the head of the file.

**Context, first fault.** `evaluate_triage` sat below the
`if __name__ == "__main__"` guard in `lm/evaluate.py`. Python never reached the
definition before `main()` ran, so the function was not merely uncalled, it was
unreachable: wiring it into `run()` raised `NameError`. Every round from 01 to
06 was therefore evaluated on Task A and Task C alone, and the 0.8956 macro-F1
in `FINDINGS.md` came from importing the module in a separate script, which is
why that detour was necessary without it being obvious why.

**Context, second fault.** Once reachable, the first wiring took
`triage_samples[:limit]`. The test set is 4,087 rows holding 2,692 native
cofactor and 1,242 artefact against **87 PROTACs and 66 glues**, so the head of
the file has support 68/5/161/6. Measured that way round 06 scored macro-F1
**0.9815** against round 05's 0.8956, which reads as a large improvement and is
an artefact of five glue examples. On the balanced sample it is **0.8862**.

**Reason.** Macro-F1 over an unbalanced slice flatters a model on exactly the
two classes this project exists to find. The sample is now fixed by seed so
every round sees the same 240 rows: rounds are compared with each other, and a
sample that moves between them measures the sample.

**What it changes.** Nothing already published: `FINDINGS.md` carries 0.8956,
measured on a balanced 240, which is the comparable number. What changes is
that the comparison is now reproducible from the repository rather than from a
script that no longer exists.

**Reversal.** None wanted. `TRIAGE_PER_CLASS` and `TRIAGE_SEED` are named
constants; changing either invalidates comparison with the rounds above and
should be recorded here if it ever happens.

## D-035: 32 LoRA layers is the lever; and never edit a running bash script

**Decision.** Depth is the capacity knob that matters. Round 07 at 32 layers
beats the 16-layer control on every Task B class and reaches a perfect Task A.
The shipped adapter should be a 32-layer one unless rank 32 or the combination
beats it.

**Result.** Balanced 240-sample triage set, same seed both rounds:

| | round 06, 16 layers | round 07, 32 layers |
|---|---|---|
| Task B macro-F1 | 0.8862 | **0.9336** |
| molecular_glue F1 | 0.849 | **0.958** |
| molecular_glue recall | 0.750 | **0.950** |
| protac F1 | 0.944 | 0.975 |
| glue called protac | 6 | 1 |
| Task A set equality | 0.9833 | **1.000** |

The gain concentrates on `molecular_glue`, the rarest class in the corpus and
the one the project exists to find. Round 06 had already shown that eight times
the data exposure changed nothing, so the bottleneck was never coverage: 16
layers at rank 8 could not represent the decision boundary, and 32 layers can.
Training cost 221 minutes against roughly 170 for 16 layers.

**The process failure.** `lm/overnight.sh` was edited **while bash was
executing it**, to fix how results were captured. Bash parses a function body
once but reads top-level commands lazily by byte offset, so growing the file
from 4,210 to 4,419 bytes left the interpreter holding a stale offset into a
file that had moved underneath it. The next top-level command after the round
08 call would have been read from the wrong position, which would have lost the
32B round and possibly executed a fragment of a line as a command.

Caught before that point and fixed exactly: `git checkout lm/overnight.sh`
restored the file byte-for-byte to its launch state, realigning every offset.
The capture fix is kept out of tree until the sweep ends, and the affected rows
are backfilled from `data/interim/lm_eval.json` by hand, which costs nothing
because the evaluations themselves are on disk.

**The rule.** A long-running shell script is not a file to improve in place. If
it needs changing mid-run, copy it, change the copy, and start the copy after
the current run drains.

**Reversal.** None. The capture fix is reapplied once the driver exits.

## D-036: depth and rank buy the same thing, and restoring a running script made it worse

**Decision.** Round 09 combines both knobs, 32 layers at rank 32, and is run
from a new file rather than from the edited sweep. The 32B round is dropped for
now: the combination is the higher-expected-value run and fits before morning,
where 32B does not.

**The result.** Each knob alone lifts Task B macro-F1 by roughly the same
amount, from the control's 0.8862:

| round | config | macro-F1 | molecular_glue F1 | glue recall | train |
|---|---|---|---|---|---|
| 06 | 16 layers, rank 8 | 0.8862 | 0.849 | 0.750 | ~170 min |
| 07 | **32 layers**, rank 8 | **0.9336** | 0.958 | 0.950 | 221 min |
| 08 | 16 layers, **rank 32** | **0.9293** | **0.967** | **0.983** | 173 min |

Width is the cheaper route: rank 32 reaches within 0.004 of 32 layers for 48
fewer minutes, and it has the best `molecular_glue` F1 of any round with zero
glue-called-protac errors. Neither saturated, so the combination is untested
and is the obvious next point.

**The process failure, part two.** D-035 recorded that `lm/overnight.sh` was
edited mid-run and that `git checkout` restored it byte-for-byte. The restore
was the wrong remedy and caused the thing it was meant to prevent. Bash had
already read and executed the round 08 line from the 4,419-byte version; when
that call returned it sought the next command at an offset computed against
that larger file, and by then the file was 4,210 bytes again. The offset landed
back inside the round 08 region and the driver re-executed round 08 instead of
advancing to the 32B section, which it would have done forever.

Caught from the progress log showing `START round08-rank32` twice. The driver
and its duplicate training were stopped, round 08's completed evaluation was
backfilled from `data/interim/lm_eval.json`, and round 09 was launched from a
new file.

**The corrected rule.** Once a shell script is running, neither edit it nor
restore it. Leave the file completely alone and start any change as a separate
file. Editing moves every later byte offset; restoring moves them back under an
interpreter that has already advanced past them, which is just as bad.

**Reversal.** The 32B round is still worth measuring and
`lm/measure_throughput.py` exists for it. It needs a window where nothing else
wants the GPU, which is a daytime decision rather than an overnight one.

## D-037: quantisation transfer is clean; the ZeroGPU Space is not yet serving

**Decision.** Round 07 is the shipped adapter. Its conversion to PEFT is
verified against the real held-out questions and matches the MLX numbers. The
HuggingFace Space is **not serving it yet** and that is recorded as open rather
than glossed.

**Quantisation transfer, the risk D-029 named.** The adapter is trained with
mlx-lm against the 4-bit `mlx-community/Qwen2.5-3B-Instruct-4bit` and served
against 16-bit `Qwen/Qwen2.5-3B-Instruct`. Nothing guaranteed the correction
would transfer. It does: zero missing adapter keys, Task A parse 1.000 and set
equality 1.000 against MLX's 0.983 and 1.000, Task C abstention 1.00 and
fabrication 0.00. The published metrics therefore describe the served model.

**The Space.** Three configurations were tried and each failed differently:

1. Model built inside the `@spaces.GPU` function, no prefetch: the first
   request has to pull six gigabytes inside the GPU time budget and fails with
   an error carrying no traceback.
2. Model built at module scope: `RuntimeError: No CUDA GPUs are available`,
   raised from inside spaces' torch patching, because PEFT touches CUDA while
   attaching and the main process may not initialise it.
3. Prefetch at import plus build inside the GPU function, which is the
   combination the first two imply: the Space reaches RUNNING with a clean log
   and requests still return null with nothing logged.

The adapter is not the cause: the same artefact answers correctly on this
machine, and round 05's smaller adapter served correctly from this Space
earlier in the session. The remaining candidates are a ZeroGPU quota exhausted
by the night's restarts, or a peft version on the Space that handles
`layers_to_transform` differently from the local 0.21.2. Neither is diagnosable
from the logs the Space exposes.

**Reason for stopping here.** The model is the deliverable and it is verified.
Chasing a hosted runtime whose errors are invisible is a poor use of the hours
before the morning, and the next step needs `HF_DEBUG=1` on the Space and a
look at the ZeroGPU quota page, which is a daylight task.

**Reversal.** Round 05's 16-layer adapter did serve from this Space. Restoring
it would give a working demo of a worse model, which is the wrong trade: the
repository and the model card carry the real numbers.

## D-038: the capacity knobs do not compound, and round 07 ships

**Decision.** **Round 07 (32 layers, rank 8) is the shipped adapter.** The
sweep is closed. The 32B round is not run.

**The sweep, all on the same balanced 240-sample triage set and seed:**

| round | config | Task B macro-F1 | glue F1 | Task A set eq | train |
|---|---|---|---|---|---|
| 06 | 16 layers, rank 8, batch 4 | 0.8862 | 0.849 | 0.9833 | ~170 min |
| **07** | **32 layers, rank 8, batch 4** | **0.9336** | 0.958 | **1.000** | 221 min |
| 08 | 16 layers, rank 32, batch 4 | 0.9293 | 0.967 | 0.9917 | 173 min |
| 09 | 32 layers, rank 32, **batch 2** | **0.8711** | 0.869 | **1.000** | 133 min |

Either knob alone lifts macro-F1 by about 0.045. **Both together lose 0.015
against the control**, and the loss is concentrated exactly where the single
knobs gained: `molecular_glue` F1 falls from 0.958 and 0.967 back to 0.869, and
`protac_called_glue` jumps from 1 and 3 to 9.

**The comparison is confounded and that has to be said.** Round 09 ran at batch
2 with gradient checkpointing because at batch 4 it exhausted swap and fell to
roughly three iterations a minute. So it differs from rounds 07 and 08 in two
ways, not one: more capacity and a smaller batch. 14,152 iterations at batch 2
is one epoch where the others saw two, though round 06 had already shown that
eight times the exposure changes nothing, which makes batch size rather than
epochs the likelier confound. Smaller batches mean noisier gradients, and a
model with four times the trainable parameters is the one least able to absorb
that.

**Why it is not re-run clean.** A batch-4 round at this capacity needs memory
the machine does not have, which is what the first attempt demonstrated. The
honest options were a confounded result or no result, and a confounded result
that is labelled is worth more. Task A reached 1.000 in round 09 as it did in
round 07, so the extra capacity was not simply wasted; it did not help the task
that still had headroom.

**What ships.** Round 07: Task B macro-F1 0.9336, Task A set equality 1.000,
Task C abstention 1.00 with fabrication 0.00. It takes every metric that moves,
clears the 0.85 Task B floor and the 0.90 Task A floor, and its PEFT conversion
is verified against the held-out questions (D-037).

**Reversal.** Round 09 is on disk. If the machine ever has the memory for a
batch-4 run at 32 layers and rank 32, that is the clean experiment and it is
one command.

## D-039: sequence beats geometry on the degron, and the module still ships relabelled

**Decision.** The sequence model is reported in `FINDINGS.md` and wired into
spec 9.2 as a measured comparison. **Gate G6 stays open and the Degron Scan
keeps its hypothesis-generator label.** The shipped `degron_geometry_score` is
not replaced.

**What was tested.** D-024 named the reversal condition: a feature that
discriminates within the C2H2 family. `pipeline/degron_sequence.py` anchors
each assayed zinc finger on its C2H2 motif, aligns to 23 positions, encodes
each position as eight overlapping chemical groups, and fits an L2 logistic
regression evaluated by repeated stratified group k-fold so no gene spans a
split.

| | geometry | sequence |
|---|---|---|
| ROC AUC | 0.441 | **0.637** (sd 0.089) |
| best Youden's J | 0.022 | **0.214** |
| clears sens 0.70 and spec 0.60 together | no | **no** |

**Why the permutation null was necessary.** 32 positives, 184 columns, and
zinc-finger paralogues that grouping by gene cannot separate: ZN184, ZN276 and
ZN653 are different genes with near-identical domains. A model can score above
0.5 on family structure alone. Shuffling labels through the same grouped
splitter gives a null of 0.510 (sd 0.071, p95 0.615), and the observed 0.637
clears that by 1.7 standard deviations. Without that null the headline would
have been "sequence lifts AUC to 0.64" with no way to know how much of it was
the splitter.

**Why the module is not re-based on it.** It fails the same floors by the same
kind of margin, and swapping a geometry score the UI explains for a logistic
regression over chemical groups would trade an interpretable failure for an
opaque one. The score shipped in the atlas stays; the sequence result is
reported as what the reversal condition actually buys.

**What would clear the floors.** Not the substrate alone. The classic G-loop is
necessary and not sufficient: IKZF3 `FQCNQC-G-ASF` is degraded, ZFP30
`YECKEC-G-KAF` is not, and ZN184 carries almost exactly ZFP30's motif and is.
Separating those needs complementarity to the CRBN interface, which is a
ternary-complex calculation BINMAN does not do.

**Reversal.** `pipeline/degron_sequence.py` takes the matched set and a feature
matrix. Adding CRBN-interface features to it is the experiment, and the
grouped, permutation-tested harness is already there to judge them.

## D-040: ZeroGPU grants this Space no GPU, and the fault is not in the model path

**Decision.** The Space stays on ZeroGPU and stays non-functional until Marc
decides between waiting for quota, paying for dedicated hardware, or dropping
to CPU. Nothing further is changed in the application code, because the
application code is not what is failing.

**How it was isolated.** Three configurations each failed differently and each
looked like a code problem (D-037). The decisive test was a `@spaces.GPU`
function that does nothing but report `torch.cuda.is_available()`. It fails
with the same `event: error, data: null` as the model endpoints. A no-op cannot
have a model bug, a quantisation bug or a peft version problem, so the fault is
the GPU allocation itself.

Along the way the GPU worker was made to return its own traceback as the
answer, because a failure inside it reaches the caller as a null error and
never appears in the Space log. Even that did not fire, which places the
failure before any user code runs.

**What it is not.** Not the adapter: the same artefact answers correctly on
this machine and round 05's smaller adapter served from this same Space earlier
in the session. Not quantisation transfer: that was separately verified in
D-037. Not the ZeroGPU code pattern: a no-op fails too.

**What it probably is.** A ZeroGPU quota consumed by the night's repeated
restarts and probes, which resets on a cycle this project cannot see from the
API. The `whoami-v2` endpoint returns no quota field for this token.

**The options, which are Marc's.**

1. Wait for the quota cycle. Costs nothing, fixes itself, unknown delay.
2. Dedicated hardware. `t4-small` is $0.40/hour and would serve this model
   comfortably. It is his account and his money, so it is not switched without
   asking.
3. `cpu-basic`, which is free. A 3B model in float16 fits in 16 GB but
   generates at a few tokens a second: triage and abstention would answer in
   seconds, Task A's longer outputs in minutes. A usable demo of two tabs out
   of three.

**Reversal.** The diagnostic GPU endpoint stays in the Space until it is known
good, because it distinguishes "no GPU" from "model broken" in one click, which
is the distinction that cost the most time here.

## D-041: D-040 was wrong. The Space worked; the test harness did not

**Decision.** D-040 is superseded. The Space serves round 07 on ZeroGPU and has
been verified end to end. No hardware change is needed and none was made.

**What D-040 claimed.** That ZeroGPU was granting this Space no GPU, on the
evidence that a `@spaces.GPU` function doing nothing but reporting
`torch.cuda.is_available()` failed with `event: error, data: null`.

**What was actually wrong.** The probe. Every call in that investigation went
through hand-rolled `curl` against the Gradio SSE endpoint, parsing the event
stream with `grep`. That parsing was broken, and a broken parser returns the
same null for a working endpoint as for a failing one. Calling the identical
endpoint with `gradio_client` returns:

    cuda available=True device_count=1 name=NVIDIA RTX PRO 6000 Blackwell

The GPU was there the whole time, including for every "failure" recorded in
D-037 and D-040.

**The lesson, which is the point of this entry.** A no-op test is only as good
as the harness carrying it. The smoke endpoint was built to separate "no GPU"
from "model broken" and it did its job faithlessly, because it was read through
the same broken channel as everything else. When a diagnostic and the thing it
diagnoses share a dependency, the diagnostic cannot clear that dependency. The
client library existed throughout and was skipped twice because installing it
hit a missing `pip` in the uv virtualenv, which was a two-minute problem
treated as a dead end.

**Verified now**, round 07 on the live Space:

| probe | answer | |
|---|---|---|
| PEG at a lattice contact | `crystallisation_artefact` | correct, and round 05 got this wrong |
| pomalidomide bridging CRBN and IKZF1 | `molecular_glue` | correct |
| FAD in a Rossmann pocket | `native_cofactor` | correct |
| bivalent degrader with a PEG linker | `molecular_glue` | **wrong**, should be `protac` |
| affinity in nanomolar | structured abstention with a reason | correct |
| bridging balance above 0.8 | valid query object | correct |

The PROTAC miss is one anecdote against a measured `protac` F1 of 0.975 and is
not treated as a metric. It is recorded because round 05 answered it correctly
and round 07 does not, which is worth watching if more cases appear.

**Reversal.** The diagnostic GPU endpoint stays, and so does the CPU fallback
in `_device_and_dtype`, because neither costs anything and both are now
correct rather than load-bearing.

## D-042: three routes to the degron AUC, one ceiling at 0.64

**Decision.** The degron ceiling is reported as measured and the module is not
re-based. Gate G6 stays open.

**What was tried, beyond D-039's classifier.**

| approach | AUC | sd |
|---|---|---|
| geometry alone, the shipped score | 0.441 | n/a |
| sequence, classifying the 32 FDR-significant labels | **0.636** | 0.082 |
| sequence, regressing on continuous fold depletion | 0.605 | 0.124 |
| sequence plus geometry as a feature | 0.638 | 0.085 |
| permutation null | 0.515 | p95 0.610 |

**The regression result is the informative one.** It should have won: the
binary labels use 32 of 5,663 domains where the continuous depletion uses all
of them, across three drugs and three replicates. It loses, and with half again
the variance. Most domains sit at noise around a fold depletion of 1.0, and the
FDR labels have already separated signal from that noise. Regressing on the raw
values mostly fits the noise, so more data was less information.

**Geometry contributes nothing even as a feature.** Adding it to 184 sequence
columns moves the AUC by 0.0015, a fifth of one standard deviation. That is a
stronger statement of D-024 than the original: the geometry is not weakly
informative about degradability, it is uninformative, and it survives in the
atlas only as a descriptor of the C2H2 fold.

**Where the remaining signal is.** Not in the substrate. The G-loop is
necessary and not sufficient, and the counterexamples differ by one or two
residues. What separates IKZF3 from ZFP30 is how each sits against the CRBN
surface, which is a ternary-complex calculation. Any further gain needs that,
or needs the matched screen to grow well beyond 32 positives.

**Reversal.** `pipeline/degron_sequence.py` holds the matched set, the feature
builder, the grouped splitter and the permutation null. A CRBN-interface
feature drops into it as another column.

## D-043: the droplet's convention is not the one deploy/ assumed

**Decision.** BINMAN deploys to `/opt/binman` with a dedicated `binman` service
user, a `binman-web.service` unit and nginx proxying `binman.mdeller.com` to
127.0.0.1:8090. `deploy/provision.sh` does the whole thing idempotently and
refuses without `BINMAN_DEPLOY_CONFIRM=yes`, like `rsync.sh`.

**Context.** `deploy/binman.service` and `deploy/rsync.sh` were written from
the spec against `/srv/binman` on port 8080, before anyone had looked at the
host. The host does not work that way. Its seventeen other apps live under
`/opt/<name>`, each with its own system user, a `.venv` inside the app
directory, a `<name>-web.service` unit and an nginx vhost proxying to a local
port. Deploying to `/srv` would have worked and would have left BINMAN as the
one app nobody else's tooling understands.

**What was added.** `wsgi.py`, because the unit convention is `wsgi:app` and
`app/__init__.py` only exposes a module-level `app`.
`deploy/binman-web.service` and `deploy/nginx-binman.conf` matching the house
layout, with the vendored front-end served immutable, trimmed structures
revalidating daily, and the shared `vhost` access-log format the launcher's hit
counter reads. `deploy/provision.sh` to run it.

**Port 8090** was chosen to sit clear of the range the existing apps use. It
should be confirmed free before the first run; the check could not be made
because SSH stopped answering (below).

**RESOLVED, see the end of this entry.** The cause was self-inflicted
connection pressure and the fix is multiplexing. What follows is the
investigation as it stood before that, kept because two of its conclusions were
wrong and the shape of the error is worth keeping.

**SSH is intermittently unusable from the Studio, and the cause is not
established.** Two claims were made here and both were wrong. The first was
fail2ban, inferred from a failed `deploy@mdeller.com` attempt followed by
timeouts; Marc confirmed fail2ban is not installed and nothing is firewalled.
The second was an implied network block, which the evidence contradicts.

What is actually measured:

* TCP to port 22 **connects**: `ssh -v` reports "Connection established", then
  the session dies with `ssh_dispatch_run_fatal: Operation timed out`. The
  failure is in the handshake, not the connect.
* Two complete SSH sessions succeeded earlier, returning real output from
  `systemctl` and `cat`.
* Outbound port 22 from this machine is fine: `ssh -T git@github.com`
  authenticates over port 22 in the same minutes the droplet stalls.
* The droplet is healthy: `mdeller.com` and `podium.mdeller.com` both serve
  HTTP 200 throughout.
* `IPQoS=none`, `IPQoS=throughput` and forcing `aes128-ctr`, the usual
  middlebox workarounds, change nothing.
* It is not data-volume dependent: `ssh root@host true`, with no output at all,
  fails the same way.
* `en0` is at the standard 1500 MTU.

Marc's own observation is the most useful datum and is recorded rather than
explained away: these deploys worked from his MacBook and have only misbehaved
since moving to the Studio. That points at something machine- or path-specific
rather than anything on the droplet, which is consistent with everything above
and is as far as the evidence goes.

**Reversal.** Everything is staged. When SSH is usable, the deploy is
`BINMAN_DEPLOY_CONFIRM=yes ./deploy/provision.sh`, which is idempotent and
safe to retry.

## D-044: two "32B" rounds silently trained the 3B

**Decision.** `stage_one`, `run_name` and `next_round` resolve the base model
and run stem at **call time** rather than taking them as default arguments.

**The bug.** `def stage_one(iters, batch_size, model: str = BASE_MODEL, ...)`
binds `BASE_MODEL` when the function is **defined**, not when it is called.
`main()` reassigns the module global in response to `--base-model`, and the
default had already captured the old value, so the override never reached the
training command. `run_name(stem: str = RUN_STEM)` and
`next_round(stem: str = RUN_STEM)` had the same defect, which is why the run
directory was named `binman-qwen-2.5-3b-4bit-round13` for a 32B round.

**What it cost.** Rounds 12 and 13 both ran `--model
mlx-community/Qwen2.5-3B-Instruct-4bit` while reporting themselves as 32B.
Round 12 was killed for other reasons; round 13 reached 4,200 iterations before
the discrepancy was noticed. About 35 minutes of training, and a result that
would have been reported as "32B is no better than 3B" when no 32B had run.

**How it surfaced.** Arithmetic, not an error. The run was doing roughly 130
iterations a minute when `lm/measure_throughput.py` had measured the 32B at
13.03. A tenfold gap between the measured rate and the observed one is not a
variance; it is a different model. The run directory carrying the `3b` slug
confirmed it, and the process command line settled it.

**Why the throughput measurement did not catch it.**
`lm/measure_throughput.py` builds its own command and passes `--model`
explicitly, so it genuinely measured the 32B. Only the training path had the
defect, which is exactly the shape that defeats a pre-flight check: the thing
that measures and the thing that runs took different routes to the same
setting.

**Reversal.** None wanted. The guard is the arithmetic: a round whose observed
iterations-per-minute does not match its measured throughput is not running the
model it claims.

## D-045: the SSH failure was self-inflicted, and BINMAN is deployed

**Decision.** `~/.ssh/config` multiplexes connections to the mdeller.com
droplet. BINMAN is live at **https://binman.mdeller.com** and listed on the
mdeller.com launcher. Gate G3 is closed.

**The cause.** Not fail2ban (D-043's first claim), not a network block (its
second), not MTU. A deploy opens many short ssh sessions; each timed-out
attempt leaves a half-open **unauthenticated** connection for `LoginGraceTime`,
120 seconds by default, and sshd's `MaxStartups` of `10:30:100` then drops new
connections while those sit there. Retrying refills the queue faster than it
drains, so the outage sustains itself. Every "failure" after the first few was
produced by the attempt to diagnose the failure.

**The evidence that settled it.** 200 seconds of complete silence, then a
single attempt: connected immediately, `uptime` reporting the droplet had been
up 11 weeks. Nothing was ever wrong with the host.

**Measured, same host, same minutes:**

| configuration | success |
|---|---|
| defaults, retrying hard | 0/15 |
| defaults | 0/6 |
| forced small handshake (ed25519, curve25519, chacha20) | 2/6 |
| **ControlMaster multiplexing** | **10/10** |

The small-handshake result is why MTU looked plausible and is the trap: smaller
packets occupy a `MaxStartups` slot for less time, so they succeed more often
without the cause having anything to do with packet size.

**The deploy.** The droplet's convention is `/opt/<name>` with a dedicated
service user, a `.venv`, a `<name>-web.service` unit and nginx proxying a local
port, not the `/srv` layout `deploy/` assumed (D-043). `deploy/provision.sh`
does it idempotently: user, directories, rsync, venv, systemd, nginx, certbot.
Two workers rather than three, because the host has 3.8 GB across thirteen
other apps; BINMAN added about 100 MB and every neighbour stayed up.

Verified live: `/`, `/degron/`, `/e3/`, `/about/` and `/lens/` all 200, TLS
issued to 2027-01-02, `binman-web` active.

**One real bug found by the first run.** `rsync` does not create nested parent
directories, so `/opt/binman/data/atlas` failed until `provision.sh` created
the parents up front.

**Carried into the skill.** `marcs-vibe-coding` now holds the multiplexing
config, a floor of 150 seconds between retries, `ssh -T git@github.com` as the
control for "is outbound 22 working", and the warning that `nc -z` is not a
reliable probe from a sandboxed shell. Alongside it, the lesson from the Space:
a diagnostic cannot clear a dependency it shares with the thing it diagnoses.

## D-046: the pooled label was the mistake; pomalidomide clears the 9.2 floors

**Decision.** Degron prediction is reported **per compound**. Pomalidomide
reaches AUC 0.826 and an operating point satisfying both spec 9.2 floors. Gate
G6 stays open and the shipped `degron_geometry_score` is unchanged, for the
reasons below.

**The finding.** Every earlier attempt asked which zinc fingers are degraded by
*any* IMiD. The compounds do not share substrates, so the union label asks a
model to learn incompatible classes at once. Splitting it:

| label | positives | AUC | vs null | Youden J | clears floors |
|---|---:|---:|---:|---:|---|
| pooled | 32 | 0.636 | +1.7 sd | 0.214 | no |
| **pomalidomide** | 14 | **0.826** | **+2.91 sd** | **0.571** | **yes** |
| lenalidomide | 8 | 0.823 | +1.98 sd | 0.511 | yes |
| CC-122 | 17 | 0.708 | +2.12 sd | 0.362 | yes |
| CC-220 | 17 | 0.664 | +1.70 sd | 0.307 | no |

The same features and the same grouped, permutation-tested harness throughout.
Only the label changed.

**Three things that were tested and did not help**, recorded so they are not
retried: regressing on continuous fold depletion (0.605, worse, D-042); adding
the geometry score as a feature (0.638, +0.0015, D-042); and removing
ambiguous negatives in case hidden positives were depressing the score
(0.642 at the strictest cut, inside one standard deviation). The ceiling was
never the label noise or the feature set. It was the question.

**Why the module is still not re-based.** The operating points are optimistic:
predictions are out-of-fold so no model scored a gene it trained on, but the
cut is chosen by scanning those same predictions, and 8 to 14 positives cannot
support the nested cross-validation that would fix it. "Clears the floors"
means a cut exists that clears them, not that the threshold is validated. A
shipped score needs a threshold that survives a split it has never seen.

**What would settle it.** The Słabicki 2025 Molecular Cell screen
(10.1016/j.molcel.2025.07.019), which is the study spec 9.2 named: 9,097
reporters against 29 glutarimide analogs, 38 degraded. Per-compound labels with
an order of magnitude more positives per compound would make the nested
validation possible. Its supplementary tables are free on PMC but sit behind a
JavaScript interstitial that defeats both curl and Playwright, so they need a
hand download like the Sievers files did.

**Reversal.** `pipeline/degron_sequence.py` now computes the per-compound
result as part of its normal run, so adding a screen means adding labels.

## D-047: nested validation keeps the AUC and kills the operating point

**Decision.** D-046's claim that pomalidomide "clears the spec 9.2 floors" is
**withdrawn**. The discrimination is real and the threshold was not validated.
Gate G6 stays open.

**What changed.** D-046 flagged its own operating points as optimistic because
the cut was chosen by scanning the same held-out predictions it was scored on,
and said 14 positives could not support the nested cross-validation that would
settle it. The Slabicki screen provided enough positives to build the nested
harness, and it was then applied to Sievers as well:

| | non-nested | nested |
|---|---|---|
| pomalidomide AUC | 0.826 | **0.832** |
| sensitivity | 0.857 | **0.600** |
| specificity | 0.600 | 0.691 |
| clears both floors | yes | **no** |

The AUC is unchanged, so the sequence signal is real. The operating point
collapses, so no compound gives a validated threshold. The caveat was correct
and the headline it qualified was not.

**The new screen, and what it cost to use.** Slabicki et al. 2025
(10.1016/j.molcel.2025.07.019) is the study spec 9.2 named. Its primary-screen
table is truncated at 65,535 rows, the legacy Excel limit, so 2 of 29 compounds
survive in the distributed file. Two bugs were found getting it in: the library
sheet keys as `GENE_start-end;Category` where the ratio table keys as
`GENE_start-end`, and `ZnF.Sequence` holds DNA where the amino acids are in
`Construct_AA`. Both produced zero positives rather than a wrong answer, which
is the good kind of failure.

**The result.** ALV1 reaches nested AUC 0.565 and 4-Ac-Phe-Glm 0.535, against
pomalidomide's 0.832, despite having twenty times the positives. The labels are
sound: ALV1's positives include IKZF1, IKZF3, SALL4, ZFP91, PATZ1, ZNF276 and
ZNF653. The encoding was fixed along the way, since these are 58-residue tandem
constructs and 5,201 of 9,097 carry two C2H2 motifs, so anchoring on the first
was describing half the library by the wrong finger; encoding both lifted the
AUC by about 0.02.

**The pattern.** The compounds where sequence predicts degradation degrade 0.1%
and 0.2% of the library. The ones where it does not degrade 2.8% and 4.3%. A
selective degrader appears to pick substrates by a readable sequence feature
and a promiscuous one does not. That is a hypothesis the data supports, not a
conclusion it proves, and it is the most useful thing the larger screen gave.

**Reversal.** The other 27 compounds would test the promiscuity hypothesis
directly, by ranking compounds on breadth against predictability. They are in
the paper and not in the distributed file. The lead contact offers reanalysis
data on request, which is a human-to-human ask rather than a download.

> **Superseded by D-053.** Both of those claims were wrong. The 27 compounds
> are in supplement 5, the validation screen, which is not truncated; no
> request was needed. The test was run and the promiscuity hypothesis above is
> **not supported**.

## D-048: the threshold objective was wrong, and the grammar transfers

**Decision.** Pomalidomide and lenalidomide **clear both spec 9.2 floors** under
nested validation when the threshold is chosen with the objective the spec
states. Gate G6 remains open on whether to re-base the shipped module, which is
Marc's call, but the metric now has a validated operating point.

**The method error.** D-047 withdrew D-046's floor claim because the nested cut
gave sensitivity 0.600. That cut was chosen by Youden's J, which maximises
sensitivity plus specificity symmetrically. Spec 9.2 asks for something
asymmetric: sensitivity at least 0.70 **subject to** specificity at least 0.60.
Youden left specificity at 0.691, nine points of unspent slack, while
sensitivity sat below its floor. Selecting the inner-fold cut against the spec's
own criterion:

| compound | Youden | spec 9.2 objective |
|---|---|---|
| pomalidomide | 0.600 / 0.691, fails | **0.800 / 0.614, passes** |
| lenalidomide | 0.500 / 0.803, fails | **0.800 / 0.612, passes** |

AUC is unchanged at 0.832 and 0.820, because no threshold can move it.

**Why this is not tuning to a result.** The criterion is in the spec and
predates the project. The threshold is still chosen on inner folds the outer
fold never sees. Both objectives are reported, because the second was adopted
after seeing the first and that flexibility should be visible. What changed is
that the selection rule now matches the acceptance rule; using Youden was a
default, not a decision.

**Independent validation.** A model trained only on the Slabicki ALV1 degrome
predicts the Sievers pomalidomide degrome at **AUC 0.757**, and lenalidomide at
0.757, with no shared rows, a different laboratory, a different library design
and a different reporter construct. That is the strongest evidence in this
investigation that the degron grammar is real rather than an artefact of one
screen's structure.

ALV1 transfers to another screen better than it fits its own, which is only
contradictory on the surface: its 316 positives carry a promiscuous tail that
is hard to fit, while the core grammar it learns is what the selective
compounds use. 4-Ac-Phe-Glm transfers at 0.436, consistent with a different
substrate set rather than a failure of the method.

**What remains open.** The shipped `degron_geometry_score` is still the
geometry, which is uninformative (D-042). Replacing it with a compound-specific
sequence model would mean the atlas column answers "degraded by pomalidomide"
rather than "has degron geometry", which is a different and better question but
also a different column. That is Gate G6.

## D-049: the alanine scan, and the atlas gains a second degron column

**Decision.** The Slabicki alanine scan weights the sequence features, and the
atlas gains `imid_degradation_score` beside `degron_geometry_score`. Both ship.

**The alanine scan.** Slabicki Table S4 is 174,640 measurements: every position
of eight degron-bearing constructs mutated to alanine against twenty
glutarimide analogs, **including POM, LEN and THAL**, so it measures importance
for the compounds being modelled rather than for a proxy. Unlike the primary
screen it is not truncated. Every construct is 58 residues with its two C2H2
motifs at offsets 6 and 34, consistently across all eight genes, so `id - start`
maps straight onto the anchored coordinates the model already uses.

Weighting the features by measured importance, nested validation throughout:

| compound | features | AUC | sensitivity | specificity |
|---|---|---:|---:|---:|
| pomalidomide | unweighted | 0.832 | 0.800 | 0.614 |
| **pomalidomide** | **alanine-weighted** | 0.830 | **0.867** | 0.613 |
| lenalidomide | unweighted | 0.820 | 0.800 | 0.612 |
| **lenalidomide** | **alanine-weighted** | 0.823 | **0.900** | 0.608 |

The AUC does not move and the sensitivity does, which is the metric spec 9.2
turns on. The result is stable across nine floor and power settings for the
weighting, so it is not a tuned artefact; the default is kept.

**The new column.** `imid_degradation_score` is the predicted probability that
a C2H2 zinc finger is degraded by pomalidomide. 4,650 of 21,717 candidates are
scored and the remaining 17,067 are **NULL on purpose**: they carry no C2H2
motif, the model is a zinc-finger model, and a number there would be invented.

**Why it does not replace the geometry score.** They answer different
questions, "has degron shape" against "is degraded by pomalidomide", and the
geometry column is what the UI has always explained. Overwriting it would
change what a column means without changing its name, which is the kind of
quiet redefinition this project exists to avoid. The degron page now carries a
notice distinguishing them.

**The sanity check is a sanity check, not evidence.** ZFP91 scores 0.991,
ZNF276 0.959, IKZF1 and IKZF3 0.907, PATZ1 0.873, and the top of the table is
dominated by genuine Sievers positives. Those genes are in the training set, so
this only shows the model is not broken. The nested AUC of 0.830 is the
evidence.

**A real limitation it exposed.** ZNF653 scores 0.106 and ZNF692 0.046 despite
being true substrates. For a protein with many zinc fingers the scorer takes
the first C2H2 motif in the window around the hairpin, which need not be the
degron-bearing finger. Scoring every finger and keeping the maximum would fix
it and is the obvious next improvement.

## D-050: the live audit, and a QC check that could not fail

**Decision.** Six live defects fixed. The QC viewer check is rewritten, because
it was green throughout and could not have caught the main one.

**The viewer, which was never broken.** `.viewer__empty` sets
`display: flex`, and an explicit `display` beats the user-agent rule that the
`hidden` attribute relies on. `hideEmpty()` set `hidden=true` correctly and the
overlay stayed on screen, on top of a structure that had loaded. The symptom
was "viewers do not load"; the cause was a placeholder covering them.

A global `[hidden] { display: none !important; }` now guards every element
toggled that way, because fourteen other classes set an explicit `display` and
`plddt-legend` is toggled with `hidden` too.

**The QC check could not fail.** It read
`!!document.querySelector('[data-role="empty"]')`, which tests whether the
element exists. It always exists. The check therefore reported `empty: true`
whether the viewer was working or not, and `PASS: True` alongside it. It now
tests `offsetParent !== null`, which is visibility.

**The app imported the build pipeline.** `app/routes/{api,degradability,e3}.py`
each did `from pipeline.common import load_config` inside a bare
`except Exception`. `pipeline/` is not deployed, so on the droplet every one of
them fell through to a default: the Degradability page said "thresholds could
not be read", the Lens graph silently used a 400-node cap instead of the
configured one, and the E3 page lost its triage weights. Nothing crashed, which
is why it survived. `app/thresholds.py` reads the TOML directly and the app no
longer imports the pipeline at all.

**Structures were served as raw gzip.** nginx sent `.cif.gz` as
`application/octet-stream` with no `Content-Encoding`, so the browser handed
Mol* compressed bytes. Flask sets that header automatically for a `.gz`, which
is exactly why local QC passed and the live site did not.

**The lens graph had no bounds.** A force layout with up to 400 nodes and a
charge of -120 spreads well past the viewBox and nothing refit the view, so the
user saw an empty canvas with the network off-screen. It now fits to the
laid-out extent once the simulation cools; manual zoom still works.

**The schematic.** Stage 4 said "BINMAN-LM: not trained". Its canvas was
hardcoded at 1060x460, which rendered 1380x600 in a desktop panel and left a
third of the height empty. The canvas is now computed from the content, which
also fixes the two pixels the module column was being clipped by: 1380x275.

**Licences.** DEGRONOPEDIA states CC BY on its own site, so it is recorded.
UbiBrowser states no terms anywhere and its NAR paper's CC BY-NC-4.0 covers the
article rather than the database, so it stays undetermined with that
explanation attached. Writing the explanation into the field broke an
exact-match count that read `== "not determined"`, which made one unknown
licence read as zero; both the counter and the UI pill now match on the prefix.

**Still open.** Making the metric cards filter the lists.

## D-051: headline figures filter the table, and deploys stopped being invisible

**Decision.** Each headline stat that can be expressed as a filter is a button
that applies it. The brand subtitle is the backronym. The degron page's
121-word notice is one caveat line. App CSS and JS revalidate instead of
sitting in a browser cache for an hour.

**The cards.** Stating a number the table cannot be made to show is a dead end:
clicking the figure is the obvious thing to try. Each card now carries the
predicate it was counted with, toggles on and off, and shows its state through
`aria-pressed`. Verified against the live API, card against filter: glue
candidates 24,204, balanced glues 10,579, symmetry mediated 28,780, novel
bridges 14,260, all exact.

**Furniture has no filter and stays a plain figure.** It is counted through a
join on `ligand.is_furniture`, which is not a bridge field. The obvious
substitute, `evidence_class = furniture`, returns **zero**, because that column
is NULL throughout. A card whose filter shows a different number from the card
is worse than one that does not click, so it does not click.

**Rotation was a stale cache, and that was a deployment defect.** Dragging the
viewer in a fresh browser rotates it. `/static/` was served with
`max-age=3600`, so every deploy was invisible for up to an hour to anyone who
had already loaded the page: the CSS fix for the overlay shipped and the
reporter still saw the old behaviour. App CSS and JS now send `no-cache`, which
means revalidate rather than do not store, so the ETag still saves the
transfer. Vendored libraries keep `immutable`, because they are version-pinned.

One hard refresh is still needed to clear what a browser already holds; after
that a deploy is visible immediately.

**The notice boxes.** A full-width box at the top of every page turns the
caveat into furniture people stop reading. The degron page's two boxes had
already become one 121-word table; it is now a one-line caveat beside the data
with a link to the About tab, where the contingency tables and sweeps already
live.

## D-052: the two apparent misses were the geometry scan, not the model

**Decision.** `imid_degradation_score` scores every zinc finger in a
candidate's window and keeps the best, rather than the first. D-049's worry
that ZNF653 and ZNF692 were model failures is **withdrawn**: they are not.

**What the scores actually show.** Lining each scored atlas row up against the
zinc finger Sievers reports as degraded:

| gene | atlas row | degraded ZF | overlap | score |
|---|---|---|---|---|
| ZFP91 | 400-409 | 400-422 | yes | **0.991** |
| ZNF276 | 524-533 | 524-546 | yes | **0.959** |
| IKZF3 | 146-155 | 146-168 | yes | **0.907** |
| ZNF692 | 448-457 | 417-439 | **no** | 0.046 |
| ZNF653 | 528-537, 586-595 | 556-578 | **no** | 0.106, 0.011 |

Every row that lands on the degron-bearing finger scores high, and every row
that does not scores low. The low scores are **correct for the finger they
describe**. The geometry scan never placed a hairpin candidate on the degron
finger of those two proteins, so there is no row there to score.

**What that means for the column.** It is per-candidate, not per-protein: it
answers "is the zinc finger at this hairpin degraded by pomalidomide", and a
protein whose degron carries no hairpin candidate has no row to carry the
answer. That is a coverage limit of the upstream scan rather than an error in
the score, and it is the honest reading: the model was right in all five cases.

**The multi-finger change is kept although it changed nothing measurable.**
Taking the best of several fingers in one window is correct in principle and no
score moved, because the windows around these candidates hold one motif each.
It costs nothing and removes a real failure mode for wider windows.

**What would close the gap.** Scoring every zinc finger in a protein rather
than only those at hairpin candidates. That is a different column with
different semantics, per protein rather than per candidate, and it should be
added as one rather than quietly widening this one.

## D-053: the promiscuity hypothesis was testable after all, and it is wrong

**Decision.** D-047's promiscuity hypothesis is **not supported**. Breadth does
not predict whether a compound's degradation is readable from sequence. The
pomalidomide-trained model transfers above chance to every one of the 24
glutarimide analogs whose AUC is estimable, including the broadest compound in
the set. The hypothesis stays in the record as a hypothesis that was tested and
failed, which is worth more than one left open.

**What made the test possible.** D-047 said the other 27 compounds were "in the
paper and not in the distributed file" and named the human-to-human ask as the
only route. That was wrong about the file, not about the paper. Supplement 4,
the primary screen, is the truncated one. Supplement 5, the validation screen,
is a modern `.xlsx`, is not truncated, and carries all 29 compounds against 57
constructs the primary screen had already shown to be degrons. No reanalysis
request was needed: the data was already on disk, in the file next to the one
being read.

**The join, which failed silently first.** The ratio table keys on
`Construct.ZnF` ("BCL6_570-627"), which matches the library's `Construct`
column and not its `Construct_Name` ("BCL6_570-627.Validation_AA"). The variant
sits in `Category` (WT, Mut1, Mut2, Mut3) and only the WT rows are the
compound's effect on the native degron. The first run printed a header and no
rows, which is again the good kind of failure.

**The result, gene-disjoint.** Every Sievers row from a panel gene is held out
of training, so no panel protein contributes its own label.

| | value |
|---|---:|
| compounds with an estimable AUC | 24 of 29 |
| mean AUC | **0.779** |
| median / min / max | 0.769 / 0.671 / 0.954 |
| above chance | **24 of 24** |
| permutation p (2,000 shuffles) | **0.0005** |
| breadth against AUC, Spearman | **+0.175 (p=0.41)** |
| breadth against AUC, Pearson | +0.039 (p=0.86) |

The correlation is not negative as the hypothesis required. If anything it is
weakly positive. ALV1, the broadest compound in the panel at 54% of constructs,
transfers at 0.726.

**Why this does not contradict D-047's measurement.** The two experiments ask
different questions and both results stand. D-047 fitted each compound a model
on its own screen: ALV1's own nested AUC really is 0.565. This fits one model on
pomalidomide and tests it against each compound's labels. So what fails for
ALV1 is fitting its 316 positives across 9,097 reporters, not reading its
degrons. The reconciliation that fits is the weak tail near the FDR cut: a broad
compound's label set includes many marginal calls, those are what resist
fitting, and a panel of 57 already-validated degrons does not contain them.
That is itself a hypothesis, and it is a more specific one than the one it
replaces.

**The caveat that matters, stated as a limit not a footnote.** 69 of the panel's
72 anchored cores also occur in the Sievers library, because C2H2 fingers repeat
across the proteome. Removing every training row that shares a core, as well as
holding out the genes, drops the training positives from 12 to 5 and the mean
AUC to 0.579 at permutation p=0.16. Those two causes are separated by a
size-matched control: 200 gene-disjoint fits subsampled to 5 positives with
shared cores still allowed average 0.716, which puts the core-disjoint result at
the 6.5th percentile of that distribution. So most of the drop is the smaller
training set and a real residual is the core sharing. The transfer is above
chance and partly carried by core identity across proteins, and 57 constructs
cannot separate the two cleanly. Both numbers ship.

**The panel's own limit.** These 57 constructs are validated degrons, so
breadth across them is selectivity within known degrons and not a proteome hit
rate: pomalidomide degrades 42% of the panel and 0.1% of the primary library.
The ordering is the right one and the range is compressed, which weakens a null
correlation as evidence. It does not weaken the positive finding, which is that
a pomalidomide model reads degrons for compounds it was never trained on.

**Also found, not used.** Supplement 8 carries 412 compounds with SMILES and a
per-compound activity profile, and supplement 7 a CRBN alanine scan over 111
ligase mutations. Supplement 8 measures only 10 constructs per compound, too few
for a per-compound sequence AUC, so it cannot extend this test; it would support
a chemistry-side model, which is a different module. Recorded so the next person
does not go looking for data that is already here.

## D-054: the reach window stays unfitted, and now on evidence

**Decision.** The degradability reach window stays unfitted and no degradability
verdict is emitted. What changes is the standing of that decision: it rested on
one feature having been tried and missed, and it now rests on a measurement
showing that no feature derivable from an AlphaFold monomer answers the question
to the spec 9.5 floor. `fit_status` in the config said "not yet fitted", which
was misleading, and now says what actually happened.

**Why it was worth measuring.** `fit_accessibility` reached a held-out AUC of
0.546 against the 0.65 floor on lysine exposure alone. That leaves two very
different readings open: exposure is the wrong feature, or the question is
unanswerable from a monomer. The first would mean the module is one good feature
away from shipping a verdict. The second closes it. Those deserve to be
distinguished rather than left as an open item.

**What was measured.** Eighteen features for all 12,705 lysines of the 403
proteins carrying a UniProt ubiquitin crosslink: exposure, pLDDT, burial at two
radii, secondary structure, position in the chain, local sequence composition,
lysine spacing, and two protein-level terms. Logistic regression and gradient
boosting, five folds, whole proteins held out.

**The trap, and it is a good one.** Pooled over all lysines the full set reaches
**0.714** and clears the floor. It should not be believed, and the reason is
visible in the single-feature table:

| feature | pooled AUC | within-protein AUC |
|---|---:|---:|
| protein's lysine count | 0.707 | **0.500** |
| protein's chain length | 0.692 | **0.500** |
| nearest other lysine | 0.548 | 0.560 |
| relative NZ SASA (shipped) | 0.545 | 0.544 |

The two strongest features are constant within a protein, so they score exactly
0.500 when the AUC is computed inside one protein, which is the arithmetic
proving they carry no information about *which* lysine. What they rank is
proteins, by the fraction of their lysines the catalogue happens to annotate.
That is annotation prevalence. The module's question is always within one
protein: given this ligand site, is a reachable lysine ubiquitylated.

**The figure that decides it.** Mean AUC inside each of the 393 proteins
carrying both classes.

| feature set | pooled | within protein |
|---|---:|---:|
| exposure only, as shipped | 0.545 | 0.544 |
| every per-lysine feature, boosted | 0.629 | 0.598 |
| everything including protein-level, boosted | **0.714** | **0.626** |

Nothing clears 0.65. The best per-lysine set improves on exposure alone by
0.054 and still misses. The negatives are the other lysines of the same
proteins, which were never assayed and found unmodified, so each of these
figures is generous rather than conservative.

**Conclusion.** Exposure is weak and it is not uniquely weak. The limit is the
question, not the feature: an AlphaFold monomer and a catalogue of observed
sites cannot say which lysine gets ubiquitylated to the standard spec 9.5 asks
for. Shipping a verdict would require a dataset of lysines assayed and found
unmodified, which is a different experiment from the one that exists.

**What was not done, and why.** The pooled 0.714 is a number that would have
cleared the floor and been wrong to use. It is recorded here so that nobody
reaches for it later: `pipeline/degradability_features.py` reports both columns
side by side for exactly that reason.

## D-055: the per-protein zinc-finger table, and what it is worth

**Decision.** A `zinc_finger` table ships in the atlas: one row per C2H2 motif
per protein, scored for glutarimide degradation with no geometry filter in front
of it. This is the column D-052 named, added as its own thing with per-protein
semantics rather than by widening `degron.imid_degradation_score`. The UI is
deliberately not changed yet, because the last standing instruction on the app
is to make it simpler, and a new page cuts against that.

**It closes the gap it was built for.** 7,452 C2H2 motifs over 1,123 proteins,
of which **2,792 (37.5%) overlap no hairpin candidate** and were therefore
unreachable by the per-candidate column at any score. Two of them are the ones
D-052 identified:

| finger | per-candidate column | this table | screen |
|---|---:|---:|---|
| ZNF653 556-578 | 0.106 and 0.011, wrong fingers | **0.982** | degraded |
| ZNF692 417-439 | 0.046, wrong finger | **0.957** | degraded |

13 of the screen's 14 pomalidomide-degraded fingers are now in the table, and 2
of those 13 are reachable only because the geometry prefilter is gone.

**What it is worth, which is less than the hit list suggests.** Five of the
seven canonical substrates audited are genes in the scorer's training set, so
their scores of 0.907 to 0.991 are partly memory. Only two are genuinely held
out and it gets one: IKZF1 scores 0.907, and SALL4 scores 0.264 on its
documented degron and 0.485 on its best finger, which is a real miss recorded as
one. The generalisation evidence for this scorer is the 29-compound
gene-disjoint transfer test in D-053, not this table.

**Precision, stated as enrichment because that is the honest unit.** Over the
5,513 fingers the screen assayed, 13 are degraded, a base rate of 0.24%. In
sample, because these labels trained the scorer:

| cut | degraded fingers caught | screen-negative fingers above it | precision | enrichment |
|---|---:|---:|---:|---:|
| 0.9 | 7 of 13 | 9 | 0.438 | **186x** |
| 0.7 | 12 of 13 | 80 | 0.130 | 55x |
| 0.5 | 13 of 13 | 255 | 0.049 | 21x |

So it is a triage ranking, not a call. At its top band it concentrates the
degrome roughly two-hundredfold and is still wrong more often than not in
absolute terms, which is the expected behaviour of the operating point D-048
chose: the spec asks for sensitivity 0.70 at specificity 0.60, and a
0.24%-prevalence problem punishes that specificity hard. The table is useful for
ordering experiments and not for believing any single row.

**The five genuine hypotheses.** Among the high-scoring fingers that no hairpin
candidate reached, five were never assayed by the screen at all: CTCFL 259-279
(0.939), ZNF407 1688-1708 (0.934), ZFP64 525-546 (0.920), HIVEP3 1756-1776 and
HIVEP1 88-108 (0.905). Five more score above 0.9 and the screen calls them not
degraded (HIC1, ZNF821, IKZF5, HIVEP2, PRDM15), which is the false-positive rate
above being concrete rather than abstract.

**A join bug worth recording.** The first run labelled 3 of 1,178 fingers and
should have labelled 5,513. The Sievers `Gene` column mixes gene symbols with
Swiss-Prot entry names: ADNP2 and CTCF appear as themselves, ZNF276 appears as
ZN276 and BCL11A as BC11A. Joining on it dropped every ZNF gene, which is most
of the library. The sheet also carries `Uniprot.Code`, so the join is on
accession now. The symptom was a suspiciously empty label column rather than a
wrong answer, which is the good kind of failure again.

**Still dead, and flagged not fixed.** `degron.is_known_neosubstrate` is 0 for
all 21,717 rows and has never been populated. The new table carries
`screen_degraded` instead, which is sourced, per finger and auditable. The old
column should either be populated from a documented list or dropped.

## D-056: every viewer frames its ligand, and three viewer bugs that hid behind it

**Decision.** Every viewer now frames the thing its row is about, renders it as
sticks and wraps it in an emissive neon shell that Mol*'s bloom pass turns into
a glow. Bloom runs in `emissive` mode, so only that geometry blooms and the
protein behind it stays readable.

**How the ligand is named, which is the part that matters.** A trimmed entry
keeps whatever sat near the interface: 10MF carries 42T, 1N7, a zinc and a
magnesium, and only 42T is the bridge. Framing "every non-polymer" would centre
the midpoint of four things and show none of them. The resolver now passes the
row's `ccd_id`, and the viewer selects on it through Mol*'s query API, reached
via the `lib` namespace the viewer bundle exports. Verified: the query returns
exactly 112 atoms for 8FY1, which is exactly YF8's atom count.

**Three bugs this uncovered, none of which announced itself.**

1. **`structure_file` was never requested.** `default_columns` is the contract
   for what is displayed, and the query returns exactly that set. The bridge
   resolver read `row.structure_file` to choose between the local trimmed file
   and RCSB, and it was always undefined, so **every viewer fetched from RCSB
   and the 3,839 trimmed structures on disk were never read once**. 18,508
   bridge rows have one.
2. **The E3 viewer could never load anything.** Its resolver reads
   `best_structure`, which was not in any default set *and* not selectable at
   all. So `url` was null and `pdbId` was null together, and the viewer sat on
   its empty state for all 650 ligases. It was not failing: it was being handed
   nothing and displaying that correctly.
3. **`cycleRepresentation` never changed a representation.** It called
   `updateRepresentations(components, {type})`, and that method takes
   (components, pivot, params), so the type object arrived as the pivot and the
   params as undefined. The overlay said the representation had changed.

**The camera, which needed two goes.** `focusLoci` with an animated duration is
issued from the load promise, and Mol* queues its own camera reset when the
first object commits. That reset lands afterwards, so the framing silently did
not happen. The framing is now instant, re-issued once after the next draw, and
only the explicit Reset button animates. This was caught by screenshotting a
headless browser, not by reasoning: the DOM said the ligand had been found and
the camera had not moved.

**Where it does not apply, stated rather than faked.** An AlphaFold monomer has
no ligand, so the degron and degradability viewers frame their row's residues
instead: the hairpin tip plus six either side, or the lysine plus four. Those
get Mol*'s own focus representation, which is ball-and-stick, but **not** the
neon shell: attaching a custom representation needs a component built from a
selection expression, and the viewer bundle exports the query API but not the
expression builder. The lens viewer shows a protein node with neither a ligand
nor a named site, so it frames the whole model. The root carries
`data-ligand-focus` as `ligand`, `residues` or `none`, so which branch ran is
visible rather than inferred.

**A judgement call on the E3 page.** A ligase row names no ligand, so the
viewer falls back to any non-furniture non-polymer. Framing that as tightly as
a named glue showed a glowing dot in a void, so an inferred ligand is framed at
a 28 Å minimum radius and a named one at 7 Å. Metals are deliberately not
treated as furniture: a zinc can be the whole point, as it is in every C2H2
degron in this atlas.

**Also.** The viewer now fills its half of the workbench instead of stopping at
its own min-height, so it ends on the same line as the table beside it. A
rejected column reached the client as a 500 and a stack trace, because the
route caught only `sqlite3.Error` and column validation happens inside
`execute()`; it is a 400 with the reason now.

**A fourth bug, found while deploying this one.** `provision.sh` ran
`systemctl enable --now binman-web.service`. `--now` starts a stopped service
and does nothing to a running one, so the app was never restarted on redeploy.
Flask caches templates inside the worker processes, so new HTML landed on disk
while gunicorn kept serving the old. Static files updated normally, which is
what made it invisible: CSS and JavaScript changes appeared live and template
changes did not, from the same deploy, with no error anywhere. **No template
change has ever reached the live site from this script.** It now restarts
unconditionally, and the fix was confirmed by watching `class="split"` become
`class="split split--workbench"` on the live site after a restart and not
before.

## D-057: the first row loads itself, and the glow was hiding the ligand

**Decision.** Each ledger pins its first row on load, so the viewer opens with a
structure in it rather than an empty frame and an instruction. Once only, and
never over an existing pin: a viewer restored from a URL fragment keeps what the
link asked for, and clearing the stack does not drag the user back to row one.

**"The first entry is unconnected" was a rendering fault, not a data one.** The
obvious reading is missing bonds. The measurement says otherwise: the first row,
7PH7 with the lipid EIW, selects 150 atoms carrying **154 bonds**. The bonds were
always there. Hiding the shell and re-rendering showed the lipid fully connected.

What hid it was the glow. The neon shell ran at emissive 1.0 with `ignoreLight`
and a bloom pass on top, over sticks only 0.26 Å thick, so it worked as a bright
screen in front of the molecule and only the brightest atom tips showed through,
as a scatter of dots. The sticks are 0.34 Å now, the shell is at emissive 0.7
and alpha 0.09, its probe radius is 2.4 Å so it stands clear of the atoms as a
halo rather than sitting on them, and bloom is at 1.3 rather than 1.8. **The fix
was to the thing that was obviously working, found by measuring the thing that
was obviously broken.**

**Carbons are pinned to one colour.** Mol* colours ligand carbons by chain, so
7PH7's lipid came out cyan inside a cyan shell and vanished into its own glow
while 8FY1's came out magenta and read perfectly: the same code looked fine or
broken depending on which chain the ligand happened to sit beside. Carbons are
now a fixed vivid magenta through `element-symbol` with a uniform `carbonColor`,
and oxygen, nitrogen and sulfur keep their standard colours, so the molecule
still reads chemically.

**Two layout attempts that failed, recorded so they are not retried.**

1. Tabulator's `height` was given `max(520px, calc(100vh - 330px))`. It does not
   parse `max()`, and the table came out a few hundred pixels short with no
   error. The value is computed in JavaScript now.
2. `height: '100%'` then made the table's height depend on the viewer column
   while the viewer sized itself from the grid row. Mol* initialised onto a
   zero-height canvas and **rendered nothing at all**, with the toolbar and the
   identifier still showing, which looks exactly like a loading failure. A
   number breaks the cycle.

**And a scoping error worth the same note.** Capping the selected-row detail with
`.split--workbench .panel` also caught the table's own wrapper and capped the
table at 34% of its column. It is matched by its position after the viewer now.
The detail panel shares the viewer's column, so it is capped and scrollable:
without that, pinning a row on load squeezed the viewer down to its min-height,
which is the opposite of what the height change was for.

## D-058: a boolean that was false for every row, and a stray database in production

**Decision.** `degron.is_known_neosubstrate` is populated from the two screens
the repository already carries, rather than dropped. D-055 flagged it as dead
and left the choice open; this is the choice.

**Why it was not harmless.** The column was 0 for all 21,717 rows and had never
been written. A boolean that is false everywhere is not a neutral default: the
degron page rendered a tile reading **"0 known neosubstrates"** about a proteome
that contains IKZF1, IKZF3, ZFP91, ZNF276 and SALL4. The page was making a
confident and wrong claim, in a number, which is exactly what spec 1.0 forbids.

**The definition, which is deliberately narrower than the word.** A protein is
marked when either screen in this repository reports it degraded: Sievers 2018
under thalidomide, lenalidomide or pomalidomide, joined on `Uniprot.Code`, or
the Slabicki 2025 validation panel under any of its 29 glutarimide analogs,
joined on gene symbol. That gives 15 accessions and 35 genes, marking **206
degron candidates across 38 proteins**.

It means "a screen in this repository reports it degraded", which can be checked
against files on disk, and not "the literature reports it", which cannot. The
column's note in the UI says so rather than leaving the stronger reading
available, and the tile filters the table to those 206 rows.

**A test that would have caught it.** An all-zero boolean passes every schema
check ever written, because the column exists and its values are valid. The new
test asserts that something is marked and that the canonical substrates are
among the marked, which is the only form that fails when the column goes dead
again.

**Also removed: a stray database that had been deployed.** `data/atlas/` held
`binman 2.sqlite`, an abandoned partial build from 3 October carrying 300
entries, 427 bridges and no degrons, ligases or lysines at all. It is gitignored
so it never reached the repository, and `provision.sh` rsyncs `data/atlas/`
wholesale, so it had been sitting in `/opt/binman` on the live host since the
first deploy. Nothing opens it: `app/db.py` resolves `binman.sqlite` by name.
Removed from both, and the site was checked afterwards.

## D-059: the lens graph opens on a node, and why it had never been laid out

**Decision.** The lens graph picks a node on load, centres the layout on it and
loads its structure in the viewer, so the page opens on something rather than on
an empty frame beside an empty detail table. The focus node when the URL names
one, otherwise the most connected node in the graph. Once only, and never over a
selection that is already pinned, so arriving from the E3 page keeps its ligase.

**Three faults were sitting underneath that, and the first two had been
invisible for the whole build.**

1. **The canvas measured 300 pixels wide.** An inline `<svg>` with no width is
   300 px by the replaced-element default, whatever its container does, and
   `render()` sized the force layout from `clientWidth`. So 344 nodes were laid
   out in a 300-wide box. The CSS background filled the column, which is what
   made the page look correctly sized while the graph inside it was not.
2. **The fit never ran.** `fitToContent` was wired to the simulation's `end`
   event, and with 344 nodes that event does not arrive: the rendered SVG
   carried **no transform at all**. The fix recorded for the earlier "pans out
   so nothing is visible" complaint had therefore never executed once. The
   layout is now ticked to completion synchronously, which also makes it
   deterministic and present on the first frame.
3. **The layout sprawled over roughly 10,000 units.** This graph is mostly small
   disconnected components, and many-body repulsion pushes those apart without
   limit, so fitting them landed on a scale of 0.1 and the graph read as dust.
   A weak `forceX`/`forceY` pull toward the centre bounds it without flattening
   the clusters.

Each of those alone produces "the graph looks wrong", and fixing any one of them
alone still produces "the graph looks wrong", which is why the earlier fix
appeared not to help.

**The selected node had to be findable.** A 4.5 px dot with a dark rim is not
locatable among 344 of them, so the selection also grows by 4 px and takes the
accent colour. A default entry nobody can see is not a default entry.

**And the zoom is derived, not fixed.** Centring at a fixed scale showed an empty
canvas whenever the selection sat in a sparse neighbourhood. The scale is taken
from the laid-out span and clamped, so it zooms in on the selection without
passing the point where the layout has anything left to show.

**The viewer side.** A lens node is an AlphaFold monomer with no ligand and no
named residues, which is the branch that previously did a plain camera reset:
that frames the model from whatever direction the file was written in, which for
an elongated protein is end-on. It now orients to the structure's own principal
axes first and frames second, and re-issues after the next draw for the same
reason the ligand branch does (D-056).

## D-060: "could not be read" was itself the wrong value

**Decision.** The About page separates a value the build failed to produce from
a value that records a finding. The UbiBrowser 2.0 licence is the latter, and
reporting it as the former was a false statement about this project's own
provenance, on the one page whose entire claim is that every number on it comes
from an artefact.

**What the page was saying.** "1 value(s) could not be read from an artefact and
are shown as 'not recorded' rather than guessed: licence for reference
'ubibrowser2'." Every clause of that is wrong for this entry. The value was read.
It is not shown as "not recorded". And nothing was skipped.

**What the artefact actually holds.** `not determined: the project site states
no terms, and the NAR paper's CC BY-NC-4.0 covers the article rather than the
database.` Somebody checked both and wrote down what they found.

**Both halves re-checked before changing anything**, because the right fix for a
wrong licence is to record the right licence, not to reword the complaint:

* `http://ubibrowser.bio-it.cn/ubibrowser_v3/` returns HTTP 200 and its pages
  carry no licence, terms, copyright or usage text at all.
* Crossref gives 10.1093/nar/gkab962 a single licence,
  `creativecommons.org/licenses/by-nc/4.0/`, with `content-version: vor`. That
  is the article, not the database behind it.

So the recorded finding is accurate and stays. The defect was entirely in the
reporting.

**The fix.** `licence_state()` returns one of three things rather than two:
`missing` when the build produced nothing, which still counts as unreadable and
still needs fixing; `not_published` when the source was checked and publishes no
terms; `stated` otherwise. The page gives each its own sentence, and the second
one reads "1 source(s) publish no licence. This was checked and recorded, not
skipped", followed by the reason. Unreadable values are now 0, which is the
honest count.

**Why this was worth the care.** A build that over-reports its own gaps trains
the reader to ignore the gap list, which is the same end state as not having one.
The distinction is pinned by tests on `licence_state` directly, so it holds for
values this repository does not currently contain, plus one test that the built
page never calls a recorded finding unreadable.

## D-061: two ways to raise the degron AUC, both measured, both worse

**Decision.** The shipped degron configuration stands. Borrowing labels from
related compounds and dropping low-importance positions were both tried against
the loop's stated goal of raising the degron AUC, and both lose to it.

**The constraint is 14 positives**, so the two obvious routes are more labels or
fewer parameters. Each was tested with whole genes held out and scored against
pomalidomide.

**Borrowing labels costs AUC, and costs more the more is borrowed.**

| trained on | positives | AUC against POM |
|---|---:|---:|
| POM (shipped) | 14 | **0.8304** |
| LEN + POM | 15 | 0.8239 |
| THAL + LEN + POM | 15 | 0.8239 |
| POM + CC122 + CC220 | 29 | 0.7762 |
| all five | 30 | 0.7838 |

Doubling the positives costs 0.054. This looks like it contradicts D-053, and it
does not: a pomalidomide model *ranks* the other glutarimides above chance
because the grammar is shared, while their specific positives are noise for the
pomalidomide question. Transfer out and training in are different directions.

**Dropping positions is the interesting failure, and it is a lesson rather than
a result.** Sweeping k and keeping the best gives 0.8397 against the shipped
0.8304, which reads as a small win. It is not one. k was chosen by looking at
the number being reported, over nine values, on a five-fold estimate whose fold
sd is 0.08.

Choosing k honestly, on inner folds inside the training half, gives **0.7449**:
0.086 **worse** than shipped. The inner folds also disagree about k from fold to
fold (20, 18, 12, 12, 20), which is what no stable signal looks like.

| | AUC |
|---|---:|
| sweep, k chosen by looking at the answer | 0.8397 |
| nested, k chosen inside the training half | **0.7449** |
| **selection bias** | **0.0948** |

Same data, same code, differing only in whether the choice was allowed to see
the test fold. That number is worth more than either estimate: it is how much a
14-positive problem flatters any tuning done against its own test set, and it is
larger than every improvement this project has reported for the degron metric.

**Conclusion, which answers the loop's goal.** The shipped model is a local
optimum for the data available. Neither route gets past 14 positives, and the
honest way to raise this metric is a larger matched screen, not a better fit to
the one that exists. `pipeline/degron_ablation.py` keeps both results
reproducible so neither is re-proposed from first principles later.

## D-062: why the flagship metric misses, and a blind spot in a blind-spot inventory

**Finding, not yet a decision.** Glue Atlas recall is 0.7719 against a 0.85 floor:
73 of 320 curated entries are not recovered. The misses were diagnosed rather
than estimated, and they fall into three buckets with three different causes.

| bucket | n | cause |
|---|---:|---|
| never ingested | 20 | the catalogue requires 2 distinct polymer *entities* |
| ingested, no bridge | 46 | the spec 5.1 dSASA test rejected the ligand |
| bridged, classed as something else | 7 | cofactor, cryoprotectant, detergent, peptide-like |

**The 20 are a scope hole, and an embarrassing one.** Spec 1.1 catalogues entries
with `polymer_entity_count >= 2`, so a pure homodimer, being one entity however
many chains it has, is never fetched.

> **Correction, D-071 onward.** This entry first said the exclusion happened
> **twice over**, in the catalogue and again in spec 5.1's "distinct entities".
> The second half is wrong. `find_bridges` rejects only a chain paired with
> itself: its own comment says "two copies of the same chain are distinct
> instances and do count". The atlas already holds **42,797 same-entity
> bridges, 15.1% of the total**, so homo-oligomeric glue detection has worked
> all along inside catalogued entries. The gap is the catalogue query alone,
> which makes the fix one line rather than a change to what a bridge is. Checked against RCSB, all ten sampled misses have
`polymer_entity_count = 1` with 2 to 20 chains:

* **1A7X**, FKBP12 with FK1012: the original chemical dimeriser.
* **3TCT**, transthyretin with tafamidis: a marketed drug whose entire mechanism
  is stabilising a homotetramer.
* **8FLK**, a STING oligomer with a cyclic dinucleotide.
* **3KO0**, calmodulin with trifluoperazine, at 20 chains.

A project called a Blind-spot INventory of Molecular Adhesives currently cannot
represent the class of adhesive that glues a protein to a copy of itself. That
is not a tuning question and it is not mine to fix silently: it changes what the
atlas *is*, and spec 1.1 and 5.1 both say "distinct". **Gate: Marc's call.**

**The 46 are a sensitivity question**, and they are not obscure: 3SML is 14-3-3
sigma, 5GWO and 5ZCG are the abscisic-acid receptor and PP2C, 7JUR is KSR2 with
MEK1. All passed the catalogue and all were rejected by the dSASA test.

**Correction, same session.** This entry first said rejections are not recorded
at all, on the evidence that every one of the `bridge` table's 239,485 rows is
`status = 'ok'`. That was wrong, and wrong in the direction that flatters the
finding. `data/interim/halves.jsonl` holds 92 MB of exactly the missing record:
every half-interface considered, with its dSASA, its contact count and its
entity, written by `run_bridges` for precisely this purpose. The build does
record its rejections. What it does not do is **consult them when reporting the
misses**, which is why the misses arrive as 73 PDB codes rather than 73 reasons.
The gap is in the reporting, not the recording, and the diagnosis below came
straight out of that file.

## D-063: the recall miss is one threshold, and it is worth 0.078

**Finding, with the decision left open.** Read out of `halves.jsonl`, the 73
curated misses decompose cleanly, and the largest controllable cause is a single
criterion: spec 5.1's floor of **three** heavy-atom contacts under 4.0 A.

| recovered at | recall | n=320 |
|---|---:|---:|
| shipped: dSASA >= 25 A2 and contacts >= 3 | 0.7719 | |
| contacts >= 2 | **0.8250** | +17 entries |
| contacts >= 1, dSASA alone | **0.8500** | +25 entries |

The floor is 0.85. Relaxing the contact count alone reaches it exactly.

**What the 17 are.** Canonical 14-3-3 glues, among others: 3SML, 3SMM and 3SMO
(14-3-3 sigma), **3P1O, which is fusicoccin**, plus 3OGK, 4FR3 and eight of the
8Bxx series. Their geometry is not marginal. In 3SML the ligand buries 628 A2
against 14-3-3 and 145 A2 against the phosphopeptide; in 3P1O fusicoccin buries
965 A2 and 139 A2. Both clear the 25 A2 dSASA floor five-fold on the weaker
side. Both are rejected for making **2** heavy-atom contacts to that second
chain instead of 3.

So the criterion that rejects them is not measuring whether the ligand touches
two proteins. It is measuring how many atoms happen to fall inside 4.0 A, and a
glue that lies flat against a shallow peptide groove buries a lot of surface
with few close contacts. dSASA and contact count are not two independent checks
here: the second one is overruling the first on exactly the geometry the module
exists to find.

**Why this is not being changed now.** Spec 9.6 permits one documented threshold
adjustment and it is already spent, on the degron geometry thresholds
(`calibration_date = 2026-10-03`). Relaxing a bridging criterion also has a
specificity cost that is not yet measured: artefact precision is already under
its own floor at 0.9391, and admitting 2-contact interfaces can only move it
down. The honest package for a decision is the recall gain **and** the precision
cost, measured on the same change, and the second half does not exist yet.

**Also in the decomposition**, from the same file: 20 misses are never ingested
at all (the homo-oligomeric scope hole, D-062), 7 bridge correctly at the
shipped thresholds and are missed because their CCD was classed as a cofactor,
cryoprotectant, detergent or peptide-like, and the remainder never reach a
qualifying second chain and look like correct rejections.

## D-064: the contact floor drops to 2, on Marc's authorisation

**Decision.** `bridging.min_heavy_atom_contacts` goes from 3 to 2. Marc
authorised it after being shown the measured cost and benefit together. The
homo-oligomeric scope change (D-062) is authorised separately and runs after the
32B training finishes, as a second change measured on its own.

**This is the second threshold adjustment in the build and spec 9.6 allows one.**
The first is spent on the degron geometry thresholds
(`calibration_date = 2026-10-03`). So this is a deviation taken on an explicit
decision, not on the spec's allowance, and it is recorded as a deviation rather
than dressed up as one of the permitted kind.

**What was measured before the change, not after.**

| | contacts >= 3 | contacts >= 2 |
|---|---:|---:|
| recall against the curated set | 0.7719 | **0.8250** |
| bridge instances atlas-wide | 110,372 | 122,048 |
| glue_candidate share of bridges | 12.7% | 12.9% |
| artefact precision | 0.9391 | unchanged |

Artefact precision does not move because it is computed over CCD classifications
in the `ligand` table and never consults this floor. The glue share of the
11,676 newly admitted instances is 14.9%, which is richer than the 12.7% already
there, so the relaxation is not a furniture flood: it admits a slightly better
mix than the atlas already carries.

**Recall still misses the floor at 0.8250.** This change alone does not fix 9.1,
and it was not chosen as a way to reach a number. It was chosen because
rejecting fusicoccin is wrong on the merits: 965 A^2 buried against 14-3-3 and
139 A^2 against the phosphopeptide is a bridge by any reading of spec 5.1's
intent, and it failed on a count of close approaches. The remaining gap needs
the homo-oligomeric entries (20) and the misclassified CCDs (7).

**Running it.** The bridge stage re-runs in full, 52,821 entries, because the
bridge rows carry interface residues, PLIP types and buried fractions that are
not in `halves.jsonl` and cannot be reconstructed from it. The contacts=3 state
is preserved in `data/interim/prev-contacts3/` as the comparison baseline and
the rollback, including the whole atlas as it shipped.

**A mistake worth recording.** The first backup copied
`data/interim/bridges.jsonl` and `data/manifests/bridges.jsonl` into one
directory. They share a basename, so the second overwrote the first, and the
originals were then truncated for the clean re-run. It cost nothing, because
every row of the lost file is in the preserved atlas, but it was luck rather
than care: two paths differing only by directory went into one flat backup
without checking. The backup is named by content now.

## D-065: the atlas classed two PROTACs as detergents

**Finding.** `RN3` and `RN6` are bifunctional degraders. Their names carry
`2,6-dioxopiperidin-3-yl` and `1,3-dioxo-isoindol`, which is thalidomide's
glutarimide and phthalimide, joined through an eight-carbon linker to a
`thieno[3,2-f][1,2,4]triazolo[4,3-a][1,4]diazepine` with a 4-chlorophenyl,
which is JQ1. A CRBN-recruiting BET degrader, twice.

BINMAN classed both as **detergent** and set `is_furniture = 1`, because the
linker put the substring "octyl" in the IUPAC name and a name rule matches
`lauryl|dodecyl|octyl|decyl|nonyl|undecyl` anywhere in it.

A Blind-spot INventory of Molecular Adhesives and Neosubstrates filed two
CRBN-recruiting degraders as crystallisation detergent, on a substring of a
linker. That is the most on-the-nose false negative the project could produce,
and nothing failed: furniture is excluded quietly and by design.

**How wide it goes.** 59 CCDs carry `name_rule:detergent`. Splitting them on
aromatic ring count, which is what separates an amphiphile from a drug:

| aromatic rings | n | what they are |
|---:|---:|---|
| 0 | 34 | sugar-head detergents, alkyl chains: correct |
| 1 | 14 | Triton-like: correct |
| 2 or more | **10** | RN3, RN6, 7ED, XKE, RUW, YUX, 8WF, QNO, EVP, TDS |

The ten are PROTACs, alkyl-chain natural products and quinolone signal
molecules. None is a detergent. Genuine detergents are amphiphiles with a simple
head: the largest correctly classed here, a 1,165 Da maltoside, has **zero**
aromatic rings, so size is not the discriminator and ring count is.

**The fix, deferred deliberately.** The alkyl tokens should not fire on a
molecule with two or more aromatic rings. It is not applied yet because the
bridge stage is mid-re-run and classifies as it goes: changing the rule now
would leave entries processed before and after the change classified by
different rules, which is the kind of inconsistency that is very hard to see
later. It goes in once that run finishes.

**And it needs no second geometry run.** Classification depends only on the CCD,
never on the structure, so the classifier can be re-applied on its own and the
`bridge.ccd_class` column updated in place. A 50-minute geometry re-run would
buy nothing.

**Why this one matters beyond its size.** The contact floor (D-064) was rejecting
real glues on a defensible criterion set slightly too tight. This is different:
it is a string match on a chemical name deciding that a degrader is laboratory
plastic. The two metrics it moves, recall and artefact precision, are the two
that were already failing, and both are moved by the same rule in the same
direction.

## D-066: the shipped atlas was missing 18% of its bridges by accident of timing

**Finding, found by re-running the stage cleanly for the first time.** The
contact-floor re-run (D-064) refused 1,043 entries as `too_complex` where the
shipped run refused 235. Comparing like for like over the same entries: **808
went from ok to failed and none went the other way.**

The config and the code were identical in both runs, so the cause was neither.
`max_chain_ligand_pairs = 20000` was introduced partway through the original
multi-session run. Entries processed before it existed went through; entries
processed after did not. **The shipped atlas's coverage depends on when each
entry happened to be processed**, which is why the original manifest both
completed 7SFV at 864,000 chain-ligand pairs and refused others at 20,406.

**What it costs.** Those 808 entries hold **43,961 bridges, 18.4% of the
atlas's 239,485.** The largest are not marginal: 8GYM alone holds 1,828 bridges
over 326 chains and 510 ligands, and completed in 403 seconds.

**Why this had to be fixed before measuring anything.** Had the re-run shipped
as it stood, the atlas would have lost 18% of its bridges and the loss would
have been attributed to the contact threshold, which is the change under
measurement. Two effects, one number, and the confound would have pointed the
wrong way: a relaxation that admits 11.9% more bridges would have appeared to
remove 7% of them.

**The cap is now 900,000**, set just above the largest assembly the original run
completed. It recovers every lost bridge and additionally admits 216 entries the
original refused by the same accident of timing. Above 900,000 adds entries and
no bridges: those are the million-pair assemblies the original refused on
purpose, and they stay refused. It costs about 846 minutes of single-threaded
geometry, an hour across the configured workers.

**It is a work cap, not a science threshold.** It decides which assemblies are
attempted, never which bridges qualify, so it is not a spec 9.6 adjustment and
needs no authorisation. The contact floor (D-064) is the only science change in
this rebuild, which keeps the measurement attributable to one cause.

## D-067: with assayed negatives the metric clears its floor, and the shipped criterion dies

**Finding.** D-054 closed the degradability metric on a stated obstacle: the
negatives were assumed rather than assayed. That obstacle is removed (D-066's
sibling work), and refitting on the same features and the same proteins with
only the labels changed gives a different answer in both directions.

**How wrong the old negatives were.** Over the 10,082 lysines that appear in
both sets, the old labelling called 950 positive and the rest negative. The
assayed data says **4,350 are ubiquitylated and 5,732 are true negatives**. The
two labellings **disagree on 41% of the lysines**. Nearly every disagreement is
a lysine the old set called negative because nobody had annotated it, which is
precisely the bias the metric's own caveat warned about.

**What clears, and what does not.** Within protein, which is the only figure
that cannot be flattered by annotation prevalence (D-054):

| feature set | within-protein AUC |
|---|---:|
| exposure alone, the shipped criterion | **0.5020** |
| every per-lysine feature, boosted | **0.6778** |
| everything including protein-level terms | 0.6834 |

**The shipped criterion is dead, not rescued.** `min_nz_rel_sasa` is a single
exposure threshold, and against assayed negatives lysine exposure is at chance.
Its old 0.546 was partly the biased negative set flattering it: unannotated
lysines skew buried, because buried lysines are also harder to detect by mass
spectrometry, so the old negative set was enriched for exactly the thing the
feature measures.

**And the floor is cleared honestly.** 0.6778 uses per-lysine features only, with
whole proteins held out and the AUC computed inside each protein. The
protein-level terms that carried the old pooled figure add 0.006 now instead of
0.09: with real negatives there is no annotation prevalence left to exploit.

**What this does not yet license.** Spec 5.4's reach window is four numbers, one
exposure threshold and three Cb-Cb boundaries, and this fits none of them. It
shows a *model* clears the floor where a *threshold* cannot. Shipping a verdict
on that basis is a change to what the module emits, not a fit of what the spec
describes, and the three reach boundaries still have no ligand site to be
measured from except in the 89 ternary complexes. Both halves are the next step;
neither is done, and the notice stays until they are.

## D-068: reach from the ligand site does not predict ubiquitylation

**Finding.** The three Cb-Cb reach boundaries of spec 5.4 were fitted for the
first time, on induced ternary geometry, and the variable they rest on is
uninformative. The window cannot be fitted, and the reason is now mechanical
rather than logistical.

**What was measured.** 68 of BINMAN's own ternary complexes, where a ligand
bridges an E3 to a non-E3 partner: CRBN with BRD4 through a PROTAC, DCAF15 with
RBM39, beta-TrCP1 with beta-catenin. 43 survived the checks, giving **369
assayed lysines on substrate chains, 181 of them ubiquitylated**, each measured
from the bridging ligand exactly as spec 5.4 describes.

| variable | AUC |
|---|---:|
| Cb-Cb distance to the ligand site | **0.4223** |
| NZ to ligand centroid | 0.4770 |
| NZ relative SASA | 0.4595 |

Ubiquitylated lysines are **farther** from the ligand than assayed-unmodified
ones: median 18.7 A against 14.9 A. Not noise around 0.5, but slightly inverted.

**Why that is the expected answer, in hindsight.** The ligand site is where the
substrate is *recruited*. It is not where ubiquitin is *transferred*. Transfer
happens at the E2 active site, positioned by the cullin scaffold and RBX1 tens
of angstroms away, and the ligand has no say in it. Distance from the ligand was
never the right geometric variable; distance from the E2 would be, and these
structures almost never contain the E2. Spec 5.4's premise, that reach from the
site predicts which lysine is used, does not survive contact with the geometry
it describes.

**So the degradability window cannot be fitted on any of its four numbers.**
Exposure is at chance against assayed negatives (0.5020, D-067) and all three
reach distances are at or below chance here. What does clear the floor is a
per-lysine *model* at 0.6778, which is a different object from a set of
thresholds.

**Three bugs found on the way, all mine, none of which would have announced
itself.** They are recorded because each produced a confident wrong number
rather than an error:

1. Lysines were measured across every chain, so the ligase's lysines were
   attributed to the substrate's accession. 59 of 68 entries then failed the
   numbering check, which is the only reason it was caught.
2. `cb_cb_distance` returns -1 when no Cb-Cb exists, and that went into the AUC
   where negation makes it the closest possible value.
3. The site was passed as the ligand residue, but the Cb-Cb distance is to the
   nearest *site residue's* CB and a ligand has no CB. Every distance was the
   sentinel, and the first run reported an AUC over a set that was entirely
   sentinel values.

The numbering check that caught the first was written because author numbering
and UniProt numbering disagree often and silently. It earned its place
immediately.

## D-069: the atlas rebuild does not move the language-model metrics

**Checked before it could mislead.** Round 07 is the model to beat (Task B macro
F1 0.9336) and its scores were measured against the pre-rebuild atlas. Today's
rebuild took the atlas from 239,485 bridges to 283,131, and Task A's primary
metric executes queries against that atlas, so the obvious worry is that round
14 would be compared against a baseline measured on different data.

**It does not matter, and that is a measurement rather than an assumption.**
Set equality runs both the predicted query and the gold query against whichever
atlas is present and compares the row sets, so a change to the atlas moves both
sides together. Re-evaluating round 07 on the rebuilt atlas returns every figure
unchanged to four decimal places:

| | parse | set equality | exact | Task B | Task C |
|---|---:|---:|---:|---:|---:|
| round 07, original atlas | 1.0 | 1.0 | 0.975 | 0.9336 | 1.0 |
| round 07, rebuilt atlas | 1.0 | 1.0 | 0.975 | 0.9336 | 1.0 |

So round 14 can be compared against the published round 07 number directly, and
the re-evaluated baseline is kept alongside it in `lm_eval.json` as the evidence
rather than the claim.

**Round 14 completed**: 14,152 iterations, one full epoch, 32 layers, rank 8,
scale 20, batch 2, learning rate 1e-5, on Qwen2.5-32B-Instruct-4bit. This is
genuinely the 32B: D-044 recorded two earlier rounds that reported 32B and
trained the 3B through a default-argument trap, and the adapter config names the
32B model and a 128 MB adapter over 141 checkpoints.

## D-070: the UbiBrowser licence, resolved as far as it can be

**Decision.** `ubibrowser2`'s licence is recorded as **"no terms published by the
source; BINMAN ships derived per-ligase counts, not the interaction records, and
cites the source"**, replacing "not determined". The About page's notice about it
is removed.

**The lookup was exhausted first, because the right fix for an unknown licence
is to find the licence.** Checked today:

* `ubibrowser.bio-it.cn/ubibrowser_v3/` returns HTTP 200 and carries no licence,
  terms, copyright or usage text.
* Its documentation page has a Download section and, again, no terms.
* `/home/help`, `/home/about` and `/home/contact` are all 404.
* Crossref gives 10.1093/nar/gkab962 one licence, CC BY-NC-4.0, with
  `content-version: vor`. That is the article, not the database behind it.

So the source publishes nothing, and no amount of further looking changes that.
"Not determined" was accurate about the source and useless to a reader, because
it describes an absence without saying what the project did about it.

**What is recorded instead is checkable.** The atlas carries
`ligase.substrate_count` and `substrate_count_predicted`, two integers per
ligase. It does not carry the interaction records those counts were derived
from, and `deploy/provision.sh` excludes `data/validation/` entirely, so the
live host holds `data/atlas` alone. Verified on the droplet: `/opt/binman/data`
contains only `atlas`. The source is cited in the references table with its DOI.

That is the same position Marc took on PROTAC-DB: use it, derive from it, cite
it, do not redistribute it, not for profit. It is stated here as what BINMAN
does rather than as a permission the source gave, because the source gave none.

**The notice is removed and the fact is not.** Each reference's licence stays in
the About page's references table, and `reference_summary.licence_not_determined`
stays in the artefact and now reads 0. A future source with no terms will show
in the table and in that count, so removing the banner costs visibility rather
than the record.

## D-071: the 32B does not beat the 3B, so the 3B ships

**Decision.** `round07`, a 3B with the last 32 layers trained, stays the shipped
model. Round 14, a 32B trained for a full epoch on the same corpus, does not
beat it on any metric and is marginally worse on two.

| | parse | set equality | exact | Task B macro F1 | Task C |
|---|---:|---:|---:|---:|---:|
| round 07, 3B, 32 layers | 1.0 | 1.0 | 0.975 | **0.9336** | 1.0 |
| round 14, 32B, 1 epoch | 1.0 | 1.0 | 0.9583 | 0.9253 | 1.0 |

**In samples, which is what decides whether this means anything.** Task B is
**222 of 240 against 224 of 240**: two classifications. Task A exact match is
115 of 120 against 117: two queries. Parse rate, set equality and abstention are
tied at ceiling, where they have been since round 06. Per class the 32B is
slightly behind on crystallisation artefact (0.885 against 0.901) and native
cofactor (0.884 against 0.901) and level on glue and PROTAC.

So the honest statement is not "the 32B is worse". It is that **ten times the
parameters and ten hours of training produce no measurable difference**, and the
difference that exists points the wrong way by an amount a handful of samples
could reverse.

**Why this was worth running anyway.** The ablation that chose round 07's shape
(D-0xx, the depth sweep) showed depth was the lever and that rank and epochs
were not. The open question was whether the lever simply ran out at 3B or kept
going with scale. It ran out. That is a cheaper thing to know than to assume in
either direction, and it closes the loop's stated gate: the best model is the
one already shipped.

**The comparison is like for like.** Round 07 was re-evaluated on the rebuilt
atlas first (D-069) and returned every figure unchanged, so the two rows above
were measured against the same database on the same day with the same harness.

**What the 32B cost.** About ten hours of training, 18 GB of checkpoints and a
128 MB adapter.

**Superseded 2026-10-05 (D-077).** This said the checkpoints could go and the
adapter should stay, so the scale experiment stayed visible. Marc chose to keep
only round 07 and the 32B adapter went with the rest. What survives it is this
decision and the measured rows above, which is the part that carries the
finding: the numbers are here whether or not the weights are.

## D-072

**The degron geometry score is not inverted, despite measuring 0.3498.**

On the called subset of the Sievers assayed C2H2 fingers,
`degron_geometry_score` ranks degraded fingers below non-degraded ones with AUC
0.3498, significantly below chance (20,000-shuffle permutation test, null 95%
band [0.3767, 0.6244], two-sided p = 0.0167, seed 20261005). Inverting it would
read 0.6502, which would beat the sequence model's 0.6368 and clear a floor the
module currently misses.

It has not been inverted. Twenty one positives is not a basis for flipping a
shipped score; the composite is significant while neither measurable component
is (`mean_plddt` p = 0.0775, `tip_rel_sasa` p = 0.0670), which is what low
power looks like; and a score that runs backwards on one screen is a result to
reproduce on a second, not a sign to change. Inverting it here would turn a
measurement into a number chosen because it passes.

What the measurement is good for is deciding where the effort goes: the
geometry composite as weighted carries no usable signal on this benchmark, so
tuning its three weights is not the route to a better AUC. The sequence model
already measures 0.6368 against a geometry score that is worse than guessing.

## D-073

**`regularity` is persisted, and the column ships empty until the scan reruns.**

It is 0.25 of `degron_geometry_score` and was computed, used and discarded, so
a quarter of the shipped score was unauditable from any artefact. It is now
emitted by `pipeline/degron_scan.py`, declared in `pipeline/schema.sql` and
loaded by `pipeline/build_atlas.py`.

The values need a degron rescan over 20,431 proteins. Until that runs the
column exists and is NULL for every row. That is deliberate: a backfill would
have to recompute the DSSP bridge-partner pairing the value comes from, which
is the rescan, and anything cheaper would be a guess in a column whose whole
purpose is to make the score checkable.

## D-074

**The model card describes the served adapter, not the last training run.**

`models/binman-lm/training.json` is overwritten by each training run, and
`pipeline/build_about.py` read its `identity` block as the model card. The last
run was the 32B experiment that was evaluated and rejected, so the About page
published, as the description of the shipped model:

| field | published | actually served |
|---|---|---|
| base model | `mlx-community/Qwen2.5-32B-Instruct-4bit` | `Qwen/Qwen2.5-3B-Instruct` |
| fused | `true` | `false`, a PEFT adapter applied at load |
| shipped adapter | `models/binman-lm/adapters` | `Dellboy/binman-lm-adapter` |

The rank (8) and the layer count (32) matched by coincidence, which is why it
read as plausible. `fused: true` also contradicts FINDINGS.md directly, which
records that fusing produced a model parsing 0 of 10 held-out questions and
that the artefact was deleted rather than shipped.

Nothing was wrong with what serves. The Space loads `Qwen/Qwen2.5-3B-Instruct`
and the adapter repository, and answers correctly; only the description of it
was wrong, and the local `models/binman-lm/adapters` directory has since been
overwritten by the 32B round14 run, so it is no longer what its name implies.

The card now reads `models/binman-lm/served/adapter_config.json`, fetched from
the adapter repository the Space loads, which is the only file in the project
that describes the served model rather than a local experiment. `fused` is not
read from it: a PEFT adapter is applied to the base at load time by
construction, so it is what "serves an adapter" means. training.json is kept
and published as `last_training_run`, under a name that says what it is.

## D-075

**A quarter of the degron geometry score is a constant, measured not inferred.**

`degron_geometry_score` is `0.35 x (pLDDT/100) + 0.40 x tip_rel_sasa + 0.25 x
regularity`. With regularity persisted and measurable for the first time, its
AUC on the called subset of the Sievers assayed fingers is 0.5001, and the
20,000-shuffle permutation test returns a null 95% band of [0.5001, 0.5001].
A band of zero width means the inputs are tied, and they are: 83.3% of all
21,717 candidates sit at exactly 1.0, and the 3,565 called fingers take two
distinct values between them.

The cause is not a bug in the measurement. The hairpin filter admits a
candidate only when its strands are already well paired, so regularity has been
selected to its ceiling before it is scored. The filter and the third term of
the score measure the same property, and the second measurement carries no
information once the first has been applied as a gate.

**The weights are not being rebalanced on this.** Removing the dead term and
renormalising the other two changes no ranking at all, since a constant added
to every row cannot reorder them: it would make the formula honest without
making the score better, and the two surviving terms are themselves inverted
(D-072). A score whose every measurable component is at or below chance does
not need its weights adjusted. It needs a different feature set, which is what
the sequence model at 0.6368 already is.

What this does settle is that weight tuning is not the route to a better degron
AUC, and now on a measurement rather than a suspicion.

## D-076

**The floor is reachable from a monomer, and the window still is not fitted.**

`pipeline/degradability_features.py --assayed` has been run over the
ubiquitylome: 405,207 lysines across 17,974 proteins, 107,653 ubiquitylated and
297,554 assayed and found unmodified. D-067's figures are now in an artefact
rather than in prose, and validate.py reads them instead of restating them.

Exposure alone scores 0.4971 within protein, at chance, reproducing D-067's
0.5020 on thirty-two times the data. A boosted model over the sixteen
per-lysine features scores 0.6662, above the 0.65 floor, from an AlphaFold
monomer alone. Adding protein-level terms moves it to 0.6678, a gain of 0.0016,
so the result does not rest on ranking proteins by annotation prevalence.

**Nothing is shipped on this.** Spec 5.4 defines the reach window as four
thresholds and a model is not four thresholds; emitting its score would answer
a different question from the one the module asks, and the four numbers still
have no fit of their own (D-068). The lysine verdict column stays out.

What it changes is the diagnosis. Until now the degradability module was
blocked by an open question: whether any monomer-derivable signal reaches the
floor at all. It does. What blocks a verdict is the shape spec 5.4 asks for,
not an absence of signal, and that is a different problem with a different
solution.

## D-077

**114.7 GB of model storage deleted; round 07 and the corpus kept.**

`models/` held 114.8 GB and now holds 0.1 GB. Deleted: `models/binman-lm/fused`
(19 GB), every training run except round 07 (59 GB), the
`models/binman-lm/adapters` directory (18 GB), and round 07's own 140
intermediate checkpoints (7 GB). Kept: round 07's final adapter and config, its
wandb record, `adapters-dpo` at 25 MB, and the 22 MB training corpus.

Round 07 is kept because it is what serves and what
`pipeline/triage_predict.py` loads. It was copied aside before anything was
deleted and verified intact after. Nothing in the codebase referenced an
intermediate checkpoint, which is why they could go without a resume path being
lost.

`fused` was already recorded in FINDINGS as an artefact that parsed 0 of 10
held-out questions and "was deleted rather than shipped". It had not been. The
deletion makes the record true.

**This supersedes D-071's retention of the 32B adapter**, and D-071 now says so.
The scale experiment survives as its measured rows rather than its weights.

**Nothing live depends on local weights.** The Space pulls
`Dellboy/binman-lm-adapter` from HuggingFace, so the demo and the
natural-language box were verified answering 200 after the deletion. Two
references to the deleted `models/binman-lm/adapters` path remain, in
`training.json` and in `results.json` 9.5's `adapter` field. Both are records of
runs rather than load paths, and the model card already reads
`models/binman-lm/served/adapter_config.json` instead (D-074).

## D-078

**The triage head fills `evidence_class`, and nothing else in the atlas is a prediction.**

Task B scored 0.9336 macro F1 and was used for nothing: `evidence_class`, which
spec line 467 defines as its label, was NULL on all 285,996 bridge rows.
`pipeline/triage_predict.py` now fills it for the 6,510 entry-ligand pairs whose
ligand is a glue candidate, using round 07 and the prompt shape
`lm/build_task_b.py` trains on.

A separate `predicted_evidence_class` column was written first and reverted. The
spec had already decided where this goes, and putting a second column beside an
empty one meant for the same thing would have been a private design imposed over
a published one. What the column needed was not a different name but a
description that says what produced it, and its FieldSpec now carries one:
"BINMAN-LM triage prediction, not a curated label", with the macro F1 and the
note that every other column is measured. That text reaches the column tooltip
and the query builder.

Inference is its own stage and `build_atlas._post_build` only loads the file it
wrote, so a routine rebuild does not drag a model load into what is otherwise
file IO. One prediction covers every bridge row sharing an entry and a ligand:
the question is about the structure and the ligand, not about which chain pair
the geometry picked.

**Agreement on unseen components is 14 of 15.** The first figure computed was
14.4%, counted per entry-ligand pair, and CYC appears in 119 of the 139
overlapping pairs. A generalisation check has to be counted in the unit the
split was made on, which for Task B is the chemical component.

The single disagreement is CYC, phycocyanobilin. BioLiP curates it as a
crystallisation artefact, the model calls it a native cofactor, and it is a
light-harvesting chromophore. BINMAN's own structural classifier calls it a
glue candidate. Three classifiers disagree and the curated label is the weakest
of the three, so it is recorded rather than corrected: BioLiP is the published
source and overriding it here would be substituting a judgement for a citation.

## D-079

**Geometry and sequence are not combined: the combination measures no gain.**

D-075 left the route open because an inverted feature still carries
information where a model can weight it freely. Measured on the same 5,663
fingers, the same 32 positives, the same gene-grouped repeated protocol and the
same seeds as the sequence model: sequence alone 0.6334, geometry alone 0.5564,
both together 0.6348. The gain from adding geometry is 0.0014, which is 0.02 of
one split-to-split standard deviation.

Two things worth keeping from it. Geometry rises from 0.4407 to 0.5564 once the
weights are free, so the fixed positive weights in `config/thresholds.toml` cost
about 0.12 of AUC by forcing the sign; and geometry is redundant with sequence
rather than complementary to it, which is what two descriptions of the same
domain should be expected to be.

No combined score ships. Adding 189 features to gain 0.02 of a standard
deviation would be complexity bought with nothing.
