# BINMAN build log

One line per meaningful event, timestamped UTC (spec Section 0 rule 5).

| Timestamp | Phase | Event |
|---|---|---|
| 2026-10-03T16:41:48Z | 1.0 | Build started. Spec 1.2 read end to end. Project root confirmed at `/Users/dellboy/Documents/Vibe_Coding/BINMAN`. |
| 2026-10-03T16:41:48Z | 1.0 | Directory tree created: app, pipeline, lm, tools, tests, deploy, data, models, config, docs. |
| 2026-10-03T16:41:48Z | 1.0 | `pixi.toml` written (spec 3.1). First solve failed: fpocket requires `__osx >=14.5`, pixi was solving against a macos=13.0 minimum platform. |
| 2026-10-03T16:41:48Z | 1.0 | `system-requirements.macos = "14.5"` added (DECISIONS D-002). Solve succeeded. |
| 2026-10-03T16:41:48Z | 1.0 | Compute environment verified: gemmi 0.7.5, biotite 1.6.0, rdkit 2026.03.6, mkdssp 4.6.1, fpocket 4.2.3, obabel, plip, freesasa, mlx 0.29.3. |
| 2026-10-03T16:41:48Z | 1.0 | `KMP_DUPLICATE_LIB_OK=TRUE` set: pydssp pulls PyTorch and collides with the numpy OpenMP runtime (DECISIONS D-003). |
| 2026-10-03T16:41:48Z | 1.0 | `pyproject.toml` written for the uv app environment (spec 3.2). |
| 2026-10-03T16:41:48Z | 1.0 | `config/thresholds.toml` written. Every spec Section 5 cutoff is a named constant; the reach window is flagged `fitted = false`. |
| 2026-10-03T16:41:48Z | 1.0 | `tools/hwprobe.py` run. Apple M2 Ultra, 16 performance + 8 efficiency cores, 60 GPU cores, 128 GB unified memory, 1513.7 GB free. MPS available, MLX smoke test passed on GPU. |
| 2026-10-03T16:41:48Z | 1.0 | Derived tuning: cpu_workers 14, io_workers 16, model_device mps, memory_headroom_gb 24. No G1 (MLX passed), no G5 (free space far above the 50 GB floor). |
| 2026-10-03T16:41:48Z | 1.0 | `.claude/settings.json` write refused by the harness as self-modification. Shipped as `deploy/claude-settings.json` instead (DECISIONS D-004). |
| 2026-10-03T16:41:48Z | 1.0 | `git init` on branch `main`. Gate G4 authorised by Marc at build start (DECISIONS D-001). |
| 2026-10-03T16:43:55+00:00 | 1.0 | Vendored 26 front-end files (10613 KB total), 0 failure(s). Manifest at app/static/vendor/VENDOR.json. |
| 2026-10-03T17:04:36+00:00 | 1.0 | Validation datasets: 4/10 resolved (biolip2_annotations, biolip2_artefacts, ubibrowser_literature_e3, ubibrowser_predicted_e3). Manifest at data/validation/MANIFEST.md. |
| 2026-10-03T17:04:36+00:00 | gate | G7 opened: 6 validation dataset(s) could not be obtained automatically: degronopedia, mgdb_glues, mgtbind_ternary, molgluedb_glues, |
| 2026-10-03T17:13:44+00:00 | 1.0 | Validation datasets: 4/10 resolved (biolip2_annotations, biolip2_artefacts, ubibrowser_literature_e3, ubibrowser_predicted_e3). Manifest at data/validation/MANIFEST.md. |
| 2026-10-03T17:13:44+00:00 | gate | G7 opened: 6 validation dataset(s) could not be obtained automatically: degronopedia, mgdb_glues, mgtbind_ternary, molgluedb_glues, |
| 2026-10-03T17:18:13+00:00 | 1.0 | Validation datasets: 4/10 resolved (biolip2_annotations, biolip2_artefacts, ubibrowser_literature_e3, ubibrowser_predicted_e3). Manifest at data/validation/MANIFEST.md. |
| 2026-10-03T17:18:13+00:00 | gate | G7 opened: 6 validation dataset(s) could not be obtained automatically: degronopedia, mgdb_glues, mgtbind_ternary, molgluedb_glues, |
