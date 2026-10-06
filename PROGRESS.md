# BINMAN progress

Rewritten after every phase and at least every 30 minutes during long compute.
See `BUILD_LOG.md` for the timestamped event log.

## Headline state

| | |
|---|---|
| Phases complete | 1, 2 and 3 built; 4 built and QC'd |
| Atlas | 52,821 entries, 239,485 bridges, 21,717 degrons, 650 ligases, 30,057 edges, 142.5 MB |
| Section 9 floors measured and passed | E3 enrichment p = 0.0024, pocket coverage 0.982, LM set equality 0.98, LM fabrication rate 0.00 |
| Section 9 floors measured and missed | 4, all Gate G6 and all diagnosed: glue recall 0.772 against 0.85 (D-027), artefact precision 0.939 against 0.95, degron sensitivity 0.656 against 0.70 and specificity 0.353 against 0.60 (D-024) |
| Section 9 metrics not computed | 4, each with the dataset that is missing (Gate G7): packing specificity, substrate Spearman, degradability AUC and its split assertion |
| QC | 24 screenshots, 0 console errors, 0 serious or critical axe violations |
| Tests | 77 passing |
| Trimmed structures | 3,839 files, 553 MB, inside the 2.5 GB budget |
| Repository | public at github.com/bellcheddar/BINMAN |

## Phase 1: Foundations and the Glue Atlas

| Step | State | Notes |
|---|---|---|
| 1.0 Hardware probe | **done** | M2 Ultra, 16P/8E cores, 60 GPU cores, 128 GB. MPS and MLX pass. |
| 1.0 Environments | **done** | pixi compute, uv app. gemmi, freesasa, mkdssp 4.6.1, fpocket 4.2.3, plip, rdkit, mlx. |
| 1.0 Vendored front-end | **done** | Mol* 5.12.0, D3 7.9.0, Plotly 2.35.2, Tabulator 6.3.1, 3 self-hosted fonts. |
| 1.0 Validation datasets | **partial** | 10 of 12 resolved. Outstanding: DEGRONOPEDIA and ProtCID, neither of which publishes a bulk route (D-023). G7 open, non-blocking. |
| 1.0 Smoke test and budget | **done** | 5.1 entries/s measured, 2.9 h projected against a 96 h budget. No G1. |
| 1.1 Catalogue | **done** | 52,821 entries. Tier 1 902, tier 2 34,539, tier 3 17,380. |
| 1.2 Download and prepare | **done** | 52,821 entries; 235 skipped by the work cap (D-017). |
| 1.3 Geometry | **done** | 239,485 bridges, 23,054 with a glue-candidate ligand. |
| 1.4 Classification | **done** | 9,962 components classified; furniture classified, not deleted. |
| 1.5 Trimmed structures | **done** | 3,839 files, wired into 18,508 bridge rows. |

## Phase 2: Degron Scan, E3 Triage and Degradability

| Step | State | Notes |
|---|---|---|
| 2.1 Degron scan | **done** | 20,279 proteins scanned, 21,717 candidates over 8,983 proteins, 570 failed. Thresholds calibrated (D-010), tip definition corrected (D-011); 3 of 5 documented degrons recovered. |
| 2.2 E3 triage | **done** | 650 ligases, 638 with a pocket score (0.982 coverage). Repertoire bug found and fixed (D-012). |
| 2.3 Degradability | **done for geometry** | 1,650 lysines measured. **No verdicts**: the reach window is unfitted because the diGly data is unavailable, which is the spec-mandated behaviour. |
| 2.4 Edge table | **done** | 16,235 edges. Curated E3 edges fill as the ligase table grows. |
| 2.5 FINDINGS v1 | **done** | Every number carries its method and its n. |

## Phase 3: BINMAN-LM

| Step | State | Notes |
|---|---|---|
| 3.0 Baseline first | **done** | Mandatory, run before training: parse 0.283, set equality 0.233, below the 0.85 skip threshold. |
| 3.1 Base model | **done** | Qwen2.5-3B-Instruct 4-bit via mlx-lm. Not gated, so no G2. |
| 3.2 Task A corpus | **done** | 6,000 generated, 6,000 parser-validated, zero label noise. |
| 3.3 Preference pairs | **done** | 1,400, exactly 200 per corruption mode. |
| 3.4 Task B corpus | **not built** | 3 of 5 classes have no published label source. Reported, not substituted. |
| 3.5 Task C corpus | **done** | 980 abstention pairs. |
| 3.6 External query set | **done** | 15 queries, 12 with harvested phrasing, 3 flagged as the project's own. |
| 3.7 Training | **done** | Round 04 ships (SFT on the complete atlas). Both DPO rounds rejected by the generation guard. |
| 3.8 Evaluation | **done** | Synthetic set equality 0.98 (floor 0.90). External not computed: no answerable externally-phrased question survived the harvest. |
| 3.9 Serving | **done** | `deploy/serve_lm.sh`. The app is fully functional with `BINMAN_LM_URL` unset. |

## Phase 4: App, QC and delivery

| Step | State | Notes |
|---|---|---|
| 4.1 Flask app | **done** | Depot design system, split ledger, header triangle, lens graph, 5 Mol* viewers, About tab. |
| 4.1b About generator | **done** | Generated from artefacts; "not recorded" where a value cannot be read. |
| 4.2 Shared selection | **done** | Verified by QC: pinning propagates across modules and deep-links by URL fragment. |
| 4.3 Atlas bundle | **done** | 75.7 MB against a 2.5 GB budget. |
| 4.4 QC | **done** | 24 screenshots, 0 console errors, 0 serious or critical axe violations. |
| 4.5 Icons | **done** | Blog mark via the house skill; an independent favicon, legible at 16px, apple-touch-icon opaque. |
| 4.6 README | **done** | Forged to house standard; source kept re-runnable. |
| 4.7 Deploy scripts | **done, not executed** | `rsync.sh` refuses to run without explicit confirmation. G3 open. |

## Gates

| Gate | State | Blocks? |
|---|---|---|
| G1 Compute | never opened | MLX passed on GPU; projection 2.9 h against 96 h. |
| G2 Secrets | never opened | The base model is not gated; W&B credential already in `~/.netrc`. |
| G3 Deploy | **open** | **yes, by design.** Needs approval, DNS, nginx, certbot. |
| G4 Publish | **authorised** | Granted at build start. Repository is public. |
| G5 Disk | never opened | 1.4 TB free against a 50 GB floor. |
| G6 Science | **open** | no. Artefact precision 0.945 against 0.95, diagnosed. |
| G7 Dataset access | **open** | no. 6 datasets need a manual download. |

## Nothing is still running

All four phases are complete. The final sequence ran in order: full geometry,
full degron scan, trimmed structures, atlas rebuild, corpus regeneration against
the complete atlas, retrain, final evaluation, validation, About regeneration,
tests and QC.

## What a reader should look at first

1. `FINDINGS.md`, which states every number with its method and its n, and says
   plainly which metrics could not be computed and why.
2. `GATE_OPEN.md`, which carries the one open gate, G7, and the decision it needs.
3. `DECISIONS.md`, 92 entries, each with the alternatives considered and how to
   reverse it.
