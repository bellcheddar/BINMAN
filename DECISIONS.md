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
