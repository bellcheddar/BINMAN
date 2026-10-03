# BINMAN progress

Rewritten after every phase and at least every 30 minutes during long compute.

Last updated: see BUILD_LOG.md for the authoritative timestamp.

## Phase 1: Foundations and the Glue Atlas

| Step | State | Notes |
|---|---|---|
| 1.0 Hardware probe | **done** | M2 Ultra, 16P/8E cores, 60 GPU cores, 128 GB, 1513 GB free. MPS and MLX both pass. |
| 1.0 pixi compute env | **done** | gemmi 0.7.5, biotite 1.6.0, rdkit 2026.03.6, mkdssp 4.6.1, fpocket 4.2.3, obabel, plip, freesasa, mlx 0.29.3 |
| 1.0 uv app env | **done** | `pyproject.toml` written |
| 1.0 Vendored front-end | **done** | Mol* 5.12.0, D3 7.9.0, Plotly 2.35.2, Tabulator 6.3.1, 3 self-hosted fonts. 26 files, 10.6 MB. |
| 1.0 Thresholds config | **done** | Every spec Section 5 cutoff named. Reach window flagged `fitted = false`. |
| 1.0 Validation datasets | **partial** | 4 of 10 resolved. G7 open, non-blocking. See `data/validation/MANIFEST.md`. |
| 1.0 Geometry core | **done** | Validated on 5 canonical glues. See FINDINGS.md. |
| 1.0 Smoke test and budget | pending | |
| 1.1 Catalogue | pending | 52,821 candidate entries counted from the RCSB Search API. |
| 1.2 Download and prepare | pending | |
| 1.3 Geometry run | pending | |
| 1.4 Classification | pending | |
| 1.5 Trimmed structures | pending | |

## Phase 2: Degron Scan, E3 Triage and Degradability

Not started.

## Phase 3: BINMAN-LM

Not started.

## Phase 4: App, QC and delivery

Not started.

## Open gates

| Gate | State | What is needed |
|---|---|---|
| G4 Publish | **authorised** | Granted by Marc at build start (DECISIONS D-001). |
| G7 Dataset access | **open, non-blocking** | 6 validation datasets need a manual download. See `GATE_OPEN.md`. |
| G1 Compute | not open | MLX smoke test passed on GPU. |
| G5 Disk | not open | 1513 GB free against a 50 GB floor. |
| G2 Secrets | not open | No credential needed so far. |
| G3 Deploy | not open | Reached at the end of Phase 4. Deploy scripts written, never executed. |
| G6 Science | not open | No Section 9 metric has missed a floor yet. |
