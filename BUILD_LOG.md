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
| 2026-10-03T17:49:27+00:00 | 1.3 | Bridge run starting: 52,761 entries pending of 52,822 catalogued (tiers 1 to 3), 16 IO workers, 14 geometry workers. |
| 2026-10-03T17:50:30+00:00 | 1.3 | Bridge run starting: 80 entries pending of 52,822 catalogued (tiers 1 to 1), 16 IO workers, 14 geometry workers. |
| 2026-10-03T17:50:33+00:00 | 1.3 | Bridge run finished: 80 entries in 0.0 min, 23 bridges, 0 failed, 31.3 entries/s. |
| 2026-10-03T17:50:41+00:00 | 1.3 | Bridge run starting: 52,681 entries pending of 52,822 catalogued (tiers 1 to 3), 16 IO workers, 14 geometry workers. |
| 2026-10-03T17:52:45+00:00 | 4.1b | About tab generated: 51 references, 4/10 datasets resolved, worked example selected, 2 value(s) not recorded. |
| 2026-10-03T17:55:41+00:00 | 1.3 | 5,957/52,681 entries, 7,049 bridges, 0 failed, 19.9 entries/s, ~0.7 h remaining. |
| 2026-10-03T17:56:49+00:00 | 2.2 | UniProt keyword KW-0833 cross-check set: 755 reviewed human proteins. |
| 2026-10-03T17:56:53+00:00 | 2.2 | InterPro IPR001841 (RING): 296 human reviewed proteins. |
| 2026-10-03T17:57:23+00:00 | 2.2 | InterPro IPR000569 (HECT): 28 human reviewed proteins. |
| 2026-10-03T17:57:24+00:00 | 2.2 | InterPro IPR002867 (RBR): 14 human reviewed proteins. |
| 2026-10-03T17:57:26+00:00 | 2.2 | InterPro IPR001810 (F-box): 67 human reviewed proteins. |
| 2026-10-03T17:57:48+00:00 | 2.2 | InterPro IPR000210 (BTB): 178 human reviewed proteins. |
| 2026-10-03T17:57:54+00:00 | 2.2 | InterPro IPR001496 (SOCS-box): 38 human reviewed proteins. |
| 2026-10-03T17:57:56+00:00 | 2.2 | InterPro IPR003613 (U-box): 9 human reviewed proteins. |
| 2026-10-03T17:57:57+00:00 | 2.2 | InterPro IPR001373 (Cullin): 9 human reviewed proteins. |
| 2026-10-03T17:57:59+00:00 | 2.2 | InterPro IPR024991 (APC-C): 1 human reviewed proteins. |
| 2026-10-03T17:57:59+00:00 | 2.2 | Repertoire: 625 ligases from 9 InterPro signatures, 389 also carrying the KW-0833 keyword. Per family: {'RING': 296, 'HECT': 28, 'RBR': 14, 'F-box': 67, 'BTB': 178, 'SOCS-box': 38, 'U-box': 9, 'Cullin': 9, 'APC-C': 1}. |
| 2026-10-03T17:57:59+00:00 | 2.2 | UbiBrowser substrate counts loaded: 445 E3s with curated substrates, 588 with predicted. |
| 2026-10-03T18:00:42+00:00 | 1.3 | 8,197/52,681 entries, 7,844 bridges, 0 failed, 13.7 entries/s, ~0.9 h remaining. |
| 2026-10-03T18:01:15+00:00 | 2.2 | E3 triage complete: 6 ligases, 0 with a pocket score (coverage 0.000, floor 0.8). Notes: {'structure_download_failed:FileNotFoundError': 6, 'open_targets_failed:RuntimeError': 6}. |
| 2026-10-03T18:02:31+00:00 | 2.2 | UniProt keyword KW-0833 cross-check set: 755 reviewed human proteins. |
| 2026-10-03T18:02:31+00:00 | 2.2 | InterPro IPR001841 (RING): 296 human reviewed proteins. |
| 2026-10-03T18:02:31+00:00 | 2.2 | InterPro IPR000569 (HECT): 28 human reviewed proteins. |
| 2026-10-03T18:02:31+00:00 | 2.2 | InterPro IPR002867 (RBR): 14 human reviewed proteins. |
| 2026-10-03T18:02:31+00:00 | 2.2 | InterPro IPR001810 (F-box): 67 human reviewed proteins. |
| 2026-10-03T18:02:31+00:00 | 2.2 | InterPro IPR000210 (BTB): 178 human reviewed proteins. |
| 2026-10-03T18:02:31+00:00 | 2.2 | InterPro IPR001496 (SOCS-box): 38 human reviewed proteins. |
| 2026-10-03T18:02:31+00:00 | 2.2 | InterPro IPR003613 (U-box): 9 human reviewed proteins. |
| 2026-10-03T18:02:31+00:00 | 2.2 | InterPro IPR001373 (Cullin): 9 human reviewed proteins. |
| 2026-10-03T18:02:31+00:00 | 2.2 | InterPro IPR024991 (APC-C): 1 human reviewed proteins. |
| 2026-10-03T18:02:31+00:00 | 2.2 | Repertoire: 625 ligases from 9 InterPro signatures, 389 also carrying the KW-0833 keyword. Per family: {'RING': 296, 'HECT': 28, 'RBR': 14, 'F-box': 67, 'BTB': 178, 'SOCS-box': 38, 'U-box': 9, 'Cullin': 9, 'APC-C': 1}. |
| 2026-10-03T18:02:31+00:00 | 2.2 | UbiBrowser substrate counts loaded: 445 E3s with curated substrates, 588 with predicted. |
| 2026-10-03T18:03:40+00:00 | 2.2 | E3 triage complete: 8 ligases, 2 with a pocket score (coverage 0.250, floor 0.8). Notes: {'fpocket': 2, 'open_targets_failed:RuntimeError': 2}. |
| 2026-10-03T18:04:36+00:00 | 2.2 | UniProt keyword KW-0833 cross-check set: 755 reviewed human proteins. |
| 2026-10-03T18:04:36+00:00 | 2.2 | InterPro IPR001841 (RING): 296 human reviewed proteins. |
| 2026-10-03T18:04:36+00:00 | 2.2 | InterPro IPR000569 (HECT): 28 human reviewed proteins. |
| 2026-10-03T18:04:36+00:00 | 2.2 | InterPro IPR002867 (RBR): 14 human reviewed proteins. |
| 2026-10-03T18:04:36+00:00 | 2.2 | InterPro IPR001810 (F-box): 67 human reviewed proteins. |
| 2026-10-03T18:04:36+00:00 | 2.2 | InterPro IPR000210 (BTB): 178 human reviewed proteins. |
| 2026-10-03T18:04:36+00:00 | 2.2 | InterPro IPR001496 (SOCS-box): 38 human reviewed proteins. |
| 2026-10-03T18:04:36+00:00 | 2.2 | InterPro IPR003613 (U-box): 9 human reviewed proteins. |
| 2026-10-03T18:04:36+00:00 | 2.2 | InterPro IPR001373 (Cullin): 9 human reviewed proteins. |
| 2026-10-03T18:04:36+00:00 | 2.2 | InterPro IPR024991 (APC-C): 1 human reviewed proteins. |
| 2026-10-03T18:04:36+00:00 | 2.2 | Repertoire: 625 ligases from 9 InterPro signatures, 389 also carrying the KW-0833 keyword. Per family: {'RING': 296, 'HECT': 28, 'RBR': 14, 'F-box': 67, 'BTB': 178, 'SOCS-box': 38, 'U-box': 9, 'Cullin': 9, 'APC-C': 1}. |
| 2026-10-03T18:04:36+00:00 | 2.2 | UbiBrowser substrate counts loaded: 445 E3s with curated substrates, 588 with predicted. |
| 2026-10-03T18:04:56+00:00 | 2.2 | E3 triage complete: 10 ligases, 10 with a pocket score (coverage 1.000, floor 0.8). Notes: {'fpocket': 10, 'open_targets': 10}. |
| 2026-10-03T18:05:06+00:00 | 2.2 | UniProt keyword KW-0833 cross-check set: 755 reviewed human proteins. |
| 2026-10-03T18:05:06+00:00 | 2.2 | InterPro IPR001841 (RING): 296 human reviewed proteins. |
| 2026-10-03T18:05:06+00:00 | 2.2 | InterPro IPR000569 (HECT): 28 human reviewed proteins. |
| 2026-10-03T18:05:06+00:00 | 2.2 | InterPro IPR002867 (RBR): 14 human reviewed proteins. |
| 2026-10-03T18:05:06+00:00 | 2.2 | InterPro IPR001810 (F-box): 67 human reviewed proteins. |
| 2026-10-03T18:05:06+00:00 | 2.2 | InterPro IPR000210 (BTB): 178 human reviewed proteins. |
| 2026-10-03T18:05:06+00:00 | 2.2 | InterPro IPR001496 (SOCS-box): 38 human reviewed proteins. |
| 2026-10-03T18:05:06+00:00 | 2.2 | InterPro IPR003613 (U-box): 9 human reviewed proteins. |
| 2026-10-03T18:05:06+00:00 | 2.2 | InterPro IPR001373 (Cullin): 9 human reviewed proteins. |
| 2026-10-03T18:05:06+00:00 | 2.2 | InterPro IPR024991 (APC-C): 1 human reviewed proteins. |
| 2026-10-03T18:05:06+00:00 | 2.2 | Repertoire: 625 ligases from 9 InterPro signatures, 389 also carrying the KW-0833 keyword. Per family: {'RING': 296, 'HECT': 28, 'RBR': 14, 'F-box': 67, 'BTB': 178, 'SOCS-box': 38, 'U-box': 9, 'Cullin': 9, 'APC-C': 1}. |
| 2026-10-03T18:05:06+00:00 | 2.2 | UbiBrowser substrate counts loaded: 445 E3s with curated substrates, 588 with predicted. |
| 2026-10-03T18:05:42+00:00 | 1.3 | 10,433/52,681 entries, 8,786 bridges, 0 failed, 11.6 entries/s, ~1.0 h remaining. |
| 2026-10-03T18:07:04+00:00 | 2.1 | Human reviewed proteome: 20,431 accessions. |
| 2026-10-03T18:07:04+00:00 | 2.1 | Degron scan: 25 accessions pending, 16 IO workers, 14 DSSP workers. |
| 2026-10-03T18:07:22+00:00 | 2.1 | Degron scan complete: 25 proteins scanned, 12 candidate degrons written, 0 failed. |
| 2026-10-03T18:10:42+00:00 | 1.3 | 12,735/52,681 entries, 10,923 bridges, 0 failed, 10.6 entries/s, ~1.0 h remaining. |
| 2026-10-03T18:11:43+00:00 | 2.2 | 50/625 ligases processed. Notes: {'fpocket': 40, 'open_targets': 38, 'open_targets_no_expression': 2}. |
| 2026-10-03T18:12:30+00:00 | 2.1 | Human reviewed proteome: 20,431 accessions. |
| 2026-10-03T18:12:30+00:00 | 2.1 | Degron scan: 20,431 accessions pending, 16 IO workers, 14 DSSP workers. |
| 2026-10-03T18:14:43+00:00 | 2.2 | 100/625 ligases processed. Notes: {'fpocket': 87, 'open_targets': 87, 'open_targets_no_expression': 3, 'structure_download_failed:FileNotFoundError': 3}. |
| 2026-10-03T18:14:47+00:00 | 2.3 | Reach window NOT fitted: no diGly site data (G7). No verdict column is produced, and the spec 1.0 starting values remain flagged unfitted. |
| 2026-10-03T18:14:47+00:00 | 2.3 | Degradability: 12 glue-candidate bridges to measure. |
| 2026-10-03T18:14:54+00:00 | 2.3 | Degradability complete: 1,650 lysines over 12 sites, 0 failed. Verdicts assigned: 0 (0 is expected and correct while the reach window is unfitted). |
| 2026-10-03T18:15:31+00:00 | 2.4 | Edge table built: 11,022 edges (21 bridged_by, 0 curated ubiquitylates, 11,001 predicted, 0 has_degron). |
| 2026-10-03T18:15:42+00:00 | 1.3 | 15,040/52,681 entries, 14,540 bridges, 0 failed, 10.0 entries/s, ~1.0 h remaining. |
| 2026-10-03T18:17:11+00:00 | 2.2 | 150/625 ligases processed. Notes: {'fpocket': 136, 'open_targets': 134, 'open_targets_no_expression': 5, 'structure_download_failed:FileNotFoundError': 4, 'no_ensembl_gene_id': 1}. |
| 2026-10-03T18:17:13+00:00 | 4.3 | Atlas built: 52,821 entries, 16,179 bridges (novel set not determinable: no curated glue database resolved (G7)), 9,952 ligands, 12 degrons, 10 ligases, 1,650 lysines, 60.4 MB. |
| 2026-10-03T18:17:13+00:00 | 9 | Validation run against binman.sqlite: 16 metric(s) not computed (dataset unavailable), 0 measured floor(s) missed. |
| 2026-10-03T18:17:30+00:00 | 2.1 | 503/20,431 scanned, 547 candidates, 18 failed, 1.7/s, ~3.3 h remaining. |
| 2026-10-03T18:20:42+00:00 | 1.3 | 17,352/52,681 entries, 17,640 bridges, 0 failed, 9.6 entries/s, ~1.0 h remaining. |
| 2026-10-03T18:21:34+00:00 | 2.2 | 200/625 ligases processed. Notes: {'fpocket': 184, 'open_targets': 184, 'open_targets_no_expression': 5, 'structure_download_failed:FileNotFoundError': 6, 'no_ensembl_gene_id': 1}. |
| 2026-10-03T18:22:30+00:00 | 2.1 | 1,017/20,431 scanned, 1,092 candidates, 37 failed, 1.7/s, ~3.2 h remaining. |
| 2026-10-03T18:22:46+00:00 | 3.2 | Corpus grounding: 28 numeric field ranges read from the atlas, vocabularies {'ccd_id': 4000, 'ccd_class': 11, 'ligase_gene': 10, 'ligase_acc': 10, 'ligase_family': 2, 'verdict': 0, 'evidence_class': 0, 'motif_family': 1, 'method': 15}. |
| 2026-10-03T18:22:46+00:00 | 3.2 | Task A generated 6,000 pairs, 6,000 validated by the app parser, 0 rejected and dropped (the corpus therefore has zero label noise by construction). |
| 2026-10-03T18:22:46+00:00 | 3.2 | Corpus written: Task A 4,837/550/613, 1,400 preference pairs across 7 modes, Task C 784 train. Task B buildable: False. |
| 2026-10-03T18:23:26+00:00 | 3.2 | Corpus grounding: 28 numeric field ranges read from the atlas, vocabularies {'ccd_id': 4000, 'ccd_class': 11, 'ligase_gene': 10, 'ligase_acc': 10, 'ligase_family': 2, 'verdict': 0, 'evidence_class': 0, 'motif_family': 1, 'method': 15}. |
| 2026-10-03T18:23:26+00:00 | 3.2 | Task A generated 6,000 pairs, 6,000 validated by the app parser, 0 rejected and dropped (the corpus therefore has zero label noise by construction). |
| 2026-10-03T18:23:26+00:00 | 3.2 | Corpus written: Task A 4,817/568/615, 1,400 preference pairs across 7 modes, Task C 784 train. Task B buildable: False. |
| 2026-10-03T18:25:42+00:00 | 1.3 | 19,087/52,681 entries, 19,761 bridges, 0 failed, 9.1 entries/s, ~1.0 h remaining. |
| 2026-10-03T18:26:52+00:00 | 2.2 | 250/625 ligases processed. Notes: {'fpocket': 234, 'open_targets': 234, 'open_targets_no_expression': 5, 'structure_download_failed:FileNotFoundError': 6, 'no_ensembl_gene_id': 1}. |
| 2026-10-03T18:27:30+00:00 | 2.1 | 1,533/20,431 scanned, 1,727 candidates, 57 failed, 1.7/s, ~3.1 h remaining. |
| 2026-10-03T18:30:42+00:00 | 1.3 | 20,571/52,681 entries, 23,057 bridges, 0 failed, 8.6 entries/s, ~1.0 h remaining. |
| 2026-10-03T18:32:13+00:00 | 2.2 | 300/625 ligases processed. Notes: {'fpocket': 283, 'open_targets': 283, 'open_targets_no_expression': 5, 'structure_download_failed:FileNotFoundError': 7, 'no_ensembl_gene_id': 2}. |
| 2026-10-03T18:32:30+00:00 | 2.1 | 2,044/20,431 scanned, 2,237 candidates, 75 failed, 1.7/s, ~3.0 h remaining. |
| 2026-10-03T18:32:34+00:00 | 3.0 | baseline: loading mlx-community/Qwen2.5-3B-Instruct-4bit zero-shot |
| 2026-10-03T18:34:28+00:00 | 3.0 | baseline: parse rate 0.2833, set equality 0.2333 on 60 synthetic queries. |
| 2026-10-03T18:34:49+00:00 | 2.2 | 350/625 ligases processed. Notes: {'fpocket': 333, 'open_targets': 332, 'open_targets_no_expression': 5, 'structure_download_failed:FileNotFoundError': 7, 'no_ensembl_gene_id': 3}. |
| 2026-10-03T18:35:42+00:00 | 1.3 | 22,734/52,681 entries, 28,284 bridges, 0 failed, 8.4 entries/s, ~1.0 h remaining. |
| 2026-10-03T18:37:31+00:00 | 2.1 | 2,550/20,431 scanned, 2,829 candidates, 105 failed, 1.7/s, ~2.9 h remaining. |
| 2026-10-03T18:37:40+00:00 | 3.6 | Europe PMC harvest: 463 candidate question sentences from open-access reviews, written to lm/corpus/external_candidates.jsonl for selection. |
| 2026-10-03T18:37:40+00:00 | 3.6 | External query set: 15 queries, 12 with real harvested phrasing, 3 flagged as the project's own phrasing. |
| 2026-10-03T18:38:08+00:00 | 2.2 | 400/625 ligases processed. Notes: {'fpocket': 382, 'open_targets': 382, 'open_targets_no_expression': 5, 'structure_download_failed:FileNotFoundError': 8, 'no_ensembl_gene_id': 3}. |
| 2026-10-03T18:40:11+00:00 | 3.7 | Stage 1 LoRA SFT starting: 5,601 train / 666 valid examples, rank 16, 16 layers, lr 1e-05, batch 4, 1200 iterations. |
| 2026-10-03T18:40:42+00:00 | 1.3 | 24,447/52,681 entries, 32,915 bridges, 0 failed, 8.1 entries/s, ~1.0 h remaining. |
| 2026-10-03T18:41:33+00:00 | 2.2 | 450/625 ligases processed. Notes: {'fpocket': 432, 'open_targets': 431, 'open_targets_no_expression': 5, 'structure_download_failed:FileNotFoundError': 8, 'no_ensembl_gene_id': 4}. |
| 2026-10-03T18:42:31+00:00 | 2.1 | 3,060/20,431 scanned, 3,502 candidates, 130 failed, 1.7/s, ~2.8 h remaining. |
| 2026-10-03T18:44:23+00:00 | 2.2 | 500/625 ligases processed. Notes: {'fpocket': 482, 'open_targets': 479, 'open_targets_no_expression': 7, 'structure_download_failed:FileNotFoundError': 8, 'no_ensembl_gene_id': 4}. |
| 2026-10-03T18:45:43+00:00 | 1.3 | 25,715/52,681 entries, 38,261 bridges, 0 failed, 7.8 entries/s, ~1.0 h remaining. |
| 2026-10-03T18:47:31+00:00 | 2.1 | 3,559/20,431 scanned, 4,074 candidates, 150 failed, 1.7/s, ~2.8 h remaining. |
| 2026-10-03T18:48:45+00:00 | 2.2 | 550/625 ligases processed. Notes: {'fpocket': 532, 'open_targets': 529, 'open_targets_no_expression': 7, 'structure_download_failed:FileNotFoundError': 8, 'no_ensembl_gene_id': 4}. |
| 2026-10-03T18:50:43+00:00 | 1.3 | 26,978/52,681 entries, 40,058 bridges, 0 failed, 7.5 entries/s, ~1.0 h remaining. |
| 2026-10-03T18:52:31+00:00 | 2.1 | 4,056/20,431 scanned, 4,563 candidates, 169 failed, 1.7/s, ~2.7 h remaining. |
| 2026-10-03T18:54:02+00:00 | 3.7 | Stage 1 complete in 13.9 min. Best validation loss None at iteration None. |
| 2026-10-03T18:54:09+00:00 | 3.7 | Stage 2 DPO starting on 600 preference pairs, beta 0.1. mlx-lm 0.32.0 provides no preference trainer, so this is the documented mlx-examples DPO fallback implemented against mlx-lm's LoRA machinery. |
| 2026-10-03T18:54:55+00:00 | 2.2 | 600/625 ligases processed. Notes: {'fpocket': 581, 'open_targets': 577, 'open_targets_no_expression': 8, 'structure_download_failed:FileNotFoundError': 9, 'no_ensembl_gene_id': 5}. |
| 2026-10-03T18:55:24+00:00 | 3.7 | Stage 2: reference log-probabilities cached for 200/600 pairs. |
| 2026-10-03T18:55:43+00:00 | 1.3 | 28,144/52,681 entries, 46,461 bridges, 0 failed, 7.2 entries/s, ~0.9 h remaining. |
| 2026-10-03T18:56:47+00:00 | 3.7 | Stage 2: reference log-probabilities cached for 400/600 pairs. |
| 2026-10-03T18:57:03+00:00 | 4.1b | About tab generated: 51 references, 4/10 datasets resolved, worked example selected, 2 value(s) not recorded. |
| 2026-10-03T18:57:15+00:00 | 2.2 | E3 triage complete: 625 ligases, 616 with a pocket score (coverage 0.986, floor 0.8). Notes: {'fpocket': 606, 'open_targets': 600, 'open_targets_no_expression': 9, 'structure_download_failed:FileNotFoundError': 9, 'no_ensembl_gene_id': 6}. |
| 2026-10-03T18:57:31+00:00 | 2.1 | 4,519/20,431 scanned, 5,078 candidates, 183 failed, 1.7/s, ~2.6 h remaining. |
| 2026-10-03T18:58:05+00:00 | 3.7 | Stage 2: reference log-probabilities cached for 600/600 pairs. |
| 2026-10-03T18:58:05+00:00 | 3.7 | Stage 2: reference cache built for 600 pairs in 3.9 min. |
| 2026-10-03T18:58:05+00:00 | 3.7 | Stage 2 step 0 failed: AttributeError: module 'mlx.nn.losses' has no attribute 'log_sigmoid' |
| 2026-10-03T18:58:06+00:00 | 4.3 | Atlas built: 52,821 entries, 48,732 bridges (novel set not determinable: no curated glue database resolved (G7)), 9,962 ligands, 12 degrons, 625 ligases, 1,650 lysines, 71.8 MB. |
| 2026-10-03T18:58:19+00:00 | 9 | Validation run against binman.sqlite: 10 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-03T18:58:21+00:00 | 3.7 | Fuse succeeded: models/binman-lm/fused |
| 2026-10-03T19:00:41+00:00 | 2.2 | UniProt keyword KW-0833 cross-check set: 755 reviewed human proteins. |
| 2026-10-03T19:00:41+00:00 | 2.2 | InterPro IPR001841 (RING): 296 human reviewed proteins. |
| 2026-10-03T19:00:41+00:00 | 2.2 | InterPro IPR000569 (HECT): 28 human reviewed proteins. |
| 2026-10-03T19:00:41+00:00 | 2.2 | InterPro IPR002867 (RBR): 14 human reviewed proteins. |
| 2026-10-03T19:00:41+00:00 | 2.2 | InterPro IPR001810 (F-box): 67 human reviewed proteins. |
| 2026-10-03T19:00:41+00:00 | 2.2 | InterPro IPR000210 (BTB): 178 human reviewed proteins. |
| 2026-10-03T19:00:41+00:00 | 2.2 | InterPro IPR001496 (SOCS-box): 38 human reviewed proteins. |
| 2026-10-03T19:00:41+00:00 | 2.2 | InterPro IPR003613 (U-box): 9 human reviewed proteins. |
| 2026-10-03T19:00:41+00:00 | 2.2 | InterPro IPR001373 (Cullin): 9 human reviewed proteins. |
| 2026-10-03T19:00:41+00:00 | 2.2 | InterPro IPR024991 (APC-C): 1 human reviewed proteins. |
| 2026-10-03T19:00:43+00:00 | 1.3 | 29,108/52,681 entries, 51,112 bridges, 0 failed, 6.9 entries/s, ~0.9 h remaining. |
| 2026-10-03T19:00:50+00:00 | 2.2 | InterPro IPR034750 (CULT): 1 human reviewed proteins. |
| 2026-10-03T19:00:51+00:00 | 3.8 | stage1: loading mlx-community/Qwen2.5-3B-Instruct-4bit with adapters at models/binman-lm/adapters |
| 2026-10-03T19:00:52+00:00 | 2.2 | InterPro IPR022772 (VHL-box): 2 human reviewed proteins. |
| 2026-10-03T19:01:00+00:00 | 2.2 | InterPro IPR038914 (DCAF15): 1 human reviewed proteins. |
| 2026-10-03T19:01:08+00:00 | 2.2 | InterPro IPR028216 (DCAF16): 1 human reviewed proteins. |
| 2026-10-03T19:01:18+00:00 | 2.2 | UniProt name "DDB1- and CUL4-associated factor" (DCAF): 22 proteins. |
| 2026-10-03T19:01:18+00:00 | 2.2 | Repertoire: 650 ligases from 13 InterPro signatures, 406 also carrying the KW-0833 keyword. Per family: {'RING': 296, 'HECT': 28, 'RBR': 14, 'F-box': 67, 'BTB': 178, 'SOCS-box': 38, 'U-box': 9, 'Cullin': 9, 'APC-C': 1, 'CULT': 1, 'VHL-box': 2, 'DCAF15': 1, 'DCAF16': 1, 'DCAF': 22}. |
| 2026-10-03T19:01:18+00:00 | 2.2 | UbiBrowser substrate counts loaded: 445 E3s with curated substrates, 588 with predicted. |
| 2026-10-03T19:02:31+00:00 | 2.1 | 5,019/20,431 scanned, 5,558 candidates, 203 failed, 1.7/s, ~2.6 h remaining. |
| 2026-10-03T19:04:13+00:00 | 2.2 | E3 triage complete: 650 ligases, 638 with a pocket score (coverage 0.982, floor 0.8). Notes: {'fpocket': 22, 'open_targets': 25, 'structure_download_failed:FileNotFoundError': 3}. |
| 2026-10-03T19:05:42+00:00 | 3.8 | stage1: parse rate 0.0, set equality 0.0 on 120 synthetic queries. |
| 2026-10-03T19:05:43+00:00 | 1.3 | 30,273/52,681 entries, 57,023 bridges, 0 failed, 6.7 entries/s, ~0.9 h remaining. |
| 2026-10-03T19:05:50+00:00 | 2.4 | Edge table built: 16,235 edges (5,226 bridged_by, 0 curated ubiquitylates, 11,001 predicted, 8 has_degron). |
| 2026-10-03T19:06:01+00:00 | 4.3 | Atlas built: 52,821 entries, 57,758 bridges (novel set not determinable: no curated glue database resolved (G7)), 9,962 ligands, 12 degrons, 650 ligases, 1,650 lysines, 75.7 MB. |
| 2026-10-03T19:06:01+00:00 | 9 | Validation run against binman.sqlite: 1 metric(s) not computed (dataset unavailable), 0 measured floor(s) missed. |
| 2026-10-03T19:07:07+00:00 | 3.8 | stage1: loading mlx-community/Qwen2.5-3B-Instruct-4bit with adapters at models/binman-lm/adapters |
| 2026-10-03T19:07:21+00:00 | 9 | Validation run against binman.sqlite: 10 metric(s) not computed (dataset unavailable), 1 measured floor(s) missed. |
| 2026-10-03T19:07:32+00:00 | 2.1 | 5,524/20,431 scanned, 6,124 candidates, 221 failed, 1.7/s, ~2.5 h remaining. |
| 2026-10-03T19:07:51+00:00 | 3.8 | stage1 synthetic: 25/120 evaluated (0.73/s), parse 0.960, set equality 0.960. |
| 2026-10-03T19:08:25+00:00 | 3.8 | stage1 synthetic: 50/120 evaluated (0.73/s), parse 0.980, set equality 0.980. |
| 2026-10-03T19:08:59+00:00 | 3.8 | stage1 synthetic: 75/120 evaluated (0.73/s), parse 0.987, set equality 0.987. |
| 2026-10-03T19:09:33+00:00 | 3.8 | stage1 synthetic: 100/120 evaluated (0.73/s), parse 0.990, set equality 0.990. |
| 2026-10-03T19:10:43+00:00 | 1.3 | 30,892/52,681 entries, 63,878 bridges, 0 failed, 6.4 entries/s, ~0.9 h remaining. |
| 2026-10-03T19:11:31+00:00 | 3.8 | stage1: parse rate 0.9917, set equality 0.9917 on 120 synthetic queries. |
| 2026-10-03T19:12:32+00:00 | 2.1 | 6,023/20,431 scanned, 6,729 candidates, 244 failed, 1.7/s, ~2.4 h remaining. |
| 2026-10-03T19:14:49+00:00 | 3.7 | Stage 1 LoRA SFT starting: 5,601 train / 666 valid examples, rank 16, 16 layers, lr 1e-05, batch 4, 1200 iterations. |
| 2026-10-03T19:15:43+00:00 | 1.3 | 31,602/52,681 entries, 78,335 bridges, 0 failed, 6.2 entries/s, ~0.9 h remaining. |
| 2026-10-03T19:17:32+00:00 | 2.1 | 6,524/20,431 scanned, 7,420 candidates, 261 failed, 1.7/s, ~2.3 h remaining. |
| 2026-10-03T19:20:43+00:00 | 1.3 | 31,891/52,681 entries, 91,106 bridges, 0 failed, 5.9 entries/s, ~1.0 h remaining. |
| 2026-10-03T19:22:32+00:00 | 2.1 | 7,027/20,431 scanned, 7,957 candidates, 278 failed, 1.7/s, ~2.2 h remaining. |
| 2026-10-03T19:25:43+00:00 | 1.3 | 32,319/52,681 entries, 103,943 bridges, 0 failed, 5.7 entries/s, ~1.0 h remaining. |
| 2026-10-03T19:27:33+00:00 | 2.1 | 7,530/20,431 scanned, 8,403 candidates, 293 failed, 1.7/s, ~2.1 h remaining. |
| 2026-10-03T19:28:30+00:00 | 3.7 | Stage 1 complete in 13.7 min. Best validation loss 0.002 at iteration 1000. |
| 2026-10-03T19:28:36+00:00 | 3.7 | Stage 2 DPO starting on 600 preference pairs, beta 0.1. mlx-lm 0.32.0 provides no preference trainer, so this is the documented mlx-examples DPO fallback implemented against mlx-lm's LoRA machinery. |
| 2026-10-03T19:29:21+00:00 | 3.7 | Stage 2: reference log-probabilities cached for 200/600 pairs. |
| 2026-10-03T19:30:35+00:00 | 3.7 | Stage 2: reference log-probabilities cached for 400/600 pairs. |
| 2026-10-03T19:30:44+00:00 | 1.3 | 32,517/52,681 entries, 114,101 bridges, 0 failed, 5.4 entries/s, ~1.0 h remaining. |
| 2026-10-03T19:31:45+00:00 | 3.7 | Stage 2: reference log-probabilities cached for 600/600 pairs. |
| 2026-10-03T19:31:45+00:00 | 3.7 | Stage 2: reference cache built for 600 pairs in 3.1 min. |
| 2026-10-03T19:32:19+00:00 | 3.7 | Stage 2: step 20, mean loss over the last 20 steps 0.6585. |
| 2026-10-03T19:32:33+00:00 | 2.1 | 8,022/20,431 scanned, 8,945 candidates, 317 failed, 1.7/s, ~2.1 h remaining. |
| 2026-10-03T19:32:41+00:00 | 3.7 | Stage 2: step 40, mean loss over the last 20 steps 0.5302. |
| 2026-10-03T19:33:00+00:00 | 3.7 | Stage 2: step 60, mean loss over the last 20 steps 0.3655. |
| 2026-10-03T19:33:15+00:00 | 3.7 | Stage 2: step 80, mean loss over the last 20 steps 0.1228. |
| 2026-10-03T19:33:32+00:00 | 3.7 | Stage 2: step 100, mean loss over the last 20 steps 0.0354. |
| 2026-10-03T19:33:44+00:00 | 3.7 | Stage 2: step 120, mean loss over the last 20 steps 0.0046. |
| 2026-10-03T19:33:58+00:00 | 3.7 | Stage 2: step 140, mean loss over the last 20 steps 0.0357. |
| 2026-10-03T19:34:12+00:00 | 3.7 | Stage 2: step 160, mean loss over the last 20 steps 0.0048. |
| 2026-10-03T19:34:24+00:00 | 3.7 | Stage 2: step 180, mean loss over the last 20 steps 0.0098. |
| 2026-10-03T19:34:37+00:00 | 3.7 | Stage 2: step 200, mean loss over the last 20 steps 0.0337. |
| 2026-10-03T19:34:49+00:00 | 3.7 | Stage 2: step 220, mean loss over the last 20 steps 0.4838. |
| 2026-10-03T19:35:02+00:00 | 3.7 | Stage 2: step 240, mean loss over the last 20 steps 0.2023. |
| 2026-10-03T19:35:15+00:00 | 3.7 | Stage 2: step 260, mean loss over the last 20 steps 0.2340. |
| 2026-10-03T19:35:29+00:00 | 3.7 | Stage 2: step 280, mean loss over the last 20 steps 0.2038. |
| 2026-10-03T19:35:42+00:00 | 3.7 | Stage 2: step 300, mean loss over the last 20 steps 0.0140. |
| 2026-10-03T19:35:46+00:00 | 1.3 | 32,749/52,681 entries, 121,634 bridges, 0 failed, 5.2 entries/s, ~1.1 h remaining. |
| 2026-10-03T19:35:56+00:00 | 3.7 | Stage 2: step 320, mean loss over the last 20 steps 0.0072. |
| 2026-10-03T19:36:06+00:00 | 3.7 | Stage 2: step 340, mean loss over the last 20 steps 0.0246. |
| 2026-10-03T19:36:20+00:00 | 3.7 | Stage 2: step 360, mean loss over the last 20 steps 0.0721. |
| 2026-10-03T19:36:31+00:00 | 3.7 | Stage 2: step 380, mean loss over the last 20 steps 0.0199. |
| 2026-10-03T19:36:43+00:00 | 3.7 | Stage 2: step 400, mean loss over the last 20 steps 0.0116. |
| 2026-10-03T19:36:56+00:00 | 3.7 | Stage 2: step 420, mean loss over the last 20 steps 0.1641. |
| 2026-10-03T19:37:10+00:00 | 3.7 | Stage 2: step 440, mean loss over the last 20 steps 0.0022. |
| 2026-10-03T19:37:23+00:00 | 3.7 | Stage 2: step 460, mean loss over the last 20 steps 0.0010. |
| 2026-10-03T19:37:33+00:00 | 2.1 | 8,492/20,431 scanned, 9,382 candidates, 334 failed, 1.7/s, ~2.0 h remaining. |
| 2026-10-03T19:37:36+00:00 | 3.7 | Stage 2: step 480, mean loss over the last 20 steps 0.0042. |
| 2026-10-03T19:37:49+00:00 | 3.7 | Stage 2: step 500, mean loss over the last 20 steps 0.0110. |
| 2026-10-03T19:38:01+00:00 | 3.7 | Stage 2: step 520, mean loss over the last 20 steps 0.0030. |
| 2026-10-03T19:38:14+00:00 | 3.7 | Stage 2: step 540, mean loss over the last 20 steps 0.0044. |
| 2026-10-03T19:38:25+00:00 | 3.7 | Stage 2: step 560, mean loss over the last 20 steps 0.0017. |
| 2026-10-03T19:38:36+00:00 | 3.7 | Stage 2: step 580, mean loss over the last 20 steps 0.0014. |
| 2026-10-03T19:38:51+00:00 | 3.7 | Stage 2: step 600, mean loss over the last 20 steps 0.0016. |
| 2026-10-03T19:38:52+00:00 | 3.7 | Stage 2 DPO complete: 600 steps in 7.1 min, adapters saved to models/binman-lm/adapters-dpo. |
| 2026-10-03T19:39:04+00:00 | 3.7 | Fuse succeeded: models/binman-lm/fused |
| 2026-10-03T19:40:46+00:00 | 1.3 | 32,821/52,681 entries, 128,339 bridges, 0 failed, 5.0 entries/s, ~1.1 h remaining. |
| 2026-10-03T19:42:33+00:00 | 2.1 | 8,975/20,431 scanned, 9,844 candidates, 352 failed, 1.7/s, ~1.9 h remaining. |
| 2026-10-03T19:45:46+00:00 | 1.3 | 32,877/52,681 entries, 136,513 bridges, 0 failed, 4.8 entries/s, ~1.2 h remaining. |
| 2026-10-03T19:45:53+00:00 | 3.8 | stage2: loading mlx-community/Qwen2.5-3B-Instruct-4bit with adapters at models/binman-lm/adapters-dpo |
| 2026-10-03T19:47:33+00:00 | 2.1 | 9,473/20,431 scanned, 10,326 candidates, 371 failed, 1.7/s, ~1.8 h remaining. |
| 2026-10-03T19:50:46+00:00 | 1.3 | 32,936/52,681 entries, 147,413 bridges, 0 failed, 4.6 entries/s, ~1.2 h remaining. |
| 2026-10-03T19:52:34+00:00 | 2.1 | 9,967/20,431 scanned, 10,889 candidates, 383 failed, 1.7/s, ~1.8 h remaining. |
| 2026-10-03T19:55:46+00:00 | 1.3 | 33,062/52,681 entries, 164,510 bridges, 0 failed, 4.4 entries/s, ~1.2 h remaining. |
| 2026-10-03T19:57:36+00:00 | 2.1 | 10,462/20,431 scanned, 11,368 candidates, 395 failed, 1.7/s, ~1.7 h remaining. |
| 2026-10-03T20:00:01+00:00 | 3.8 | stage2: parse rate 0.0, set equality 0.0 on 120 synthetic queries. |
| 2026-10-03T20:00:46+00:00 | 1.3 | 33,166/52,681 entries, 172,789 bridges, 0 failed, 4.2 entries/s, ~1.3 h remaining. |
| 2026-10-03T20:02:36+00:00 | 2.1 | 10,943/20,431 scanned, 11,933 candidates, 404 failed, 1.7/s, ~1.6 h remaining. |
| 2026-10-03T20:05:46+00:00 | 1.3 | 33,384/52,681 entries, 180,446 bridges, 0 failed, 4.1 entries/s, ~1.3 h remaining. |
| 2026-10-03T20:07:38+00:00 | 2.1 | 11,431/20,431 scanned, 12,401 candidates, 413 failed, 1.7/s, ~1.5 h remaining. |
| 2026-10-03T20:08:15+00:00 | 3.7 | Stage 2 retry: lr 5e-7 (was 1e-5), 150 steps (was 600). The first attempt reached a near-zero DPO loss by collapsing the policy rather than learning the preference. |
| 2026-10-03T20:08:21+00:00 | 3.7 | Stage 2 DPO starting on 600 preference pairs, beta 0.1. mlx-lm 0.32.0 provides no preference trainer, so this is the documented mlx-examples DPO fallback implemented against mlx-lm's LoRA machinery. |
| 2026-10-03T20:09:04+00:00 | 3.7 | Stage 2: reference log-probabilities cached for 200/600 pairs. |
| 2026-10-03T20:10:17+00:00 | 3.7 | Stage 2: reference log-probabilities cached for 400/600 pairs. |
| 2026-10-03T20:10:47+00:00 | 1.3 | 33,529/52,681 entries, 187,169 bridges, 0 failed, 4.0 entries/s, ~1.3 h remaining. |
| 2026-10-03T20:11:30+00:00 | 3.7 | Stage 2: reference log-probabilities cached for 600/600 pairs. |
| 2026-10-03T20:11:30+00:00 | 3.7 | Stage 2: reference cache built for 600 pairs in 3.1 min. |
| 2026-10-03T20:11:57+00:00 | 3.7 | Stage 2: step 20, mean loss over the last 20 steps 0.6913. |
| 2026-10-03T20:12:16+00:00 | 3.7 | Stage 2: step 40, mean loss over the last 20 steps 0.6848. |
| 2026-10-03T20:12:31+00:00 | 3.7 | Stage 2: step 60, mean loss over the last 20 steps 0.6799. |
| 2026-10-03T20:12:38+00:00 | 2.1 | 11,900/20,431 scanned, 12,834 candidates, 423 failed, 1.7/s, ~1.4 h remaining. |
| 2026-10-03T20:12:44+00:00 | 3.7 | Stage 2: step 80, mean loss over the last 20 steps 0.6749. |
| 2026-10-03T20:12:57+00:00 | 3.7 | Stage 2: step 100, mean loss over the last 20 steps 0.6675. |
| 2026-10-03T20:13:08+00:00 | 3.7 | Stage 2: step 120, mean loss over the last 20 steps 0.6658. |
| 2026-10-03T20:13:20+00:00 | 3.7 | Stage 2: step 140, mean loss over the last 20 steps 0.6561. |
| 2026-10-03T20:13:29+00:00 | 3.7 | Stage 2 DPO complete: 150 steps in 2.0 min, adapters saved to models/binman-lm/adapters-dpo. |
| 2026-10-03T20:14:12+00:00 | 3.7 | Stage 2 retry REJECTED by the guard: only 1/6 probes parsed; sample output '{"record_type":"ligase","filters":[{"field":"pocket_score","op":"gt","value":0.5}],"sort":'. Shipping stage 1 alone (spec 3.7 fallback). |
| 2026-10-03T20:14:23+00:00 | 3.7 | Fuse succeeded: models/binman-lm/fused |
| 2026-10-03T20:15:47+00:00 | 1.3 | 33,728/52,681 entries, 194,443 bridges, 0 failed, 3.9 entries/s, ~1.4 h remaining. |
| 2026-10-03T20:17:39+00:00 | 2.1 | 12,386/20,431 scanned, 13,291 candidates, 433 failed, 1.6/s, ~1.4 h remaining. |
| 2026-10-03T20:20:47+00:00 | 1.3 | 33,921/52,681 entries, 211,806 bridges, 0 failed, 3.8 entries/s, ~1.4 h remaining. |
| 2026-10-03T20:22:39+00:00 | 2.1 | 12,879/20,431 scanned, 13,900 candidates, 441 failed, 1.6/s, ~1.3 h remaining. |
| 2026-10-03T20:25:48+00:00 | 1.3 | 34,050/52,681 entries, 215,853 bridges, 0 failed, 3.7 entries/s, ~1.4 h remaining. |
| 2026-10-03T20:27:39+00:00 | 2.1 | 13,351/20,431 scanned, 14,389 candidates, 451 failed, 1.6/s, ~1.2 h remaining. |
| 2026-10-03T20:30:48+00:00 | 1.3 | 34,158/52,681 entries, 216,818 bridges, 0 failed, 3.6 entries/s, ~1.4 h remaining. |
| 2026-10-03T20:32:40+00:00 | 2.1 | 13,819/20,431 scanned, 14,945 candidates, 464 failed, 1.6/s, ~1.1 h remaining. |
| 2026-10-03T20:35:49+00:00 | 1.3 | 34,277/52,681 entries, 217,766 bridges, 0 failed, 3.5 entries/s, ~1.5 h remaining. |
| 2026-10-03T20:37:40+00:00 | 2.1 | 14,291/20,431 scanned, 15,516 candidates, 470 failed, 1.6/s, ~1.0 h remaining. |
| 2026-10-03T20:40:49+00:00 | 1.3 | 34,532/52,681 entries, 219,045 bridges, 0 failed, 3.4 entries/s, ~1.5 h remaining. |
| 2026-10-03T20:42:41+00:00 | 2.1 | 14,780/20,431 scanned, 16,025 candidates, 476 failed, 1.6/s, ~1.0 h remaining. |
| 2026-10-03T20:45:50+00:00 | 1.3 | 34,897/52,681 entries, 226,358 bridges, 0 failed, 3.3 entries/s, ~1.5 h remaining. |
| 2026-10-03T20:47:41+00:00 | 2.1 | 15,266/20,431 scanned, 16,780 candidates, 488 failed, 1.6/s, ~0.9 h remaining. |
| 2026-10-03T20:50:57+00:00 | 1.3 | 35,065/52,681 entries, 229,698 bridges, 0 failed, 3.2 entries/s, ~1.5 h remaining. |
| 2026-10-03T20:52:42+00:00 | 2.1 | 15,750/20,431 scanned, 17,419 candidates, 496 failed, 1.6/s, ~0.8 h remaining. |
| 2026-10-03T20:56:00+00:00 | 1.3 | 35,204/52,681 entries, 230,703 bridges, 0 failed, 3.2 entries/s, ~1.5 h remaining. |
| 2026-10-03T20:57:42+00:00 | 2.1 | 16,228/20,431 scanned, 18,009 candidates, 502 failed, 1.6/s, ~0.7 h remaining. |
| 2026-10-03T21:01:28+00:00 | 1.3 | 35,259/52,681 entries, 232,206 bridges, 0 failed, 3.1 entries/s, ~1.6 h remaining. |
| 2026-10-03T21:02:42+00:00 | 2.1 | 16,705/20,431 scanned, 18,585 candidates, 511 failed, 1.6/s, ~0.6 h remaining. |
| 2026-10-03T21:06:55+00:00 | 1.3 | 35,268/52,681 entries, 235,526 bridges, 0 failed, 3.0 entries/s, ~1.6 h remaining. |
| 2026-10-03T21:07:43+00:00 | 2.1 | 17,189/20,431 scanned, 19,301 candidates, 519 failed, 1.6/s, ~0.6 h remaining. |
| 2026-10-03T21:12:04+00:00 | 1.3 | 35,325/52,681 entries, 238,177 bridges, 0 failed, 2.9 entries/s, ~1.6 h remaining. |
| 2026-10-03T21:12:43+00:00 | 2.1 | 17,666/20,431 scanned, 20,040 candidates, 523 failed, 1.6/s, ~0.5 h remaining. |
| 2026-10-03T21:12:43+00:00 | 1.3 | Bridge run starting: 17,353 entries pending of 52,822 catalogued (tiers 1 to 3), 16 IO workers, 14 geometry workers. |
| 2026-10-03T21:17:43+00:00 | 2.1 | 18,161/20,431 scanned, 20,465 candidates, 529 failed, 1.6/s, ~0.4 h remaining. |
| 2026-10-03T21:17:44+00:00 | 1.3 | 16,971/17,353 entries, 854 bridges, 90 failed, 56.5 entries/s, ~0.0 h remaining. |
| 2026-10-03T21:18:57+00:00 | 1.3 | Bridge run finished: 17,353 entries in 6.2 min, 858 bridges, 235 failed, 46.4 entries/s. |
| 2026-10-03T21:19:56+00:00 | 1.5 | Trimmed structures: 25 representative (entry, ligand) pairs at balance >= 0.3, trim radius 8.0 A. |
| 2026-10-03T21:20:01+00:00 | 1.5 | Trimmed structures complete: 25 written, 0 reused, 0 failed, 3.6 MB total. |
| 2026-10-03T21:20:29+00:00 | 4.3 | Atlas built: 52,821 entries, 239,485 bridges (novel set not determinable: no curated glue database resolved (G7)), 9,981 ligands, 12 degrons, 650 ligases, 1,650 lysines, 136.2 MB. |
| 2026-10-03T21:20:40+00:00 | 1.5 | Trimmed structures: 3,838 representative (entry, ligand) pairs at balance >= 0.3, trim radius 8.0 A. |
| 2026-10-03T21:22:17+00:00 | 1.5 | 500/3,838 trimmed, 88 MB so far, 0 failed. |
| 2026-10-03T21:22:43+00:00 | 2.1 | 18,646/20,431 scanned, 21,034 candidates, 539 failed, 1.6/s, ~0.3 h remaining. |
| 2026-10-03T21:24:00+00:00 | 1.5 | 1,000/3,838 trimmed, 161 MB so far, 0 failed. |
| 2026-10-03T21:25:41+00:00 | 1.5 | 1,500/3,838 trimmed, 242 MB so far, 0 failed. |
| 2026-10-03T21:27:12+00:00 | 1.5 | 2,000/3,838 trimmed, 317 MB so far, 0 failed. |
| 2026-10-03T21:27:44+00:00 | 2.1 | 19,139/20,431 scanned, 21,325 candidates, 548 failed, 1.6/s, ~0.2 h remaining. |
| 2026-10-03T21:28:36+00:00 | 1.5 | 2,500/3,838 trimmed, 383 MB so far, 0 failed. |
| 2026-10-03T21:30:30+00:00 | 1.5 | 3,000/3,838 trimmed, 469 MB so far, 0 failed. |
| 2026-10-03T21:32:45+00:00 | 2.1 | 19,640/20,431 scanned, 21,570 candidates, 559 failed, 1.6/s, ~0.1 h remaining. |
| 2026-10-03T21:33:52+00:00 | 1.5 | 3,500/3,838 trimmed, 622 MB so far, 0 failed. |
| 2026-10-03T21:36:13+00:00 | 1.5 | Trimmed structures complete: 3,813 written, 25 reused, 0 failed, 753.6 MB total. |
| 2026-10-03T21:37:45+00:00 | 2.1 | 20,148/20,431 scanned, 21,707 candidates, 568 failed, 1.6/s, ~0.0 h remaining. |
| 2026-10-03T21:38:58+00:00 | 2.1 | Degron scan complete: 20,279 proteins scanned, 21,717 candidate degrons written, 570 failed. |
| 2026-10-03T21:39:42+00:00 | 2.4 | Edge table built: 30,057 edges (19,048 bridged_by, 0 curated ubiquitylates, 11,001 predicted, 8 has_degron). |
| 2026-10-03T21:39:56+00:00 | 4.3 | Atlas built: 52,821 entries, 239,485 bridges (novel set not determinable: no curated glue database resolved (G7)), 9,981 ligands, 21,717 degrons, 650 ligases, 1,650 lysines, 142.5 MB. |
| 2026-10-03T21:40:16+00:00 | 3.2 | Corpus grounding: 28 numeric field ranges read from the atlas, vocabularies {'ccd_id': 4000, 'ccd_class': 11, 'ligase_gene': 650, 'ligase_acc': 650, 'ligase_family': 13, 'verdict': 0, 'evidence_class': 0, 'motif_family': 1, 'method': 15}. |
| 2026-10-03T21:40:16+00:00 | 3.2 | Task A generated 6,000 pairs, 6,000 validated by the app parser, 0 rejected and dropped (the corpus therefore has zero label noise by construction). |
| 2026-10-03T21:40:16+00:00 | 3.2 | Corpus written: Task A 4,752/574/674, 1,400 preference pairs across 7 modes, Task C 784 train. Task B buildable: False. |
| 2026-10-03T21:40:18+00:00 | 3.7 | Stage 1 LoRA SFT starting: 5,536 train / 672 valid examples, rank 16, 16 layers, lr 1e-05, batch 4, 1200 iterations. |
| 2026-10-03T21:40:20+00:00 | 9 | Validation run against binman.sqlite: 10 metric(s) not computed (dataset unavailable), 1 measured floor(s) missed. |
| 2026-10-03T21:40:30+00:00 | 4.1b | About tab generated: 51 references, 4/10 datasets resolved, worked example selected, 2 value(s) not recorded. |
| 2026-10-03T21:53:48+00:00 | 3.7 | Stage 1 complete in 13.5 min. Best validation loss 0.003 at iteration 1200. |
| 2026-10-03T21:53:55+00:00 | 3.7 | Fuse succeeded: models/binman-lm/fused |
| 2026-10-03T21:56:31+00:00 | 3.8 | final: loading mlx-community/Qwen2.5-3B-Instruct-4bit with adapters at models/binman-lm/adapters |
| 2026-10-03T21:57:03+00:00 | 3.8 | final synthetic: 25/150 evaluated (0.93/s), parse 0.960, set equality 0.960. |
| 2026-10-03T21:57:29+00:00 | 3.8 | final synthetic: 50/150 evaluated (0.95/s), parse 0.980, set equality 0.980. |
| 2026-10-03T21:57:54+00:00 | 3.8 | final synthetic: 75/150 evaluated (0.96/s), parse 0.973, set equality 0.973. |
| 2026-10-03T21:58:19+00:00 | 3.8 | final synthetic: 100/150 evaluated (0.97/s), parse 0.980, set equality 0.980. |
| 2026-10-03T21:58:45+00:00 | 3.8 | final synthetic: 125/150 evaluated (0.97/s), parse 0.984, set equality 0.984. |
| 2026-10-03T21:59:12+00:00 | 3.8 | final synthetic: 150/150 evaluated (0.96/s), parse 0.987, set equality 0.980. |
| 2026-10-03T22:00:27+00:00 | 3.8 | final: parse rate 0.9867, set equality 0.98 on 150 synthetic queries. |
| 2026-10-03T22:00:28+00:00 | 3.8 | baseline_final: loading mlx-community/Qwen2.5-3B-Instruct-4bit zero-shot |
| 2026-10-03T22:01:14+00:00 | 3.8 | baseline_final synthetic: 50/150 evaluated (1.19/s), parse 0.540, set equality 0.320. |
| 2026-10-03T22:01:57+00:00 | 3.8 | baseline_final synthetic: 100/150 evaluated (1.18/s), parse 0.500, set equality 0.330. |
| 2026-10-03T22:02:37+00:00 | 3.8 | baseline_final synthetic: 150/150 evaluated (1.20/s), parse 0.513, set equality 0.347. |
| 2026-10-03T22:03:18+00:00 | 3.8 | baseline_final: parse rate 0.5133, set equality 0.3467 on 150 synthetic queries. |
| 2026-10-03T22:07:49+00:00 | 3.6 | Europe PMC harvest: 18 candidate question sentences from open-access reviews, written to lm/corpus/external_candidates.jsonl for selection. |
| 2026-10-03T22:07:49+00:00 | 3.6 | External query set: 15 queries, 0 with real harvested phrasing, 15 flagged as the project's own phrasing. |
| 2026-10-03T22:08:18+00:00 | 3.8 | final: loading mlx-community/Qwen2.5-3B-Instruct-4bit with adapters at models/binman-lm/adapters |
| 2026-10-03T22:08:53+00:00 | 3.8 | final synthetic: 25/150 evaluated (0.93/s), parse 0.960, set equality 0.960. |
| 2026-10-03T22:09:19+00:00 | 3.8 | final synthetic: 50/150 evaluated (0.95/s), parse 0.980, set equality 0.980. |
| 2026-10-03T22:09:44+00:00 | 3.8 | final synthetic: 75/150 evaluated (0.96/s), parse 0.973, set equality 0.973. |
| 2026-10-03T22:10:10+00:00 | 3.8 | final synthetic: 100/150 evaluated (0.97/s), parse 0.980, set equality 0.980. |
| 2026-10-03T22:10:36+00:00 | 3.8 | final synthetic: 125/150 evaluated (0.96/s), parse 0.984, set equality 0.984. |
| 2026-10-03T22:11:02+00:00 | 3.8 | final synthetic: 150/150 evaluated (0.96/s), parse 0.987, set equality 0.980. |
| 2026-10-03T22:12:16+00:00 | 3.8 | final: parse rate 0.9867, set equality 0.98 on 150 synthetic queries. |
| 2026-10-03T22:18:42+00:00 | 4.1b | About tab generated: 51 references, 4/10 datasets resolved, worked example selected, 2 value(s) not recorded. |
| 2026-10-03T22:47:46+00:00 | 1.0 | Validation datasets: 5/11 resolved (biolip2_annotations, biolip2_artefacts, mgtbind_compounds, ubibrowser_literature_e3, ubibrowser_predicted_e3). Manifest at data/validation/MANIFEST.md. |
| 2026-10-03T22:47:46+00:00 | gate | G7 opened: 6 validation dataset(s) could not be obtained automatically: degronopedia, mgdb_glues, mgtbind_ternary, molgluedb_glues, |
| 2026-10-03T22:48:11+00:00 | 1.0 | Validation datasets: 8/11 resolved (biolip2_annotations, biolip2_artefacts, mgdb_glues, mgtbind_compounds, mgtbind_ternary, molgluedb_glues, ubibrowser_literature_e3, ubibrowser_predicted_e3). Manifest at data/validation/MANIFEST.md. |
| 2026-10-03T22:48:11+00:00 | gate | G7 opened: 3 validation dataset(s) could not be obtained automatically: degronopedia, protacdb_protacs, protcid_interfaces. |
| 2026-10-03T22:48:39+00:00 | 4.3 | Atlas built: 52,821 entries, 239,485 bridges (13,243 novel), 9,981 ligands, 21,717 degrons, 650 ligases, 1,650 lysines, 142.5 MB. |
| 2026-10-03T22:48:39+00:00 | 9 | Validation run against binman.sqlite: 1 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-03T22:49:52+00:00 | 1.4 | Reclassified 9,981 chemical components. 539 changed class: {'buffer -> glue_candidate': 417, 'cryoprotectant -> glue_candidate': 103, 'glue_candidate -> sugar': 5, 'buffer -> peptide_like': 4, 'buffer -> detergent': 4, 'glue_candidate -> cofactor': 3} |
| 2026-10-03T22:50:13+00:00 | 4.3 | Atlas built: 52,821 entries, 239,485 bridges (13,243 novel), 9,981 ligands, 21,717 degrons, 650 ligases, 1,650 lysines, 142.5 MB. |
| 2026-10-03T22:50:13+00:00 | 9 | Validation run against binman.sqlite: 6 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-03T22:50:44+00:00 | 4.3 | Atlas built: 52,821 entries, 239,485 bridges (13,243 novel), 9,981 ligands, 21,717 degrons, 650 ligases, 1,650 lysines, 142.5 MB. |
| 2026-10-03T22:50:44+00:00 | 9 | Validation run against binman.sqlite: 1 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-03T22:51:17+00:00 | 4.3 | Atlas built: 52,821 entries, 239,485 bridges (14,260 novel), 9,981 ligands, 21,717 degrons, 650 ligases, 1,650 lysines, 142.5 MB. |
| 2026-10-03T22:51:18+00:00 | 9 | Validation run against binman.sqlite: 6 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-03T22:51:49+00:00 | 4.1b | About tab generated: 51 references, 8/11 datasets resolved, worked example selected, 2 value(s) not recorded. |
| 2026-10-03T23:14:24+00:00 | 1.0 | Validation datasets: 9/11 resolved (biolip2_annotations, biolip2_artefacts, mgdb_glues, mgtbind_compounds, mgtbind_ternary, molgluedb_glues, protacdb_protacs, ubibrowser_literature_e3, ubibrowser_predicted_e3). Manifest at data/validation/MANIFEST.md. |
| 2026-10-03T23:14:24+00:00 | gate | G7 opened: 2 validation dataset(s) could not be obtained automatically: degronopedia, protcid_interfaces. |
| 2026-10-03T23:15:49+00:00 | 3.4 | Task B: resolving InChIKeys for 9,981 chemical components. |
| 2026-10-03T23:16:05+00:00 | 3.4 | Task B: 9,585 components carry an InChIKey. |
| 2026-10-03T23:16:13+00:00 | 3.4 | Task B label sources mapped onto the atlas: molecular_glue 130, protac 32, native_cofactor 842, crystallisation_artefact 345, held out as disagreements 123 |
| 2026-10-03T23:16:14+00:00 | 3.4 | Task B corpus: 112 train / 24 valid / 16 test over 4 classes at 38 each, 123 disagreements held out. |
| 2026-10-03T23:29:01+00:00 | 3.4 | Abstracts for protac: 146 fetched of 150 identifiers tried. |
| 2026-10-03T23:30:46+00:00 | 3.4 | Abstracts for protac: 295 fetched of 300 identifiers tried. |
| 2026-10-03T23:32:54+00:00 | 3.4 | Abstracts for protac: 445 fetched of 450 identifiers tried. |
| 2026-10-03T23:34:41+00:00 | 3.4 | Abstracts for protac: 568 fetched of 600 identifiers tried. |
| 2026-10-03T23:36:15+00:00 | 3.4 | Abstracts for protac: 713 fetched of 750 identifiers tried. |
| 2026-10-03T23:36:26+00:00 | 3.4 | Abstracts for protac: 729 of 766 identifiers resolved. |
| 2026-10-03T23:38:00+00:00 | 3.4 | Abstracts for molecular_glue: 145 fetched of 150 identifiers tried. |
| 2026-10-03T23:39:37+00:00 | 3.4 | Abstracts for molecular_glue: 283 fetched of 300 identifiers tried. |
| 2026-10-03T23:41:03+00:00 | 3.4 | Abstracts for molecular_glue: 427 fetched of 450 identifiers tried. |
| 2026-10-03T23:41:53+00:00 | 3.4 | Abstracts for molecular_glue: 497 of 522 identifiers resolved. |
| 2026-10-03T23:41:53+00:00 | 3.4 | Class abstracts: 1,214 unique, 6 dropped as ambiguous (cited by both a glue and a PROTAC database). |
| 2026-10-03T23:44:54+00:00 | 3.4 | Task B: resolving InChIKeys for 9,981 chemical components. |
| 2026-10-03T23:44:54+00:00 | 3.4 | Task B: 9,585 components carry an InChIKey. |
| 2026-10-03T23:45:01+00:00 | 3.4 | Task B label sources mapped onto the atlas: molecular_glue 130, protac 32, native_cofactor 842, crystallisation_artefact 345, held out as disagreements 123 |
| 2026-10-03T23:45:01+00:00 | 3.4 | Task B corpus: 15,664 train / 1,714 valid / 4,087 test over 4 classes, unbalanced, 1,214 abstract inputs, 123 disagreements held out. |
| 2026-10-03T23:45:42+00:00 | 3.7 | Stage 1 LoRA SFT starting: 21,200 train / 2,386 valid examples, rank 16, 16 layers, lr 1e-05, batch 4, 1200 iterations. |
| 2026-10-04T00:01:04+00:00 | 3.7 | Stage 1 complete in 15.4 min. Best validation loss 0.006 at iteration 1000. |
| 2026-10-04T00:01:10+00:00 | 3.7 | Fuse succeeded: models/binman-lm/fused |
| 2026-10-04T00:03:18+00:00 | 3.8 | taskA: 25/100 evaluated (0.93/s), parse 1.000, set equality 1.000. |
| 2026-10-04T00:03:44+00:00 | 3.8 | taskA: 50/100 evaluated (0.95/s), parse 1.000, set equality 0.960. |
| 2026-10-04T00:04:09+00:00 | 3.8 | taskA: 75/100 evaluated (0.97/s), parse 0.960, set equality 0.920. |
| 2026-10-04T00:04:25+00:00 | 3.7 | SFT corpus assembled: 28,304 train (oversampling {'task_a': 2, 'task_c': 4}), task mix abstain 11%, query 34%, triage 55% |
| 2026-10-04T00:04:34+00:00 | 3.8 | taskA: 100/100 evaluated (0.97/s), parse 0.970, set equality 0.940. |
| 2026-10-04T00:11:24+00:00 | 3.7 | SFT corpus assembled: 28,304 train (oversampling {'task_a': 2, 'task_c': 4}), task mix abstain 11%, query 34%, triage 55% |
| 2026-10-04T00:11:24+00:00 | 3.7 | Stage 1 LoRA SFT starting: 28,304 train / 2,386 valid examples, rank 16, 16 layers, lr 1e-05, batch 4, 14152 iterations. |
| 2026-10-04T00:14:09+00:00 | 1.0 | Validation datasets: 10/12 resolved (biolip2_annotations, biolip2_artefacts, mgdb_glues, mgtbind_compounds, mgtbind_ternary, molgluedb_glues, protacdb_protacs, sievers_zf_screen, ubibrowser_literature_e3, ubibrowser_predicted_e3). Manifest at data/validation/MANIFEST.md. |
| 2026-10-04T00:14:09+00:00 | gate | G7 opened: 2 validation dataset(s) could not be obtained automatically: degronopedia, protcid_interfaces. |
| 2026-10-04T00:15:21+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-04T00:16:08+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-04T00:17:37+00:00 | gate | G6 opened: A decision on whether to ship the Degron Scan at all, now that spec 9.2 is measured and fails. |
| 2026-10-04T00:18:03+00:00 | 4.1b | About tab generated: 51 references, 10/12 datasets resolved, worked example selected, 2 value(s) not recorded. |
| 2026-10-04T00:37:00+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-04T00:37:14+00:00 | 4.1b | About tab generated: 51 references, 10/12 datasets resolved, worked example selected, 2 value(s) not recorded. |
| 2026-10-04T00:46:04+00:00 | 12.3 | references.bib: 45 references, 39 Crossref matched by search (0 preprints), 6 unmatched, 6 with no DOI, 2 with licence not determined. |
| 2026-10-04T00:46:48+00:00 | 12.3 | references.bib: 45 references, 39 Crossref matched by search (0 preprints), 6 unmatched, 6 with no DOI, 2 with licence not determined. |
| 2026-10-04T00:46:50+00:00 | 4.1b | About tab generated: 52 references, 10/12 datasets resolved, worked example selected, 2 value(s) not recorded. |
| 2026-10-04T00:50:16+00:00 | 4.1b | About tab generated: 52 references, 10/12 datasets resolved, worked example selected, 2 value(s) not recorded. |
| 2026-10-04T01:10:15+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 4 measured floor(s) missed. |
| 2026-10-04T01:10:23+00:00 | 4.1b | About tab generated: 52 references, 10/12 datasets resolved, worked example selected, 2 value(s) not recorded. |
| 2026-10-04T01:10:53+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-04T01:10:54+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 4 measured floor(s) missed. |
| 2026-10-04T01:10:59+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-04T01:11:00+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 4 measured floor(s) missed. |
| 2026-10-04T01:18:25+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-04T01:18:26+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 4 measured floor(s) missed. |
| 2026-10-04T01:21:30+00:00 | 1.0 | Validation datasets: 11/13 resolved (biolip2_annotations, biolip2_artefacts, digly_sites, mgdb_glues, mgtbind_compounds, mgtbind_ternary, molgluedb_glues, protacdb_protacs, sievers_zf_screen, ubibrowser_literature_e3, ubibrowser_predicted_e3). Manifest at data/validation/MANIFEST.md. |
| 2026-10-04T01:21:30+00:00 | gate | G7 opened: 2 validation dataset(s) could not be obtained automatically: degronopedia, protcid_interfaces. |
| 2026-10-04T01:23:33+00:00 | 2.3 | Accessibility fitted on 403 proteins: min_nz_rel_sasa 0.241, held-out AUC 0.5458 over 338 observed sites. Reach stays unfitted. |
| 2026-10-04T01:24:36+00:00 | 2.3 | Accessibility fit on 403 proteins scored held-out AUC 0.5458 against a 0.65 floor. Nothing written back; no verdict emitted. |
| 2026-10-04T01:25:39+00:00 | 2.3 | Accessibility fit on 403 proteins scored held-out AUC 0.5458 against a 0.65 floor. Nothing written back; no verdict emitted. |
| 2026-10-04T01:25:46+00:00 | 9 | Validation run against binman.sqlite: 2 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-04T01:25:48+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-04T01:25:49+00:00 | 9 | Validation run against binman.sqlite: 2 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-04T01:26:29+00:00 | 4.1b | About tab generated: 52 references, 11/13 datasets resolved, worked example selected, 2 value(s) not recorded. |
| 2026-10-04T01:26:31+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-04T01:26:32+00:00 | 9 | Validation run against binman.sqlite: 2 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-04T01:27:55+00:00 | 3.9 | MLX adapter converted to PEFT: 224 tensors, rank 8, alpha 160, 16 layers. |
| 2026-10-04T01:29:42+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-04T01:29:43+00:00 | 9 | Validation run against binman.sqlite: 2 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-04T01:39:37+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-04T01:39:38+00:00 | 9 | Validation run against binman.sqlite: 2 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-04T01:55:52+00:00 | 3.9 | MLX adapter converted to PEFT: 224 tensors, rank 8, alpha 160, 16 layers. |
| 2026-10-04T01:56:25+00:00 | 3.9 | MLX adapter converted to PEFT: 224 tensors, rank 8, alpha 160, 16 layers. |
| 2026-10-04T01:57:55+00:00 | 3.9 | MLX adapter converted to PEFT: 224 tensors, rank 8, alpha 160, 16 layers. |
| 2026-10-04T01:58:39+00:00 | 3.9 | MLX adapter converted to PEFT: 224 tensors, rank 8, alpha 160, 16 layers. |
| 2026-10-04T01:59:06+00:00 | 3.9 | MLX adapter converted to PEFT: 224 tensors, rank 8, alpha 160, 16 layers. |
| 2026-10-04T02:00:31+00:00 | 3.9 | MLX adapter converted to PEFT: 224 tensors, rank 8, alpha 160, 16 layers. |
| 2026-10-04T02:01:24+00:00 | 3.9 | MLX adapter converted to PEFT: 224 tensors, rank 8, alpha 160, 16 layers. |
| 2026-10-04T02:02:59+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-04T02:03:00+00:00 | 9 | Validation run against binman.sqlite: 2 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-04T02:08:38+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-04T02:08:39+00:00 | 9 | Validation run against binman.sqlite: 2 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-04T02:13:43+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-04T02:13:44+00:00 | 9 | Validation run against binman.sqlite: 2 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-04T03:03:26+00:00 | 3.7 | Stage 1 complete in 172.0 min. Best validation loss 0.0 at iteration 6500. |
| 2026-10-04T03:03:34+00:00 | 3.7 | Fuse succeeded: models/binman-lm/fused |
| 2026-10-04T03:03:49+00:00 | 3.8 | round06: loading mlx-community/Qwen2.5-3B-Instruct-4bit with adapters at models/binman-lm/adapters |
| 2026-10-04T03:04:22+00:00 | 3.8 | round06 synthetic: 25/120 evaluated (0.90/s), parse 1.000, set equality 1.000. |
| 2026-10-04T03:04:49+00:00 | 3.8 | round06 synthetic: 50/120 evaluated (0.91/s), parse 0.980, set equality 0.980. |
| 2026-10-04T03:05:15+00:00 | 3.8 | round06 synthetic: 75/120 evaluated (0.93/s), parse 0.973, set equality 0.973. |
| 2026-10-04T03:05:41+00:00 | 3.8 | round06 synthetic: 100/120 evaluated (0.93/s), parse 0.980, set equality 0.980. |
| 2026-10-04T03:06:38+00:00 | 3.8 | round06: parse rate 0.9833, set equality 0.9833 on 120 synthetic queries. |
| 2026-10-04T03:07:36+00:00 | 3.8 | round06: loading mlx-community/Qwen2.5-3B-Instruct-4bit with adapters at models/binman-lm/adapters |
| 2026-10-04T03:08:08+00:00 | 3.8 | round06 synthetic: 25/240 evaluated (0.90/s), parse 1.000, set equality 1.000. |
| 2026-10-04T03:08:35+00:00 | 3.8 | round06 synthetic: 50/240 evaluated (0.91/s), parse 0.980, set equality 0.980. |
| 2026-10-04T03:09:01+00:00 | 3.8 | round06 synthetic: 75/240 evaluated (0.92/s), parse 0.973, set equality 0.973. |
| 2026-10-04T03:09:28+00:00 | 3.8 | round06 synthetic: 100/240 evaluated (0.93/s), parse 0.980, set equality 0.980. |
| 2026-10-04T03:09:55+00:00 | 3.8 | round06 synthetic: 125/240 evaluated (0.93/s), parse 0.984, set equality 0.984. |
| 2026-10-04T03:10:22+00:00 | 3.8 | round06 synthetic: 150/240 evaluated (0.93/s), parse 0.987, set equality 0.987. |
| 2026-10-04T03:10:49+00:00 | 3.8 | round06 synthetic: 175/240 evaluated (0.93/s), parse 0.989, set equality 0.989. |
| 2026-10-04T03:11:15+00:00 | 3.8 | round06 synthetic: 200/240 evaluated (0.93/s), parse 0.990, set equality 0.990. |
| 2026-10-04T03:11:43+00:00 | 3.8 | round06 synthetic: 225/240 evaluated (0.93/s), parse 0.991, set equality 0.991. |
| 2026-10-04T03:12:45+00:00 | 3.8 | round06: loading mlx-community/Qwen2.5-3B-Instruct-4bit with adapters at models/binman-lm/adapters |
| 2026-10-04T03:13:18+00:00 | 3.8 | round06 synthetic: 25/240 evaluated (0.90/s), parse 1.000, set equality 1.000. |
| 2026-10-04T03:13:45+00:00 | 3.8 | round06 synthetic: 50/240 evaluated (0.91/s), parse 0.980, set equality 0.980. |
| 2026-10-04T03:14:11+00:00 | 3.8 | round06 synthetic: 75/240 evaluated (0.93/s), parse 0.973, set equality 0.973. |
| 2026-10-04T03:14:38+00:00 | 3.8 | round06 synthetic: 100/240 evaluated (0.93/s), parse 0.980, set equality 0.980. |
| 2026-10-04T03:15:05+00:00 | 3.8 | round06 synthetic: 125/240 evaluated (0.93/s), parse 0.984, set equality 0.984. |
| 2026-10-04T03:15:32+00:00 | 3.8 | round06 synthetic: 150/240 evaluated (0.93/s), parse 0.987, set equality 0.987. |
| 2026-10-04T03:15:59+00:00 | 3.8 | round06 synthetic: 175/240 evaluated (0.93/s), parse 0.989, set equality 0.989. |
| 2026-10-04T03:16:25+00:00 | 3.8 | round06 synthetic: 200/240 evaluated (0.93/s), parse 0.990, set equality 0.990. |
| 2026-10-04T03:16:53+00:00 | 3.8 | round06 synthetic: 225/240 evaluated (0.93/s), parse 0.991, set equality 0.991. |
| 2026-10-04T03:18:29+00:00 | 3.8 | round06: parse rate 0.9875, set equality 0.9833 on 240 synthetic queries. |
| 2026-10-04T03:19:13+00:00 | 3.8 | round06: loading mlx-community/Qwen2.5-3B-Instruct-4bit with adapters at models/binman-lm/adapters |
| 2026-10-04T03:19:46+00:00 | 3.8 | round06 synthetic: 25/120 evaluated (0.90/s), parse 1.000, set equality 1.000. |
| 2026-10-04T03:20:13+00:00 | 3.8 | round06 synthetic: 50/120 evaluated (0.91/s), parse 0.980, set equality 0.980. |
| 2026-10-04T03:20:39+00:00 | 3.8 | round06 synthetic: 75/120 evaluated (0.93/s), parse 0.973, set equality 0.973. |
| 2026-10-04T03:21:06+00:00 | 3.8 | round06 synthetic: 100/120 evaluated (0.93/s), parse 0.980, set equality 0.980. |
| 2026-10-04T03:22:55+00:00 | 3.8 | round06: parse rate 0.9833, set equality 0.9833 on 120 synthetic queries. |
| 2026-10-04T03:23:29+00:00 | 3.7 | SFT corpus assembled: 28,304 train (oversampling {'task_a': 2, 'task_c': 4}), task mix abstain 11%, query 34%, triage 55% |
| 2026-10-04T03:23:29+00:00 | 3.7 | Stage 1 LoRA SFT starting: 28,304 train / 2,386 valid examples, rank 8, 32 layers, lr 1e-05, batch 4, 14152 iterations. |
| 2026-10-04T03:24:49+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-04T03:24:50+00:00 | 9 | Validation run against binman.sqlite: 2 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-04T07:04:48+00:00 | 3.7 | Stage 1 complete in 221.3 min. Best validation loss 0.0 at iteration 12100. |
| 2026-10-04T07:04:56+00:00 | 3.7 | Fuse succeeded: models/binman-lm/fused |
| 2026-10-04T07:04:57+00:00 | 3.8 | round07-32layers: loading mlx-community/Qwen2.5-3B-Instruct-4bit with adapters at models/binman-lm/adapters |
| 2026-10-04T07:05:45+00:00 | 3.8 | round07-32layers synthetic: 25/120 evaluated (0.58/s), parse 1.000, set equality 1.000. |
| 2026-10-04T07:06:26+00:00 | 3.8 | round07-32layers synthetic: 50/120 evaluated (0.59/s), parse 1.000, set equality 1.000. |
| 2026-10-04T07:07:07+00:00 | 3.8 | round07-32layers synthetic: 75/120 evaluated (0.60/s), parse 1.000, set equality 1.000. |
| 2026-10-04T07:07:48+00:00 | 3.8 | round07-32layers synthetic: 100/120 evaluated (0.60/s), parse 1.000, set equality 1.000. |
| 2026-10-04T07:10:22+00:00 | 3.8 | round07-32layers: parse rate 1.0, set equality 1.0 on 120 synthetic queries. |
| 2026-10-04T07:10:25+00:00 | 3.7 | SFT corpus assembled: 28,304 train (oversampling {'task_a': 2, 'task_c': 4}), task mix abstain 11%, query 34%, triage 55% |
| 2026-10-04T07:10:25+00:00 | 3.7 | Stage 1 LoRA SFT starting: 28,304 train / 2,386 valid examples, rank 32, 16 layers, lr 1e-05, batch 4, 14152 iterations. |
| 2026-10-04T10:04:02+00:00 | 3.7 | Stage 1 complete in 173.6 min. Best validation loss 0.001 at iteration 7800. |
| 2026-10-04T10:04:14+00:00 | 3.7 | Fuse succeeded: models/binman-lm/fused |
| 2026-10-04T10:04:16+00:00 | 3.8 | round08-rank32: loading mlx-community/Qwen2.5-3B-Instruct-4bit with adapters at models/binman-lm/adapters |
| 2026-10-04T10:04:48+00:00 | 3.8 | round08-rank32 synthetic: 25/120 evaluated (0.91/s), parse 1.000, set equality 1.000. |
| 2026-10-04T10:05:15+00:00 | 3.8 | round08-rank32 synthetic: 50/120 evaluated (0.92/s), parse 1.000, set equality 1.000. |
| 2026-10-04T10:05:41+00:00 | 3.8 | round08-rank32 synthetic: 75/120 evaluated (0.94/s), parse 0.987, set equality 0.987. |
| 2026-10-04T10:06:07+00:00 | 3.8 | round08-rank32 synthetic: 100/120 evaluated (0.94/s), parse 0.990, set equality 0.990. |
| 2026-10-04T10:07:54+00:00 | 3.8 | round08-rank32: parse rate 0.9917, set equality 0.9917 on 120 synthetic queries. |
| 2026-10-04T10:07:56+00:00 | 3.7 | SFT corpus assembled: 28,304 train (oversampling {'task_a': 2, 'task_c': 4}), task mix abstain 11%, query 34%, triage 55% |
| 2026-10-04T10:07:56+00:00 | 3.7 | Stage 1 LoRA SFT starting: 28,304 train / 2,386 valid examples, rank 32, 16 layers, lr 1e-05, batch 4, 14152 iterations. |
| 2026-10-04T10:08:52+00:00 | 3.7 | Stage 1 FAILED with exit -15. See data/interim/lm_stage1.log. |
| 2026-10-04T10:09:39+00:00 | 3.7 | SFT corpus assembled: 28,304 train (oversampling {'task_a': 2, 'task_c': 4}), task mix abstain 11%, query 34%, triage 55% |
| 2026-10-04T10:09:39+00:00 | 3.7 | Stage 1 LoRA SFT starting: 28,304 train / 2,386 valid examples, rank 32, 32 layers, lr 1e-05, batch 4, 14152 iterations. |
| 2026-10-04T10:42:06+00:00 | 3.7 | Stage 1 FAILED with exit -15. See data/interim/lm_stage1.log. |
| 2026-10-04T10:42:28+00:00 | 3.7 | SFT corpus assembled: 28,304 train (oversampling {'task_a': 2, 'task_c': 4}), task mix abstain 11%, query 34%, triage 55% |
| 2026-10-04T10:42:28+00:00 | 3.7 | Stage 1 LoRA SFT starting: 28,304 train / 2,386 valid examples, rank 32, 32 layers, lr 1e-05, batch 2, 14152 iterations. |
| 2026-10-04T10:47:42+00:00 | 3.9 | MLX adapter converted to PEFT: 448 tensors, rank 8, alpha 160, 32 layers. |
| 2026-10-04T12:55:52+00:00 | 3.7 | Stage 1 complete in 133.2 min. Best validation loss 0.0 at iteration 3500. |
| 2026-10-04T12:56:07+00:00 | 3.7 | Fuse succeeded: models/binman-lm/fused |
| 2026-10-04T12:56:09+00:00 | 3.8 | round09-32layers-rank32: loading mlx-community/Qwen2.5-3B-Instruct-4bit with adapters at models/binman-lm/adapters |
| 2026-10-04T12:56:56+00:00 | 3.8 | round09-32layers-rank32 synthetic: 25/120 evaluated (0.59/s), parse 1.000, set equality 1.000. |
| 2026-10-04T12:57:35+00:00 | 3.8 | round09-32layers-rank32 synthetic: 50/120 evaluated (0.61/s), parse 1.000, set equality 1.000. |
| 2026-10-04T12:58:14+00:00 | 3.8 | round09-32layers-rank32 synthetic: 75/120 evaluated (0.62/s), parse 1.000, set equality 1.000. |
| 2026-10-04T12:58:53+00:00 | 3.8 | round09-32layers-rank32 synthetic: 100/120 evaluated (0.63/s), parse 1.000, set equality 1.000. |
| 2026-10-04T13:01:20+00:00 | 3.8 | round09-32layers-rank32: parse rate 1.0, set equality 1.0 on 120 synthetic queries. |
| 2026-10-04T13:09:29+00:00 | 9 | Validation run against binman.sqlite: 2 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-04T13:09:58+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-04T13:10:49+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-04T13:10:50+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-04T13:12:14+00:00 | 5.2 | Sequence model over 5,663 zinc fingers: held-out AUC 0.6334 (sd 0.0772) against the geometry's 0.4407. |
| 2026-10-04T13:13:02+00:00 | 5.2 | Sequence model over 5,663 zinc fingers: held-out AUC 0.6334 (sd 0.0772) against the geometry's 0.4407. |
| 2026-10-04T13:13:39+00:00 | 5.2 | Sequence model over 5,663 zinc fingers: held-out AUC 0.6368 (sd 0.0895) against the geometry's 0.4407. |
| 2026-10-04T13:14:01+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-04T13:14:31+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-04T13:14:32+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-04T13:14:49+00:00 | 4.1b | About tab generated: 52 references, 11/13 datasets resolved, worked example selected, 2 value(s) not recorded. |
| 2026-10-04T13:40:22+00:00 | 3.7 | SFT corpus assembled: 28,304 train (oversampling {'task_a': 2, 'task_c': 4}), task mix abstain 11%, query 34%, triage 55% |
| 2026-10-04T13:40:22+00:00 | 3.7 | Stage 1 LoRA SFT starting: 28,304 train / 2,386 valid examples, rank 8, 32 layers, lr 1e-05, batch 1, 4636 iterations. |
| 2026-10-04T13:41:48+00:00 | 5.2 | Sequence model over 5,663 zinc fingers: held-out AUC 0.6363 (sd 0.0822) against the geometry's 0.4407. |
| 2026-10-04T13:43:00+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-04T13:43:01+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-04T13:47:55+00:00 | 3.7 | Stage 1 FAILED with exit -15. See data/interim/lm_stage1.log. |
| 2026-10-04T13:48:52+00:00 | 3.7 | SFT corpus assembled: 28,304 train (oversampling {'task_a': 2, 'task_c': 4}), task mix abstain 11%, query 34%, triage 55% |
| 2026-10-04T13:48:52+00:00 | 3.7 | Stage 1 LoRA SFT starting: 28,304 train / 2,386 valid examples, rank 8, 32 layers, lr 1e-05, batch 2, 14152 iterations. |
| 2026-10-04T14:21:26+00:00 | 3.7 | Stage 1 FAILED with exit -15. See data/interim/lm_stage1.log. |
| 2026-10-04T14:21:51+00:00 | 3.7 | SFT corpus assembled: 28,304 train (oversampling {'task_a': 2, 'task_c': 4}), task mix abstain 11%, query 34%, triage 55% |
| 2026-10-04T14:21:51+00:00 | 3.7 | Stage 1 LoRA SFT starting: 28,304 train / 2,386 valid examples, rank 8, 32 layers, lr 1e-05, batch 2, 14152 iterations. |
| 2026-10-04T14:32:22+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-04T14:32:23+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-04T15:11:37+00:00 | 5.2 | Sequence model over 5,663 zinc fingers: held-out AUC 0.6363 (sd 0.0822) against the geometry's 0.4407. |
| 2026-10-04T15:12:17+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-04T15:12:18+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-04T15:24:37+00:00 | 5.2 | ALV1: nested AUC 0.5566, sensitivity 0.3777, specificity 0.6873 on 212 positives. |
| 2026-10-04T15:24:38+00:00 | 5.2 | Ace.4.Ph.Glu.Amide: nested AUC 0.5098, sensitivity 0.4078, specificity 0.6317 on 147 positives. |
| 2026-10-04T15:25:23+00:00 | 5.2 | ALV1: nested AUC 0.5648, sensitivity 0.5430, specificity 0.5296 on 212 positives. |
| 2026-10-04T15:25:24+00:00 | 5.2 | Ace.4.Ph.Glu.Amide: nested AUC 0.5352, sensitivity 0.4076, specificity 0.6447 on 147 positives. |
| 2026-10-04T15:27:05+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-04T15:27:06+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-04T15:37:49+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-04T15:37:50+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-04T15:42:09+00:00 | 5.2 | Alanine scan: 59,570 measurements over 31 genes and 20 compounds mapped to anchored positions. |
| 2026-10-04T15:43:56+00:00 | 5.2 | imid_degradation_score written for 9 degron candidates; 391 carry no C2H2 motif and are left NULL. |
| 2026-10-04T15:46:48+00:00 | 5.2 | imid_degradation_score written for 4,650 degron candidates; 17,067 carry no C2H2 motif and are left NULL. |
| 2026-10-04T15:47:34+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-04T15:47:35+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-04T15:53:15+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-04T15:53:16+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-04T15:55:01+00:00 | 12.3 | references.bib: 45 references, 39 Crossref matched by search (0 preprints), 6 unmatched, 6 with no DOI, 0 with licence not determined. |
| 2026-10-04T15:55:22+00:00 | 4.1b | About tab generated: 52 references, 11/13 datasets resolved, worked example selected, 1 value(s) not recorded. |
| 2026-10-04T15:56:48+00:00 | 4.1b | About tab generated: 52 references, 11/13 datasets resolved, worked example selected, 1 value(s) not recorded. |
| 2026-10-04T15:57:42+00:00 | 4.1b | About tab generated: 52 references, 11/13 datasets resolved, worked example selected, 1 value(s) not recorded. |
| 2026-10-04T16:07:50+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-04T16:07:51+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-04T16:23:03+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-04T16:23:04+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-04T16:26:25+00:00 | 5.2 | imid_degradation_score written for 4,650 degron candidates; 17,067 carry no C2H2 motif and are left NULL. |
| 2026-10-04T16:27:38+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-04T16:27:39+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-04T17:11:21+00:00 | 9.2 | Glutarimide panel: the pomalidomide model transfers to 24 of 24 compounds gene-disjoint, mean AUC 0.7789, permutation p=0.0005. Breadth against AUC Spearman 0.1751 (p=0.4131). |
| 2026-10-04T17:14:36+00:00 | 12.3 | references.bib: 46 references, 40 Crossref matched by search (0 preprints), 6 unmatched, 6 with no DOI, 0 with licence not determined. |
| 2026-10-04T17:14:47+00:00 | 4.1b | About tab generated: 53 references, 11/13 datasets resolved, worked example selected, 1 value(s) not recorded. |
| 2026-10-04T17:14:48+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-04T17:14:49+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-04T17:15:00+00:00 | 4.1b | About tab generated: 53 references, 11/13 datasets resolved, worked example selected, 1 value(s) not recorded. |
| 2026-10-04T17:28:34+00:00 | 9.5 | Lysine feature ablation over 12,705 lysines in 403 proteins: best within-protein AUC 0.6258 against the 0.65 floor. Misses it. |
| 2026-10-04T17:29:52+00:00 | 4.1b | About tab generated: 53 references, 11/13 datasets resolved, worked example selected, 1 value(s) not recorded. |
| 2026-10-04T17:29:53+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-04T17:29:54+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-04T17:31:24+00:00 | 2.3 | Accessibility fit on 403 proteins scored held-out AUC 0.5458 against a 0.65 floor. No boundary written back and no verdict emitted; the measurement is recorded as provenance. |
| 2026-10-04T17:31:34+00:00 | 4.1b | About tab generated: 53 references, 11/13 datasets resolved, worked example selected, 1 value(s) not recorded. |
| 2026-10-04T17:31:35+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-04T17:31:36+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-04T17:32:13+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-04T17:32:14+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-04T17:39:42+00:00 | 2.1b | Zinc-finger scan over 200 cached models. |
| 2026-10-04T17:39:43+00:00 | 2.1b | Zinc-finger table: 10 C2H2 motifs over 1 proteins, of which 2 (20.0%) carry no hairpin candidate and were unreachable by the per-candidate column. |
| 2026-10-04T17:43:51+00:00 | 2.1b | Zinc-finger scan over 20,279 cached models. |
| 2026-10-04T17:44:15+00:00 | 2.1b | Zinc-finger table: 7,452 C2H2 motifs over 1,123 proteins, of which 2,792 (37.5%) carry no hairpin candidate and were unreachable by the per-candidate column. |
| 2026-10-04T17:48:58+00:00 | 2.1b | Zinc-finger scan over 20,279 cached models. |
| 2026-10-04T17:49:20+00:00 | 2.1b | Zinc-finger table: 7,452 C2H2 motifs over 1,123 proteins, of which 2,792 (37.5%) carry no hairpin candidate and were unreachable by the per-candidate column. |
| 2026-10-04T17:51:17+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-04T17:51:18+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-04T17:51:50+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-04T17:51:51+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-04T18:32:56+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-04T18:32:57+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-04T18:33:43+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-04T18:33:44+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-04T18:36:02+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-04T18:36:03+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-04T18:48:04+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-04T18:48:05+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-04T19:12:59+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-04T19:13:00+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-04T20:21:08+00:00 | 2.1b | Zinc-finger scan over 20,279 cached models. |
| 2026-10-04T20:25:55+00:00 | 2.1b | Zinc-finger scan over 20,279 cached models. |
| 2026-10-04T20:26:18+00:00 | 2.1b | Zinc-finger table: 7,452 C2H2 motifs over 1,123 proteins, of which 2,792 (37.5%) carry no hairpin candidate and were unreachable by the per-candidate column. |
| 2026-10-04T20:27:25+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-04T20:27:26+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-04T20:39:25+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-04T20:39:26+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-04T20:49:45+00:00 | 4.1b | About tab generated: 53 references, 11/13 datasets resolved, worked example selected, 0 value(s) not recorded, 1 source(s) publish no licence. |
| 2026-10-04T20:49:57+00:00 | 4.1b | About tab generated: 53 references, 11/13 datasets resolved, worked example selected, 0 value(s) not recorded, 1 source(s) publish no licence. |
| 2026-10-04T20:50:45+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-04T20:50:46+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-04T20:51:12+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-04T20:51:13+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-04T20:51:16+00:00 | 4.1b | About tab generated: 53 references, 11/13 datasets resolved, worked example selected, 0 value(s) not recorded, 1 source(s) publish no licence. |
| 2026-10-04T21:32:28+00:00 | 9.2 | Degron ablation: pooling and position selection both lose to the shipped model (0.8304); nested position selection scores 0.7449. |
| 2026-10-04T21:32:54+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-04T21:32:55+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-04T21:59:31+00:00 | 1.3 | Bridge run starting: 52,821 entries pending of 52,822 catalogued (tiers 1 to 3), 16 IO workers, 14 geometry workers. |
| 2026-10-04T22:04:31+00:00 | 1.3 | 9,160/52,821 entries, 9,157 bridges, 26 failed, 30.5 entries/s, ~0.4 h remaining. |
| 2026-10-04T22:09:31+00:00 | 1.3 | 15,207/52,821 entries, 16,152 bridges, 26 failed, 25.3 entries/s, ~0.4 h remaining. |
| 2026-10-04T22:14:31+00:00 | 1.3 | 20,205/52,821 entries, 24,351 bridges, 26 failed, 22.4 entries/s, ~0.4 h remaining. |
| 2026-10-04T22:19:31+00:00 | 1.3 | 22,959/52,821 entries, 31,672 bridges, 26 failed, 19.1 entries/s, ~0.4 h remaining. |
| 2026-10-04T22:24:31+00:00 | 1.3 | 25,164/52,821 entries, 39,433 bridges, 26 failed, 16.8 entries/s, ~0.5 h remaining. |
| 2026-10-04T22:29:31+00:00 | 1.3 | 27,242/52,821 entries, 45,294 bridges, 26 failed, 15.1 entries/s, ~0.5 h remaining. |
| 2026-10-04T22:34:31+00:00 | 1.3 | 28,961/52,821 entries, 55,668 bridges, 26 failed, 13.8 entries/s, ~0.5 h remaining. |
| 2026-10-04T22:39:31+00:00 | 1.3 | 30,640/52,821 entries, 66,132 bridges, 27 failed, 12.8 entries/s, ~0.5 h remaining. |
| 2026-10-04T22:44:33+00:00 | 1.3 | 31,621/52,821 entries, 84,173 bridges, 29 failed, 11.7 entries/s, ~0.5 h remaining. |
| 2026-10-04T22:49:33+00:00 | 1.3 | 32,132/52,821 entries, 110,087 bridges, 32 failed, 10.7 entries/s, ~0.5 h remaining. |
| 2026-10-04T22:54:33+00:00 | 1.3 | 32,652/52,821 entries, 127,923 bridges, 37 failed, 9.9 entries/s, ~0.6 h remaining. |
| 2026-10-04T22:59:35+00:00 | 1.3 | 33,042/52,821 entries, 154,156 bridges, 79 failed, 9.2 entries/s, ~0.6 h remaining. |
| 2026-10-04T23:04:35+00:00 | 1.3 | 33,266/52,821 entries, 183,596 bridges, 110 failed, 8.5 entries/s, ~0.6 h remaining. |
| 2026-10-04T23:09:35+00:00 | 1.3 | 33,865/52,821 entries, 196,723 bridges, 196 failed, 8.1 entries/s, ~0.7 h remaining. |
| 2026-10-04T23:14:35+00:00 | 1.3 | 34,772/52,821 entries, 215,766 bridges, 521 failed, 7.7 entries/s, ~0.6 h remaining. |
| 2026-10-04T23:14:49+00:00 | 9.4 | Assayed ubiquitylome: requesting 100 accessions in batches of 50. |
| 2026-10-04T23:14:49+00:00 | 9.4 | batch 0 failed: OSError: [Errno 63] File name too long: '/Users/dellboy/Documents/Vibe_Coding/BINMAN/data/cache/ebi_proteins/proteomics:A0A024R1R8.cif,A0A024RBG |
| 2026-10-04T23:14:49+00:00 | 9.4 | batch 1 failed: OSError: [Errno 63] File name too long: '/Users/dellboy/Documents/Vibe_Coding/BINMAN/data/cache/ebi_proteins/proteomics:A0A075B759.cif,A0A075B76 |
| 2026-10-04T23:14:49+00:00 | 9.4 | Assayed ubiquitylome: 0 lysines over 0 proteins, 0 ubiquitylated, 0 matched negatives. |
| 2026-10-04T23:15:11+00:00 | 9.4 | Assayed ubiquitylome: requesting 100 accessions in batches of 50. |
| 2026-10-04T23:15:13+00:00 | 9.4 | Assayed ubiquitylome: 253 lysines over 70 proteins, 18 ubiquitylated, 235 matched negatives. |
| 2026-10-04T23:15:29+00:00 | 9.4 | Assayed ubiquitylome: requesting 20,279 accessions in batches of 50. |
| 2026-10-04T23:15:50+00:00 | 9.4 | 1,050/20,279 accessions, 8,261 assayed lysines, 49.5/s. |
| 2026-10-04T23:16:19+00:00 | 9.4 | 2,050/20,279 accessions, 28,965 assayed lysines, 40.8/s. |
| 2026-10-04T23:16:51+00:00 | 9.4 | 3,050/20,279 accessions, 54,844 assayed lysines, 37.0/s. |
| 2026-10-04T23:17:22+00:00 | 9.4 | 4,050/20,279 accessions, 70,904 assayed lysines, 35.9/s. |
| 2026-10-04T23:18:02+00:00 | 9.4 | 5,050/20,279 accessions, 94,124 assayed lysines, 32.9/s. |
| 2026-10-04T23:18:53+00:00 | 9.4 | 6,050/20,279 accessions, 117,710 assayed lysines, 29.6/s. |
| 2026-10-04T23:19:30+00:00 | 9.4 | 7,050/20,279 accessions, 135,362 assayed lysines, 29.2/s. |
| 2026-10-04T23:19:35+00:00 | 1.3 | 52,224/52,821 entries, 225,407 bridges, 851 failed, 10.9 entries/s, ~0.0 h remaining. |
| 2026-10-04T23:20:16+00:00 | 9.4 | 8,050/20,279 accessions, 164,887 assayed lysines, 28.0/s. |
| 2026-10-04T23:20:35+00:00 | 1.3 | Bridge run finished: 52,821 entries in 81.1 min, 225,416 bridges, 1,043 failed, 10.9 entries/s. |
| 2026-10-04T23:21:03+00:00 | 9.4 | 9,050/20,279 accessions, 188,604 assayed lysines, 27.1/s. |
| 2026-10-04T23:21:36+00:00 | 9.4 | 10,050/20,279 accessions, 210,579 assayed lysines, 27.4/s. |
| 2026-10-04T23:21:40+00:00 | 1.3 | Bridge run starting: 1,043 entries pending of 52,822 catalogued (tiers 1 to 3), 16 IO workers, 14 geometry workers. |
| 2026-10-04T23:22:08+00:00 | 9.4 | 11,050/20,279 accessions, 228,492 assayed lysines, 27.7/s. |
| 2026-10-04T23:22:43+00:00 | 9.4 | 12,050/20,279 accessions, 250,281 assayed lysines, 27.7/s. |
| 2026-10-04T23:23:16+00:00 | 9.4 | 13,050/20,279 accessions, 268,564 assayed lysines, 27.9/s. |
| 2026-10-04T23:23:45+00:00 | 9.4 | 14,050/20,279 accessions, 284,507 assayed lysines, 28.3/s. |
| 2026-10-04T23:24:33+00:00 | 9.4 | 15,050/20,279 accessions, 305,836 assayed lysines, 27.6/s. |
| 2026-10-04T23:25:08+00:00 | 9.4 | 16,050/20,279 accessions, 326,029 assayed lysines, 27.7/s. |
| 2026-10-04T23:25:43+00:00 | 9.4 | 17,050/20,279 accessions, 345,331 assayed lysines, 27.8/s. |
| 2026-10-04T23:26:16+00:00 | 9.4 | 18,050/20,279 accessions, 364,888 assayed lysines, 27.9/s. |
| 2026-10-04T23:26:46+00:00 | 1.3 | 55/1,043 entries, 5,393 bridges, 0 failed, 0.2 entries/s, ~1.5 h remaining. |
| 2026-10-04T23:26:51+00:00 | 9.4 | 19,050/20,279 accessions, 387,804 assayed lysines, 27.9/s. |
| 2026-10-04T23:27:26+00:00 | 9.4 | 20,050/20,279 accessions, 414,163 assayed lysines, 27.9/s. |
| 2026-10-04T23:27:35+00:00 | 9.4 | Assayed ubiquitylome: 419,405 lysines over 18,003 proteins, 110,108 ubiquitylated, 309,297 matched negatives. |
| 2026-10-04T23:31:48+00:00 | 1.3 | 96/1,043 entries, 14,059 bridges, 0 failed, 0.2 entries/s, ~1.7 h remaining. |
| 2026-10-04T23:36:51+00:00 | 1.3 | 180/1,043 entries, 29,944 bridges, 0 failed, 0.2 entries/s, ~1.2 h remaining. |
| 2026-10-04T23:42:21+00:00 | 1.3 | 255/1,043 entries, 36,297 bridges, 1 failed, 0.2 entries/s, ~1.1 h remaining. |
| 2026-10-04T23:47:22+00:00 | 1.3 | 335/1,043 entries, 40,139 bridges, 1 failed, 0.2 entries/s, ~0.9 h remaining. |
| 2026-10-04T23:52:22+00:00 | 1.3 | 584/1,043 entries, 44,438 bridges, 5 failed, 0.3 entries/s, ~0.4 h remaining. |
| 2026-10-04T23:57:23+00:00 | 1.3 | 738/1,043 entries, 46,666 bridges, 6 failed, 0.3 entries/s, ~0.2 h remaining. |
| 2026-10-05T00:02:31+00:00 | 1.3 | 798/1,043 entries, 47,987 bridges, 11 failed, 0.3 entries/s, ~0.2 h remaining. |
| 2026-10-05T00:04:06+00:00 | 9.4 | Reach on induced ternaries: 136 assayed lysines over 68 complexes, 64 ubiquitylated. |
| 2026-10-05T00:05:06+00:00 | 9.4 | Reach on induced ternaries: 0 assayed lysines over 68 complexes, 0 ubiquitylated. |
| 2026-10-05T00:05:44+00:00 | 9.4 | Reach on induced ternaries: 369 assayed lysines over 68 complexes, 181 ubiquitylated. |
| 2026-10-05T00:07:32+00:00 | 1.3 | 985/1,043 entries, 53,680 bridges, 19 failed, 0.4 entries/s, ~0.0 h remaining. |
| 2026-10-05T00:12:49+00:00 | 1.3 | 1,041/1,043 entries, 56,829 bridges, 19 failed, 0.3 entries/s, ~0.0 h remaining. |
| 2026-10-05T00:17:50+00:00 | 1.3 | 1,041/1,043 entries, 56,829 bridges, 19 failed, 0.3 entries/s, ~0.0 h remaining. |
| 2026-10-05T00:23:16+00:00 | 1.3 | 1,042/1,043 entries, 57,115 bridges, 19 failed, 0.3 entries/s, ~0.0 h remaining. |
| 2026-10-05T00:28:16+00:00 | 1.3 | 1,042/1,043 entries, 57,115 bridges, 19 failed, 0.3 entries/s, ~0.0 h remaining. |
| 2026-10-05T00:29:35+00:00 | 1.3 | Bridge run finished: 1,043 entries in 67.9 min, 57,715 bridges, 19 failed, 0.3 entries/s. |
| 2026-10-05T00:32:50+00:00 | 4.3 | Atlas built: 52,821 entries, 283,131 bridges (15,451 novel), 9,981 ligands, 21,717 degrons, 650 ligases, 1,650 lysines, 155.9 MB. |
| 2026-10-05T00:34:04+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-05T00:34:48+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-05T00:34:49+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-05T00:39:05+00:00 | 2.1b | Zinc-finger scan over 20,279 cached models. |
| 2026-10-05T00:39:30+00:00 | 2.1b | Zinc-finger table: 7,452 C2H2 motifs over 1,123 proteins, of which 2,792 (37.5%) carry no hairpin candidate and were unreachable by the per-candidate column. |
| 2026-10-05T00:39:37+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-05T00:39:38+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-05T00:40:19+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-05T00:40:20+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-05T01:07:41+00:00 | 5.2 | imid_degradation_score written for 4,650 degron candidates; 17,067 carry no C2H2 motif and are left NULL. |
| 2026-10-05T01:08:15+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-05T01:08:16+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-05T01:36:16+00:00 | 3.8 | round07-on-rebuilt-atlas: loading mlx-community/Qwen2.5-3B-Instruct-4bit with adapters at models/binman-lm/runs/binman-qwen-2.5-3b-4bit-round07 |
| 2026-10-05T01:41:05+00:00 | 3.8 | round07-on-rebuilt-atlas synthetic: 25/120 evaluated (0.09/s), parse 1.000, set equality 1.000. |
| 2026-10-05T01:45:32+00:00 | 3.8 | round07-on-rebuilt-atlas synthetic: 50/120 evaluated (0.09/s), parse 1.000, set equality 1.000. |
| 2026-10-05T01:49:59+00:00 | 3.8 | round07-on-rebuilt-atlas synthetic: 75/120 evaluated (0.09/s), parse 1.000, set equality 1.000. |
| 2026-10-05T01:54:28+00:00 | 3.8 | round07-on-rebuilt-atlas synthetic: 100/120 evaluated (0.09/s), parse 1.000, set equality 1.000. |
| 2026-10-05T01:59:35+00:00 | 3.7 | Stage 1 complete in 697.6 min. Best validation loss 0.0 at iteration 2400. |
| 2026-10-05T01:59:53+00:00 | 3.7 | Fuse succeeded: models/binman-lm/fused |
| 2026-10-05T01:59:55+00:00 | 3.8 | round13-32b-1epoch: loading mlx-community/Qwen2.5-32B-Instruct-4bit with adapters at models/binman-lm/adapters |
| 2026-10-05T02:02:20+00:00 | 3.8 | round07-on-rebuilt-atlas: parse rate 1.0, set equality 1.0 on 120 synthetic queries. |
| 2026-10-05T02:02:47+00:00 | 3.8 | round13-32b-1epoch synthetic: 25/120 evaluated (0.16/s), parse 1.000, set equality 1.000. |
| 2026-10-05T02:02:55+00:00 | 3.8 | round14-32b-1epoch: loading mlx-community/Qwen2.5-32B-Instruct-4bit with adapters at models/binman-lm/runs/binman-qwen-2.5-32b-4bit-round14 |
| 2026-10-05T02:05:40+00:00 | 3.8 | round13-32b-1epoch synthetic: 50/120 evaluated (0.15/s), parse 1.000, set equality 1.000. |
| 2026-10-05T02:06:03+00:00 | 3.8 | round14-32b-1epoch synthetic: 25/120 evaluated (0.14/s), parse 1.000, set equality 1.000. |
| 2026-10-05T02:08:33+00:00 | 3.8 | round13-32b-1epoch synthetic: 75/120 evaluated (0.15/s), parse 1.000, set equality 1.000. |
| 2026-10-05T02:09:01+00:00 | 3.8 | round14-32b-1epoch synthetic: 50/120 evaluated (0.14/s), parse 1.000, set equality 1.000. |
| 2026-10-05T02:11:28+00:00 | 3.8 | round13-32b-1epoch synthetic: 100/120 evaluated (0.15/s), parse 1.000, set equality 1.000. |
| 2026-10-05T02:11:55+00:00 | 3.8 | round14-32b-1epoch synthetic: 75/120 evaluated (0.14/s), parse 1.000, set equality 1.000. |
| 2026-10-05T02:14:10+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-05T02:14:11+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-05T02:14:50+00:00 | 3.8 | round14-32b-1epoch synthetic: 100/120 evaluated (0.14/s), parse 1.000, set equality 1.000. |
| 2026-10-05T02:15:16+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-05T02:15:17+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-05T02:20:23+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-05T02:20:24+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-05T02:22:47+00:00 | 12.3 | references.bib: 46 references, 40 Crossref matched by search (0 preprints), 6 unmatched, 6 with no DOI, 0 with licence not determined. |
| 2026-10-05T02:22:51+00:00 | 4.1b | About tab generated: 53 references, 11/13 datasets resolved, worked example selected, 0 value(s) not recorded, 0 source(s) publish no licence. |
| 2026-10-05T02:23:29+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-05T02:23:30+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-05T02:28:03+00:00 | 3.8 | round13-32b-1epoch: parse rate 1.0, set equality 1.0 on 120 synthetic queries. |
| 2026-10-05T02:29:38+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-05T02:29:39+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-05T02:34:36+00:00 | 3.8 | round14-32b-1epoch: parse rate 1.0, set equality 1.0 on 120 synthetic queries. |
| 2026-10-05T02:37:26+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-05T02:37:27+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-05T02:43:14+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-05T02:43:15+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-05T03:15:58+00:00 | 1.1 | Tier 1 seed: 6,143 entries referenced by the resolved validation datasets plus the spec 12.3 reference list. |
| 2026-10-05T03:15:58+00:00 | 1.1 | RCSB Search API: 130,391 entries with >= 2 polymer entities and >= 1 non-polymer entity. |
| 2026-10-05T03:16:03+00:00 | 1.1 | Retrieved 130,391 candidate identifiers. |
| 2026-10-05T03:16:25+00:00 | 1.1 | Metadata fetched for 2,000 of 130,391 entries. |
| 2026-10-05T03:16:47+00:00 | 1.1 | Metadata fetched for 4,000 of 130,391 entries. |
| 2026-10-05T03:17:08+00:00 | 1.1 | Metadata fetched for 6,000 of 130,391 entries. |
| 2026-10-05T03:17:25+00:00 | 1.1 | Metadata fetched for 8,000 of 130,391 entries. |
| 2026-10-05T03:17:44+00:00 | 1.1 | Metadata fetched for 10,000 of 130,391 entries. |
| 2026-10-05T03:18:03+00:00 | 1.1 | Metadata fetched for 12,000 of 130,391 entries. |
| 2026-10-05T03:18:23+00:00 | 1.1 | Metadata fetched for 14,000 of 130,391 entries. |
| 2026-10-05T03:18:39+00:00 | 1.1 | Metadata fetched for 16,000 of 130,391 entries. |
| 2026-10-05T03:18:52+00:00 | 1.1 | Metadata fetched for 18,000 of 130,391 entries. |
| 2026-10-05T03:19:05+00:00 | 1.1 | Metadata fetched for 20,000 of 130,391 entries. |
| 2026-10-05T03:19:19+00:00 | 1.1 | Metadata fetched for 22,000 of 130,391 entries. |
| 2026-10-05T03:19:32+00:00 | 1.1 | Metadata fetched for 24,000 of 130,391 entries. |
| 2026-10-05T03:19:45+00:00 | 1.1 | Metadata fetched for 26,000 of 130,391 entries. |
| 2026-10-05T03:19:58+00:00 | 1.1 | Metadata fetched for 28,000 of 130,391 entries. |
| 2026-10-05T03:20:12+00:00 | 1.1 | Metadata fetched for 30,000 of 130,391 entries. |
| 2026-10-05T03:20:24+00:00 | 1.1 | Metadata fetched for 32,000 of 130,391 entries. |
| 2026-10-05T03:20:37+00:00 | 1.1 | Metadata fetched for 34,000 of 130,391 entries. |
| 2026-10-05T03:20:50+00:00 | 1.1 | Metadata fetched for 36,000 of 130,391 entries. |
| 2026-10-05T03:21:03+00:00 | 1.1 | Metadata fetched for 38,000 of 130,391 entries. |
| 2026-10-05T03:21:16+00:00 | 1.1 | Metadata fetched for 40,000 of 130,391 entries. |
| 2026-10-05T03:21:29+00:00 | 1.1 | Metadata fetched for 42,000 of 130,391 entries. |
| 2026-10-05T03:21:43+00:00 | 1.1 | Metadata fetched for 44,000 of 130,391 entries. |
| 2026-10-05T03:21:56+00:00 | 1.1 | Metadata fetched for 46,000 of 130,391 entries. |
| 2026-10-05T03:22:10+00:00 | 1.1 | Metadata fetched for 48,000 of 130,391 entries. |
| 2026-10-05T03:22:27+00:00 | 1.1 | Metadata fetched for 50,000 of 130,391 entries. |
| 2026-10-05T03:22:48+00:00 | 1.1 | Metadata fetched for 52,000 of 130,391 entries. |
| 2026-10-05T03:23:10+00:00 | 1.1 | Metadata fetched for 54,000 of 130,391 entries. |
| 2026-10-05T03:23:34+00:00 | 1.1 | Metadata fetched for 56,000 of 130,391 entries. |
| 2026-10-05T03:23:57+00:00 | 1.1 | Metadata fetched for 58,000 of 130,391 entries. |
| 2026-10-05T03:24:20+00:00 | 1.1 | Metadata fetched for 60,000 of 130,391 entries. |
| 2026-10-05T03:24:41+00:00 | 1.1 | Metadata fetched for 62,000 of 130,391 entries. |
| 2026-10-05T03:25:03+00:00 | 1.1 | Metadata fetched for 64,000 of 130,391 entries. |
| 2026-10-05T03:25:25+00:00 | 1.1 | Metadata fetched for 66,000 of 130,391 entries. |
| 2026-10-05T03:25:46+00:00 | 1.1 | Metadata fetched for 68,000 of 130,391 entries. |
| 2026-10-05T03:26:06+00:00 | 1.1 | Metadata fetched for 70,000 of 130,391 entries. |
| 2026-10-05T03:26:28+00:00 | 1.1 | Metadata fetched for 72,000 of 130,391 entries. |
| 2026-10-05T03:26:48+00:00 | 1.1 | Metadata fetched for 74,000 of 130,391 entries. |
| 2026-10-05T03:27:09+00:00 | 1.1 | Metadata fetched for 76,000 of 130,391 entries. |
| 2026-10-05T03:27:31+00:00 | 1.1 | Metadata fetched for 78,000 of 130,391 entries. |
| 2026-10-05T03:27:57+00:00 | 1.1 | Metadata fetched for 80,000 of 130,391 entries. |
| 2026-10-05T03:28:21+00:00 | 1.1 | Metadata fetched for 82,000 of 130,391 entries. |
| 2026-10-05T03:28:43+00:00 | 1.1 | Metadata fetched for 84,000 of 130,391 entries. |
| 2026-10-05T03:29:11+00:00 | 1.1 | Metadata fetched for 86,000 of 130,391 entries. |
| 2026-10-05T03:29:29+00:00 | 1.1 | Metadata fetched for 88,000 of 130,391 entries. |
| 2026-10-05T03:29:43+00:00 | 1.1 | Metadata fetched for 90,000 of 130,391 entries. |
| 2026-10-05T03:29:59+00:00 | 1.1 | Metadata fetched for 92,000 of 130,391 entries. |
| 2026-10-05T03:30:18+00:00 | 1.1 | Metadata fetched for 94,000 of 130,391 entries. |
| 2026-10-05T03:30:36+00:00 | 1.1 | Metadata fetched for 96,000 of 130,391 entries. |
| 2026-10-05T03:30:53+00:00 | 1.1 | Metadata fetched for 98,000 of 130,391 entries. |
| 2026-10-05T03:31:12+00:00 | 1.1 | Metadata fetched for 100,000 of 130,391 entries. |
| 2026-10-05T03:31:31+00:00 | 1.1 | Metadata fetched for 102,000 of 130,391 entries. |
| 2026-10-05T03:31:48+00:00 | 1.1 | Metadata fetched for 104,000 of 130,391 entries. |
| 2026-10-05T03:32:08+00:00 | 1.1 | Metadata fetched for 106,000 of 130,391 entries. |
| 2026-10-05T03:32:25+00:00 | 1.1 | Metadata fetched for 108,000 of 130,391 entries. |
| 2026-10-05T03:32:44+00:00 | 1.1 | Metadata fetched for 110,000 of 130,391 entries. |
| 2026-10-05T03:33:01+00:00 | 1.1 | Metadata fetched for 112,000 of 130,391 entries. |
| 2026-10-05T03:33:23+00:00 | 1.1 | Metadata fetched for 114,000 of 130,391 entries. |
| 2026-10-05T03:33:49+00:00 | 1.1 | Metadata fetched for 116,000 of 130,391 entries. |
| 2026-10-05T03:34:14+00:00 | 1.1 | Metadata fetched for 118,000 of 130,391 entries. |
| 2026-10-05T03:34:39+00:00 | 1.1 | Metadata fetched for 120,000 of 130,391 entries. |
| 2026-10-05T03:35:02+00:00 | 1.1 | Metadata fetched for 122,000 of 130,391 entries. |
| 2026-10-05T03:35:22+00:00 | 1.1 | Metadata fetched for 124,000 of 130,391 entries. |
| 2026-10-05T03:35:49+00:00 | 1.1 | Metadata fetched for 126,000 of 130,391 entries. |
| 2026-10-05T03:36:16+00:00 | 1.1 | Metadata fetched for 128,000 of 130,391 entries. |
| 2026-10-05T03:36:38+00:00 | 1.1 | Metadata fetched for 130,000 of 130,391 entries. |
| 2026-10-05T03:36:46+00:00 | 1.1 | Catalogue written: 130,391 entries. Tier counts: {1: 3871, 2: 34222, 3: 17375, 4: 74923}. |
| 2026-10-05T03:43:02+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-05T03:43:03+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-05T03:47:17+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-05T03:47:18+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-05T03:50:51+00:00 | 1.3 | Bridge run starting: 2,647 entries pending of 130,391 catalogued (tiers 1 to 3), 16 IO workers, 14 geometry workers. |
| 2026-10-05T03:55:51+00:00 | 1.3 | 2,297/2,647 entries, 1,331 bridges, 0 failed, 7.7 entries/s, ~0.0 h remaining. |
| 2026-10-05T03:56:45+00:00 | 1.3 | Bridge run finished: 2,647 entries in 5.9 min, 2,865 bridges, 0 failed, 7.5 entries/s. |
| 2026-10-05T03:59:11+00:00 | 4.1b | About tab generated: 53 references, 11/13 datasets resolved, worked example selected, 0 value(s) not recorded, 0 source(s) publish no licence. |
| 2026-10-05T03:59:22+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-05T03:59:23+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-05T04:00:56+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-05T04:00:57+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-05T04:05:37+00:00 | 4.1b | About tab generated: 53 references, 11/13 datasets resolved, worked example selected, 0 value(s) not recorded, 0 source(s) publish no licence. |
| 2026-10-05T04:07:00+00:00 | 4.1b | About tab generated: 53 references, 11/13 datasets resolved, worked example selected, 0 value(s) not recorded, 0 source(s) publish no licence. |
| 2026-10-05T04:07:10+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-05T04:07:11+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-05T04:09:12+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-05T04:09:13+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-05T04:09:30+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-05T04:09:31+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-05T04:10:12+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-05T04:10:13+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-05T04:11:59+00:00 | 4.1b | About tab generated: 53 references, 11/13 datasets resolved, worked example selected, 0 value(s) not recorded, 0 source(s) publish no licence. |
| 2026-10-05T04:13:00+00:00 | 4.1b | About tab generated: 53 references, 11/13 datasets resolved, worked example selected, 0 value(s) not recorded, 0 source(s) publish no licence. |
| 2026-10-05T04:13:13+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-05T04:13:14+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-05T04:17:03+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-05T04:17:04+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-05T04:18:09+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-05T04:18:10+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-05T04:19:25+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-05T04:19:26+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-05T04:20:50+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-05T04:20:51+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-05T04:22:14+00:00 | 4.3 | Atlas built: 130,391 entries, 285,996 bridges (15,804 novel), 30,149 ligands, 21,717 degrons, 650 ligases, 1,650 lysines, 190.2 MB. |
| 2026-10-05T04:24:40+00:00 | 5.2 | imid_degradation_score written for 4,650 degron candidates; 17,067 carry no C2H2 motif and are left NULL. |
| 2026-10-05T04:26:53+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-05T04:26:54+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 4 measured floor(s) missed. |
| 2026-10-05T04:28:28+00:00 | 2.1b | Zinc-finger scan over 20,279 cached models. |
| 2026-10-05T04:28:54+00:00 | 2.1b | Zinc-finger table: 7,452 C2H2 motifs over 1,123 proteins, of which 2,792 (37.5%) carry no hairpin candidate and were unreachable by the per-candidate column. |
| 2026-10-05T04:29:11+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-05T04:29:12+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 4 measured floor(s) missed. |
| 2026-10-05T04:29:24+00:00 | 4.1b | About tab generated: 53 references, 11/13 datasets resolved, worked example selected, 0 value(s) not recorded, 0 source(s) publish no licence. |
| 2026-10-05T04:31:33+00:00 | 2.1 | Human reviewed proteome: 20,431 accessions. |
| 2026-10-05T04:31:33+00:00 | 2.1 | Degron scan: 20,431 accessions pending, 16 IO workers, 14 DSSP workers. |
| 2026-10-05T04:32:40+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 0 measured floor(s) missed. |
| 2026-10-05T04:32:40+00:00 | 9 | Validation run against binman.sqlite: 8 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-05T04:36:25+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 0 measured floor(s) missed. |
| 2026-10-05T04:36:25+00:00 | 9 | Validation run against binman.sqlite: 8 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-05T04:36:36+00:00 | 2.1 | 504/20,431 scanned, 548 candidates, 165 failed, 1.7/s, ~3.3 h remaining. |
| 2026-10-05T04:38:11+00:00 | 4.1b | About tab generated: 53 references, 11/13 datasets resolved, worked example selected, 0 value(s) not recorded, 0 source(s) publish no licence. |
| 2026-10-05T04:38:23+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 0 measured floor(s) missed. |
| 2026-10-05T04:38:24+00:00 | 9 | Validation run against binman.sqlite: 8 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-05T04:39:19+00:00 | 4.1b | About tab generated: 53 references, 11/13 datasets resolved, worked example selected, 0 value(s) not recorded, 0 source(s) publish no licence. |
| 2026-10-05T04:39:59+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 0 measured floor(s) missed. |
| 2026-10-05T04:39:59+00:00 | 9 | Validation run against binman.sqlite: 8 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-05T04:41:38+00:00 | 2.1 | 1,004/20,431 scanned, 1,064 candidates, 175 failed, 1.7/s, ~3.3 h remaining. |
| 2026-10-05T04:43:33+00:00 | 4.1b | About tab generated: 53 references, 11/13 datasets resolved, worked example selected, 0 value(s) not recorded, 0 source(s) publish no licence. |
| 2026-10-05T04:44:05+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-05T04:44:05+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 4 measured floor(s) missed. |
| 2026-10-05T04:46:38+00:00 | 2.1 | 1,505/20,431 scanned, 1,707 candidates, 186 failed, 1.7/s, ~3.2 h remaining. |
| 2026-10-05T04:51:38+00:00 | 2.1 | 2,015/20,431 scanned, 2,222 candidates, 194 failed, 1.7/s, ~3.1 h remaining. |
| 2026-10-05T04:52:14+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-05T04:52:15+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 4 measured floor(s) missed. |
| 2026-10-05T04:56:42+00:00 | 2.1 | 2,523/20,431 scanned, 2,805 candidates, 211 failed, 1.7/s, ~3.0 h remaining. |
| 2026-10-05T05:01:42+00:00 | 2.1 | 3,018/20,431 scanned, 3,452 candidates, 224 failed, 1.7/s, ~2.9 h remaining. |
| 2026-10-05T05:06:43+00:00 | 2.1 | 3,524/20,431 scanned, 4,054 candidates, 233 failed, 1.7/s, ~2.8 h remaining. |
| 2026-10-05T05:11:43+00:00 | 2.1 | 4,024/20,431 scanned, 4,523 candidates, 243 failed, 1.7/s, ~2.7 h remaining. |
| 2026-10-05T05:12:08+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-05T05:12:08+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 4 measured floor(s) missed. |
| 2026-10-05T05:16:44+00:00 | 2.1 | 4,526/20,431 scanned, 5,094 candidates, 248 failed, 1.7/s, ~2.6 h remaining. |
| 2026-10-05T05:19:18+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-05T05:19:18+00:00 | 9 | Validation run against binman.sqlite: 5 metric(s) not computed (dataset unavailable), 4 measured floor(s) missed. |
| 2026-10-05T05:21:44+00:00 | 2.1 | 5,032/20,431 scanned, 5,562 candidates, 258 failed, 1.7/s, ~2.6 h remaining. |
| 2026-10-05T05:26:45+00:00 | 2.1 | 5,537/20,431 scanned, 6,131 candidates, 273 failed, 1.7/s, ~2.5 h remaining. |
| 2026-10-05T05:27:57+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-05T05:27:57+00:00 | 9 | Validation run against binman.sqlite: 5 metric(s) not computed (dataset unavailable), 4 measured floor(s) missed. |
| 2026-10-05T05:31:45+00:00 | 2.1 | 6,035/20,431 scanned, 6,746 candidates, 282 failed, 1.7/s, ~2.4 h remaining. |
| 2026-10-05T05:33:33+00:00 | 4.1b | About tab generated: 53 references, 11/13 datasets resolved, worked example selected, 0 value(s) not recorded, 0 source(s) publish no licence. |
| 2026-10-05T05:33:41+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-05T05:33:42+00:00 | 9 | Validation run against binman.sqlite: 5 metric(s) not computed (dataset unavailable), 4 measured floor(s) missed. |
| 2026-10-05T05:34:13+00:00 | 4.1b | About tab generated: 53 references, 11/13 datasets resolved, worked example selected, 0 value(s) not recorded, 0 source(s) publish no licence. |
| 2026-10-05T05:34:48+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-05T05:34:48+00:00 | 9 | Validation run against binman.sqlite: 5 metric(s) not computed (dataset unavailable), 4 measured floor(s) missed. |
| 2026-10-05T05:36:45+00:00 | 2.1 | 6,540/20,431 scanned, 7,444 candidates, 291 failed, 1.7/s, ~2.3 h remaining. |
| 2026-10-05T05:37:43+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-05T05:37:43+00:00 | 9 | Validation run against binman.sqlite: 5 metric(s) not computed (dataset unavailable), 4 measured floor(s) missed. |
| 2026-10-05T05:41:46+00:00 | 2.1 | 7,045/20,431 scanned, 7,976 candidates, 304 failed, 1.7/s, ~2.2 h remaining. |
| 2026-10-05T05:46:46+00:00 | 2.1 | 7,554/20,431 scanned, 8,424 candidates, 317 failed, 1.7/s, ~2.1 h remaining. |
| 2026-10-05T05:51:46+00:00 | 2.1 | 8,057/20,431 scanned, 8,963 candidates, 335 failed, 1.7/s, ~2.1 h remaining. |
| 2026-10-05T05:56:46+00:00 | 2.1 | 8,559/20,431 scanned, 9,436 candidates, 347 failed, 1.7/s, ~2.0 h remaining. |
| 2026-10-05T06:01:47+00:00 | 2.1 | 9,061/20,431 scanned, 9,932 candidates, 356 failed, 1.7/s, ~1.9 h remaining. |
| 2026-10-05T06:06:47+00:00 | 2.1 | 9,578/20,431 scanned, 10,450 candidates, 373 failed, 1.7/s, ~1.8 h remaining. |
| 2026-10-05T06:11:47+00:00 | 2.1 | 10,084/20,431 scanned, 11,050 candidates, 386 failed, 1.7/s, ~1.7 h remaining. |
| 2026-10-05T06:16:49+00:00 | 2.1 | 10,591/20,431 scanned, 11,470 candidates, 400 failed, 1.7/s, ~1.6 h remaining. |
| 2026-10-05T06:21:49+00:00 | 2.1 | 11,096/20,431 scanned, 12,090 candidates, 408 failed, 1.7/s, ~1.5 h remaining. |
| 2026-10-05T06:26:49+00:00 | 2.1 | 11,600/20,431 scanned, 12,539 candidates, 418 failed, 1.7/s, ~1.5 h remaining. |
| 2026-10-05T06:31:50+00:00 | 2.1 | 12,086/20,431 scanned, 13,016 candidates, 424 failed, 1.7/s, ~1.4 h remaining. |
| 2026-10-05T06:36:51+00:00 | 2.1 | 12,583/20,431 scanned, 13,526 candidates, 437 failed, 1.7/s, ~1.3 h remaining. |
| 2026-10-05T06:41:52+00:00 | 2.1 | 13,070/20,431 scanned, 14,039 candidates, 446 failed, 1.7/s, ~1.2 h remaining. |
| 2026-10-05T06:46:53+00:00 | 2.1 | 13,559/20,431 scanned, 14,613 candidates, 456 failed, 1.7/s, ~1.1 h remaining. |
| 2026-10-05T06:51:53+00:00 | 2.1 | 14,047/20,431 scanned, 15,200 candidates, 466 failed, 1.7/s, ~1.1 h remaining. |
| 2026-10-05T06:56:55+00:00 | 2.1 | 14,534/20,431 scanned, 15,737 candidates, 475 failed, 1.7/s, ~1.0 h remaining. |
| 2026-10-05T07:01:56+00:00 | 2.1 | 15,019/20,431 scanned, 16,397 candidates, 481 failed, 1.7/s, ~0.9 h remaining. |
| 2026-10-05T07:06:57+00:00 | 2.1 | 15,509/20,431 scanned, 17,088 candidates, 491 failed, 1.7/s, ~0.8 h remaining. |
| 2026-10-05T07:11:57+00:00 | 2.1 | 15,995/20,431 scanned, 17,773 candidates, 499 failed, 1.7/s, ~0.7 h remaining. |
| 2026-10-05T07:16:59+00:00 | 2.1 | 16,484/20,431 scanned, 18,373 candidates, 504 failed, 1.7/s, ~0.7 h remaining. |
| 2026-10-05T07:21:59+00:00 | 2.1 | 16,971/20,431 scanned, 18,962 candidates, 514 failed, 1.7/s, ~0.6 h remaining. |
| 2026-10-05T07:26:59+00:00 | 2.1 | 17,456/20,431 scanned, 19,664 candidates, 522 failed, 1.7/s, ~0.5 h remaining. |
| 2026-10-05T07:32:00+00:00 | 2.1 | 17,936/20,431 scanned, 20,367 candidates, 525 failed, 1.7/s, ~0.4 h remaining. |
| 2026-10-05T07:37:01+00:00 | 2.1 | 18,430/20,431 scanned, 20,761 candidates, 534 failed, 1.7/s, ~0.3 h remaining. |
| 2026-10-05T07:42:01+00:00 | 2.1 | 18,915/20,431 scanned, 21,179 candidates, 542 failed, 1.7/s, ~0.3 h remaining. |
| 2026-10-05T07:47:01+00:00 | 2.1 | 19,406/20,431 scanned, 21,430 candidates, 552 failed, 1.7/s, ~0.2 h remaining. |
| 2026-10-05T07:52:01+00:00 | 2.1 | 19,894/20,431 scanned, 21,654 candidates, 564 failed, 1.7/s, ~0.1 h remaining. |
| 2026-10-05T07:55:51+00:00 | 2.1 | Degron scan complete: 20,279 proteins scanned, 21,717 candidate degrons written, 570 failed. |
| 2026-10-05T07:56:23+00:00 | 4.3 | Atlas built: 130,391 entries, 285,996 bridges (15,804 novel), 30,149 ligands, 21,717 degrons, 650 ligases, 1,650 lysines, 190.2 MB. |
| 2026-10-05T07:58:47+00:00 | 5.2 | imid_degradation_score written for 4,650 degron candidates; 17,067 carry no C2H2 motif and are left NULL. |
| 2026-10-05T07:59:24+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-05T07:59:25+00:00 | 9 | Validation run against binman.sqlite: 5 metric(s) not computed (dataset unavailable), 4 measured floor(s) missed. |
| 2026-10-05T08:02:30+00:00 | 2.1b | Zinc-finger scan over 20,279 cached models. |
| 2026-10-05T08:02:54+00:00 | 2.1b | Zinc-finger table: 7,452 C2H2 motifs over 1,123 proteins, of which 2,792 (37.5%) carry no hairpin candidate and were unreachable by the per-candidate column. |
| 2026-10-05T08:03:04+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-05T08:03:05+00:00 | 9 | Validation run against binman.sqlite: 5 metric(s) not computed (dataset unavailable), 4 measured floor(s) missed. |
| 2026-10-05T08:03:36+00:00 | 9 | Validation run against binman.sqlite: 5 metric(s) not computed (dataset unavailable), 4 measured floor(s) missed. |
| 2026-10-05T08:04:46+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-05T08:04:47+00:00 | 9 | Validation run against binman.sqlite: 5 metric(s) not computed (dataset unavailable), 4 measured floor(s) missed. |
| 2026-10-05T11:16:43+00:00 | 9.5 | Lysine feature ablation over 405,207 lysines in 17974 proteins: best within-protein AUC 0.6678 against the 0.65 floor. Clears it. |
| 2026-10-05T11:17:46+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-05T11:17:54+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-05T11:17:55+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-05T11:18:18+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-05T11:18:19+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-05T11:18:40+00:00 | 4.1b | About tab generated: 53 references, 11/13 datasets resolved, worked example selected, 0 value(s) not recorded, 0 source(s) publish no licence. |
| 2026-10-05T14:13:57+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-05T14:13:58+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-05T14:15:26+00:00 | 3.5 | Triage prediction: 6 entry-ligand pairs, 5 distinct ligands. |
| 2026-10-05T14:15:30+00:00 | 3.5 | Triage prediction complete: 6 pairs classified, 0 unparseable. |
| 2026-10-05T14:15:48+00:00 | 3.5 | Triage prediction: 6,510 entry-ligand pairs, 3,059 distinct ligands. |
| 2026-10-05T14:16:52+00:00 | 3.5 | 250/6,510 classified. |
| 2026-10-05T14:17:30+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-05T14:17:31+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-05T14:17:53+00:00 | 3.5 | 500/6,510 classified. |
| 2026-10-05T14:18:56+00:00 | 3.5 | 750/6,510 classified. |
| 2026-10-05T14:19:57+00:00 | 3.5 | 1,000/6,510 classified. |
| 2026-10-05T14:20:59+00:00 | 3.5 | 1,250/6,510 classified. |
| 2026-10-05T14:22:01+00:00 | 3.5 | 1,500/6,510 classified. |
| 2026-10-05T14:23:02+00:00 | 3.5 | 1,750/6,510 classified. |
| 2026-10-05T14:24:04+00:00 | 3.5 | 2,000/6,510 classified. |
| 2026-10-05T14:25:08+00:00 | 3.5 | 2,250/6,510 classified. |
| 2026-10-05T14:26:09+00:00 | 3.5 | 2,500/6,510 classified. |
| 2026-10-05T14:27:12+00:00 | 3.5 | 2,750/6,510 classified. |
| 2026-10-05T14:28:16+00:00 | 3.5 | 3,000/6,510 classified. |
| 2026-10-05T14:29:19+00:00 | 3.5 | 3,250/6,510 classified. |
| 2026-10-05T14:30:21+00:00 | 3.5 | 3,500/6,510 classified. |
| 2026-10-05T14:31:24+00:00 | 3.5 | 3,750/6,510 classified. |
| 2026-10-05T14:32:26+00:00 | 3.5 | 4,000/6,510 classified. |
| 2026-10-05T14:33:29+00:00 | 3.5 | 4,250/6,510 classified. |
| 2026-10-05T14:34:32+00:00 | 3.5 | 4,500/6,510 classified. |
| 2026-10-05T14:35:35+00:00 | 3.5 | 4,750/6,510 classified. |
| 2026-10-05T14:36:37+00:00 | 3.5 | 5,000/6,510 classified. |
| 2026-10-05T14:37:41+00:00 | 3.5 | 5,250/6,510 classified. |
| 2026-10-05T14:38:44+00:00 | 3.5 | 5,500/6,510 classified. |
| 2026-10-05T14:39:49+00:00 | 3.5 | 5,750/6,510 classified. |
| 2026-10-05T14:40:52+00:00 | 3.5 | 6,000/6,510 classified. |
| 2026-10-05T14:41:55+00:00 | 3.5 | 6,250/6,510 classified. |
| 2026-10-05T14:42:57+00:00 | 3.5 | 6,500/6,510 classified. |
| 2026-10-05T14:42:59+00:00 | 3.5 | Triage prediction complete: 6,510 pairs classified, 12 unparseable. |
| 2026-10-05T14:44:08+00:00 | 3.5 | Triage predictions loaded: 6,498 pairs onto 27,590 bridge rows. |
| 2026-10-05T14:44:24+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-05T14:44:25+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-05T14:44:48+00:00 | 4.1b | About tab generated: 53 references, 11/13 datasets resolved, worked example selected, 0 value(s) not recorded, 0 source(s) publish no licence. |
| 2026-10-05T19:29:21+00:00 | 5.2 | Combined degron model: 5,663 fingers, 32 degraded, 3,565 called by the geometry filter, 184 sequence features and 5 geometry features. |
| 2026-10-05T19:29:26+00:00 | 5.2 | sequence_only: AUC 0.6340 +/- 0.0795 over 20 splits. |
| 2026-10-05T19:29:26+00:00 | 5.2 | geometry_only: AUC 0.5569 +/- 0.0872 over 20 splits. |
| 2026-10-05T19:29:27+00:00 | 5.2 | combined: AUC 0.6331 +/- 0.0834 over 20 splits. |
| 2026-10-05T19:29:42+00:00 | 5.2 | Combined degron model: 5,663 fingers, 32 degraded, 3,565 called by the geometry filter, 184 sequence features and 5 geometry features. |
| 2026-10-05T19:29:46+00:00 | 5.2 | sequence_only: AUC 0.6334 +/- 0.0772 over 100 splits. |
| 2026-10-05T19:29:48+00:00 | 5.2 | geometry_only: AUC 0.5564 +/- 0.0751 over 100 splits. |
| 2026-10-05T19:29:51+00:00 | 5.2 | combined: AUC 0.6348 +/- 0.0794 over 100 splits. |
| 2026-10-05T19:31:10+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
| 2026-10-05T19:32:04+00:00 | 9 | Validation run against binman.sqlite: 0 metric(s) not computed (dataset unavailable), 2 measured floor(s) missed. |
| 2026-10-05T19:32:05+00:00 | 9 | Validation run against binman.sqlite: 4 metric(s) not computed (dataset unavailable), 5 measured floor(s) missed. |
