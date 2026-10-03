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
| 2026-10-03T17:26:39+00:00 | gate | G6 opened: Spec 9.1 artefact precision measures 0.927 on a held-out half of BioLiP2's artefact ligand list, against a 0.95 floor. D |
| 2026-10-03T17:27:30+00:00 | 1.1 | Tier 1 seed: 5,795 entries referenced by the resolved validation datasets plus the spec 12.3 reference list. |
| 2026-10-03T17:27:30+00:00 | 1.1 | RCSB Search API: 52,821 entries with >= 2 polymer entities and >= 1 non-polymer entity. |
| 2026-10-03T17:27:31+00:00 | 1.1 | Retrieved 300 candidate identifiers. |
| 2026-10-03T17:27:34+00:00 | 1.1 | Catalogue written: 300 entries. Tier counts: {1: 4, 2: 213, 3: 83}. |
| 2026-10-03T17:28:28+00:00 | 1.3 | Bridge run starting: 60 entries pending of 301 catalogued (tiers 1 to 3), 16 IO workers, 14 geometry workers. |
| 2026-10-03T17:28:40+00:00 | 1.3 | Bridge run finished: 60 entries in 0.2 min, 427 bridges, 0 failed, 5.1 entries/s. |
| 2026-10-03T17:28:58+00:00 | 1.0 | Smoke test and budget projection: 60 entries through the full geometry path (download, gemmi parse, FreeSASA dSASA, contact grid, CCD classification) in 11.8 s wall clock = 5.1 entries/s with 16 IO and 14 geometry workers. 427 bridges found, 0 failures, 76 CCD codes classified. |
| 2026-10-03T17:28:58+00:00 | 1.0 | Projection for the full tier 1 to 3 queue (52,821 entries): 2.9 h against MAX_COMPUTE_HOURS of 96. No scope reduction needed, G1 not opened. |
| 2026-10-03T17:28:59+00:00 | 1.1 | Tier 1 seed: 5,795 entries referenced by the resolved validation datasets plus the spec 12.3 reference list. |
| 2026-10-03T17:28:59+00:00 | 1.1 | RCSB Search API: 52,821 entries with >= 2 polymer entities and >= 1 non-polymer entity. |
| 2026-10-03T17:29:01+00:00 | 1.1 | Retrieved 52,821 candidate identifiers. |
| 2026-10-03T17:29:12+00:00 | 1.1 | Metadata fetched for 2,000 of 52,821 entries. |
| 2026-10-03T17:29:26+00:00 | 1.1 | Metadata fetched for 4,000 of 52,821 entries. |
| 2026-10-03T17:29:40+00:00 | 1.1 | Metadata fetched for 6,000 of 52,821 entries. |
| 2026-10-03T17:29:54+00:00 | 1.1 | Metadata fetched for 8,000 of 52,821 entries. |
| 2026-10-03T17:30:09+00:00 | 1.1 | Metadata fetched for 10,000 of 52,821 entries. |
| 2026-10-03T17:30:23+00:00 | 1.1 | Metadata fetched for 12,000 of 52,821 entries. |
| 2026-10-03T17:30:38+00:00 | 1.1 | Metadata fetched for 14,000 of 52,821 entries. |
| 2026-10-03T17:30:56+00:00 | 1.1 | Metadata fetched for 16,000 of 52,821 entries. |
| 2026-10-03T17:31:21+00:00 | 1.1 | Metadata fetched for 18,000 of 52,821 entries. |
| 2026-10-03T17:31:49+00:00 | 1.1 | Metadata fetched for 20,000 of 52,821 entries. |
| 2026-10-03T17:32:18+00:00 | 1.1 | Metadata fetched for 22,000 of 52,821 entries. |
| 2026-10-03T17:32:45+00:00 | 1.1 | Metadata fetched for 24,000 of 52,821 entries. |
| 2026-10-03T17:33:14+00:00 | 1.1 | Metadata fetched for 26,000 of 52,821 entries. |
| 2026-10-03T17:33:42+00:00 | 1.1 | Metadata fetched for 28,000 of 52,821 entries. |
| 2026-10-03T17:34:13+00:00 | 4.3 | Atlas built: 300 entries, 427 bridges (0 novel), 183 ligands, 0 degrons, 0 ligases, 0 lysines, 0.6 MB. |
| 2026-10-03T17:34:21+00:00 | 1.1 | Metadata fetched for 30,000 of 52,821 entries. |
| 2026-10-03T17:34:53+00:00 | 1.1 | Metadata fetched for 32,000 of 52,821 entries. |
| 2026-10-03T17:35:25+00:00 | 1.1 | Metadata fetched for 34,000 of 52,821 entries. |
| 2026-10-03T17:35:55+00:00 | 1.1 | Metadata fetched for 36,000 of 52,821 entries. |
| 2026-10-03T17:36:26+00:00 | 1.1 | Metadata fetched for 38,000 of 52,821 entries. |
| 2026-10-03T17:36:57+00:00 | 1.1 | Metadata fetched for 40,000 of 52,821 entries. |
| 2026-10-03T17:37:33+00:00 | 1.1 | Metadata fetched for 42,000 of 52,821 entries. |
| 2026-10-03T17:37:59+00:00 | 1.1 | Metadata fetched for 44,000 of 52,821 entries. |
| 2026-10-03T17:38:22+00:00 | 1.1 | Metadata fetched for 46,000 of 52,821 entries. |
| 2026-10-03T17:38:46+00:00 | 1.1 | Metadata fetched for 48,000 of 52,821 entries. |
| 2026-10-03T17:39:11+00:00 | 1.1 | Metadata fetched for 50,000 of 52,821 entries. |
| 2026-10-03T17:39:38+00:00 | 1.1 | Metadata fetched for 52,000 of 52,821 entries. |
| 2026-10-03T17:39:50+00:00 | 1.1 | Catalogue written: 52,821 entries. Tier counts: {1: 902, 2: 34539, 3: 17380}. |
| 2026-10-03T17:39:52+00:00 | 1.3 | Bridge run starting: 52,761 entries pending of 52,822 catalogued (tiers 1 to 3), 16 IO workers, 14 geometry workers. |
| 2026-10-03T17:43:35+00:00 | 12.3 | references.bib: 41 references, 32 Crossref verified, 9 unverified, 6 with no DOI, 2 with licence not determined. |
| 2026-10-03T17:46:36+00:00 | 12.3 | references.bib: 44 references, 37 Crossref matched by search (0 preprints), 7 unmatched, 7 with no DOI, 2 with licence not determined. |
| 2026-10-03T17:46:58+00:00 | 12.3 | references.bib: 44 references, 38 Crossref matched by search (0 preprints), 6 unmatched, 6 with no DOI, 2 with licence not determined. |
| 2026-10-03T17:47:18+00:00 | 12.3 | references.bib: 44 references, 37 Crossref matched by search (0 preprints), 7 unmatched, 7 with no DOI, 2 with licence not determined. |
| 2026-10-03T17:47:30+00:00 | 12.3 | references.bib: 44 references, 38 Crossref matched by search (0 preprints), 6 unmatched, 6 with no DOI, 2 with licence not determined. |
