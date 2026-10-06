"""Cluster the novel, model-called glues by the interface they induce.

A molecular glue class is defined by what it glues, so the clustering is on the
protein pair rather than the chemistry. A pair carrying many distinct ligands is
a medicinal chemistry series somebody is running; a pair with one ligand is a
single observation.

The input is the intersection of three independent signals: the geometric
bridging filter found it, `novel_bridge` says no curated glue database lists it,
and the triage head called it a molecular glue. Homo-oligomeric pairs are
dropped here because a ligand bridging two copies of one protein is a different
question, and symmetry-mediated contacts are already excluded.

**What this does not do is separate induced proximity from a pre-existing
interface.** Both bury surface against two chains and both pass the filter. The
14-3-3 and KRAS-cyclophilin series below are induced; the tubulin and proteasome
series are ligands binding an interface that exists without them. Buried area
sorts them better than anything else here, and the biology sorts them properly.
"""

import sqlite3, collections
c = sqlite3.connect('data/atlas/binman.sqlite'); c.row_factory = sqlite3.Row

ent = collections.defaultdict(dict)        # pdb -> auth chain -> protein name
for r in c.execute("SELECT pdb_id, auth_asym_id, name FROM polymer_entity"):
    for auth in str(r['auth_asym_id'] or '').split(','):
        auth = auth.strip()
        if auth:
            ent[r['pdb_id']][auth] = (r['name'] or '').strip()

def protein(pdb, chain):
    return ent.get(pdb, {}).get(str(chain or '').split('/')[0].strip(), '')

pairs = collections.defaultdict(lambda: {'ligands': set(), 'entries': set(), 'dsasa': []})
rows = c.execute("""
  SELECT pdb_id, ccd_id, chain_a, chain_b, dsasa_total, bridging_balance
  FROM bridge
  WHERE status='ok' AND novel_bridge=1 AND evidence_class='molecular_glue'
    AND symmetry_mediated=0 AND bridging_balance >= 0.4
""").fetchall()
for r in rows:
    a, b = protein(r['pdb_id'], r['chain_a']), protein(r['pdb_id'], r['chain_b'])
    if not a or not b or a == b:
        continue                            # homo-oligomers are a separate story
    key = tuple(sorted((a[:48], b[:48])))
    d = pairs[key]
    d['ligands'].add(r['ccd_id']); d['entries'].add(r['pdb_id'])
    d['dsasa'].append(r['dsasa_total'] or 0)

print('bridges considered: %d, distinct hetero pairs: %d' % (len(rows), len(pairs)))
print()
ranked = sorted(pairs.items(), key=lambda kv: (-len(kv[1]['ligands']), -len(kv[1]['entries'])))
print('%-3s %-5s %-7s %-9s %s' % ('#', 'ligs', 'entries', 'medΔSASA', 'interface'))
import statistics
for i, (k, v) in enumerate(ranked[:18], 1):
    print('%-3d %-5d %-7d %-9.0f %s  +  %s'
          % (i, len(v['ligands']), len(v['entries']),
             statistics.median(v['dsasa']), k[0][:34], k[1][:34]))
print()
multi = [1 for k, v in pairs.items() if len(v['ligands']) >= 3]
print('pairs with 3 or more distinct ligands (a series, not a one-off): %d' % len(multi))

import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline.common import INTERIM, utcnow
report = {
    "generated_at": utcnow(),
    "bridges_considered": len(rows),
    "distinct_hetero_pairs": len(pairs),
    "pairs_with_three_or_more_ligands": len(multi),
    "top_pairs": [
        {"interface": list(k), "n_ligands": len(v["ligands"]),
         "n_entries": len(v["entries"]),
         "median_dsasa": round(statistics.median(v["dsasa"]), 1)}
        for k, v in ranked[:40]
    ],
}
(INTERIM / "novel_glue_classes.json").write_text(json.dumps(report, indent=2) + "\n")
print()
print("written: data/interim/novel_glue_classes.json")
