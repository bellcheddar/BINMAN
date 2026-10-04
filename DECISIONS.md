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
