-- BINMAN atlas schema (spec Section 7).
-- Read-only at serve time. Every foreign key and every filterable column is
-- indexed. Every table carries `status`, so a row that failed a stage stays in
-- the table with status = "failed:<reason>" and the counts always reconcile.

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS entry (
  pdb_id TEXT PRIMARY KEY, title TEXT, method TEXT, resolution REAL,
  deposit_date TEXT, release_date TEXT, organism TEXT, assembly_id TEXT,
  tier INTEGER, polymer_entity_count INTEGER, nonpolymer_entity_count INTEGER,
  status TEXT DEFAULT 'ok'
);

CREATE TABLE IF NOT EXISTS ligand (
  ccd_id TEXT PRIMARY KEY, name TEXT, formula TEXT, mw REAL,
  heavy_atoms INTEGER, smiles TEXT, ccd_class TEXT, ccd_class_rule TEXT,
  parent_ccd TEXT, is_furniture INTEGER, biolip_artefact INTEGER DEFAULT 0,
  status TEXT DEFAULT 'ok'
);

CREATE TABLE IF NOT EXISTS polymer_entity (
  id INTEGER PRIMARY KEY, pdb_id TEXT, asym_id TEXT, auth_asym_id TEXT,
  uniprot_acc TEXT, name TEXT, organism TEXT, is_e3 INTEGER DEFAULT 0,
  status TEXT DEFAULT 'ok',
  FOREIGN KEY (pdb_id) REFERENCES entry(pdb_id)
);

-- The Glue Atlas: one row per (entry, ligand instance, chain pair).
CREATE TABLE IF NOT EXISTS bridge (
  id INTEGER PRIMARY KEY, pdb_id TEXT, ccd_id TEXT,
  ligand_label TEXT, assembly_id TEXT,
  entity_a TEXT, entity_b TEXT, chain_a TEXT, chain_b TEXT,
  dsasa_a REAL, dsasa_b REAL, dsasa_total REAL,
  bridging_balance REAL, buried_fraction REAL,
  contacts_a INTEGER, contacts_b INTEGER,
  heavy_atoms INTEGER, ccd_class TEXT,
  -- evidence_class is BINMAN-LM's Task B label, as spec 467 defines it. It is
  -- the only model-derived column in the atlas, so its FieldSpec description
  -- says so where a query builder will see it (D-078).
  symmetry_mediated INTEGER, evidence_class TEXT,
  alpha REAL, alpha_source TEXT,
  interface_residues_a TEXT, interface_residues_b TEXT,
  plip_types_a TEXT, plip_types_b TEXT,
  novel_bridge INTEGER DEFAULT 0,
  structure_file TEXT, status TEXT DEFAULT 'ok',
  FOREIGN KEY (pdb_id) REFERENCES entry(pdb_id),
  FOREIGN KEY (ccd_id) REFERENCES ligand(ccd_id)
);

CREATE TABLE IF NOT EXISTS degron (
  id INTEGER PRIMARY KEY, uniprot_acc TEXT, afdb_id TEXT, gene TEXT,
  start_res INTEGER, end_res INTEGER, tip_res INTEGER, tip_aa TEXT,
  turn_length INTEGER, mean_plddt REAL, tip_rel_sasa REAL,
  -- The third component of degron_geometry_score. It was computed, weighted at
  -- 0.25 and then dropped before anything persisted it, so a quarter of the
  -- shipped score could not be audited, ablated or direction-checked without
  -- re-running the whole scan. See FINDINGS.md.
  regularity REAL,
  degron_geometry_score REAL, motif_family TEXT,
  is_known_neosubstrate INTEGER, structure_file TEXT, status TEXT DEFAULT 'ok'
);

-- Every C2H2 zinc finger in the proteome, with no geometry filter in front of
-- it. Separate from `degron` because the semantics differ: `degron` is per
-- hairpin candidate and this is per finger, so a protein whose scan placed no
-- candidate on its degron still gets an answer here (D-052, D-055).
-- `screen_degraded` is a label from the Sievers screen, NULL where that screen
-- never assayed a window overlapping the finger, never 0 by default.
CREATE TABLE IF NOT EXISTS zinc_finger (
  id INTEGER PRIMARY KEY,
  uniprot_acc TEXT, gene TEXT,
  zf_start INTEGER, zf_end INTEGER, core TEXT,
  mean_plddt REAL,
  imid_degradation_score REAL,
  has_degron_candidate INTEGER,
  screen_degraded INTEGER,
  status TEXT DEFAULT 'ok'
);
CREATE INDEX IF NOT EXISTS zinc_finger_acc ON zinc_finger (uniprot_acc);
CREATE INDEX IF NOT EXISTS zinc_finger_score ON zinc_finger (imid_degradation_score);

CREATE TABLE IF NOT EXISTS ligase (
  uniprot_acc TEXT PRIMARY KEY, gene TEXT, name TEXT, family TEXT, subfamily TEXT,
  pdb_entries INTEGER, best_structure TEXT, pocket_score REAL, pocket_volume_a3 REAL,
  has_ligand INTEGER, expression_breadth INTEGER, tumour_enriched INTEGER,
  substrate_count INTEGER, substrate_count_predicted INTEGER,
  exploitation_status TEXT, triage_score REAL, triage_rank INTEGER,
  structure_file TEXT, status TEXT DEFAULT 'ok'
);

