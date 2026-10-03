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
