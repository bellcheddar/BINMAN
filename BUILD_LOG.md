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