CREATE TABLE IF NOT EXISTS lysine (
  id INTEGER PRIMARY KEY, uniprot_acc TEXT, structure_id TEXT, site_id TEXT,
  res_num INTEGER, nz_rel_sasa REAL, cb_cb_distance REAL, nz_centroid_distance REAL,
  verdict TEXT, observed_diGly INTEGER DEFAULT 0, status TEXT DEFAULT 'ok'
);

-- The lens graph.
CREATE TABLE IF NOT EXISTS edge (
  id INTEGER PRIMARY KEY, source_acc TEXT, target_acc TEXT,
  ccd_id TEXT, edge_type TEXT, evidence TEXT, pdb_id TEXT,
  status TEXT DEFAULT 'ok'
);

-- Every derived row traces back to its source, tool and parameters.
CREATE TABLE IF NOT EXISTS provenance (
  id INTEGER PRIMARY KEY, table_name TEXT, row_id TEXT,
  source TEXT, retrieved_at TEXT, tool TEXT, tool_version TEXT, params TEXT
);

CREATE INDEX IF NOT EXISTS idx_bridge_pdb       ON bridge(pdb_id);
CREATE INDEX IF NOT EXISTS idx_bridge_ccd       ON bridge(ccd_id);
CREATE INDEX IF NOT EXISTS idx_bridge_class     ON bridge(ccd_class);
CREATE INDEX IF NOT EXISTS idx_bridge_balance   ON bridge(bridging_balance);
CREATE INDEX IF NOT EXISTS idx_bridge_dsasa     ON bridge(dsasa_total);
CREATE INDEX IF NOT EXISTS idx_bridge_novel     ON bridge(novel_bridge);
CREATE INDEX IF NOT EXISTS idx_bridge_sym       ON bridge(symmetry_mediated);
CREATE INDEX IF NOT EXISTS idx_bridge_evidence  ON bridge(evidence_class);
CREATE INDEX IF NOT EXISTS idx_bridge_status    ON bridge(status);
-- Compound, and the order matters: every served query filters on status and
-- then sorts, so an index on status alone leaves SQLite sorting the whole table
-- in a temp B-tree to return a page of 200. With these it walks the index.
-- Measured on the default Glue Atlas page: 37 ms to 1 ms.
CREATE INDEX IF NOT EXISTS idx_bridge_status_dsasa   ON bridge(status, dsasa_total DESC);
CREATE INDEX IF NOT EXISTS idx_bridge_status_balance ON bridge(status, bridging_balance DESC);
CREATE INDEX IF NOT EXISTS idx_entry_res        ON entry(resolution);
CREATE INDEX IF NOT EXISTS idx_entry_tier       ON entry(tier);
CREATE INDEX IF NOT EXISTS idx_entry_method     ON entry(method);
CREATE INDEX IF NOT EXISTS idx_ligand_class     ON ligand(ccd_class);
CREATE INDEX IF NOT EXISTS idx_ligand_mw        ON ligand(mw);
CREATE INDEX IF NOT EXISTS idx_ligand_furniture ON ligand(is_furniture);
CREATE INDEX IF NOT EXISTS idx_pe_pdb           ON polymer_entity(pdb_id);
CREATE INDEX IF NOT EXISTS idx_pe_uniprot       ON polymer_entity(uniprot_acc);
CREATE INDEX IF NOT EXISTS idx_pe_is_e3         ON polymer_entity(is_e3);
CREATE INDEX IF NOT EXISTS idx_degron_acc       ON degron(uniprot_acc);
CREATE INDEX IF NOT EXISTS idx_degron_score     ON degron(degron_geometry_score);
CREATE INDEX IF NOT EXISTS idx_degron_plddt     ON degron(mean_plddt);
CREATE INDEX IF NOT EXISTS idx_degron_family    ON degron(motif_family);
CREATE INDEX IF NOT EXISTS idx_degron_known     ON degron(is_known_neosubstrate);
CREATE INDEX IF NOT EXISTS idx_ligase_family    ON ligase(family);
CREATE INDEX IF NOT EXISTS idx_ligase_rank      ON ligase(triage_rank);
CREATE INDEX IF NOT EXISTS idx_ligase_pocket    ON ligase(pocket_score);
CREATE INDEX IF NOT EXISTS idx_ligase_status    ON ligase(exploitation_status);
CREATE INDEX IF NOT EXISTS idx_ligase_gene      ON ligase(gene);
CREATE INDEX IF NOT EXISTS idx_lysine_acc       ON lysine(uniprot_acc);
CREATE INDEX IF NOT EXISTS idx_lysine_verdict   ON lysine(verdict);
CREATE INDEX IF NOT EXISTS idx_lysine_site      ON lysine(site_id);
CREATE INDEX IF NOT EXISTS idx_edge_source      ON edge(source_acc);
CREATE INDEX IF NOT EXISTS idx_edge_target      ON edge(target_acc);
CREATE INDEX IF NOT EXISTS idx_edge_type        ON edge(edge_type);
CREATE INDEX IF NOT EXISTS idx_prov_table       ON provenance(table_name, row_id);
