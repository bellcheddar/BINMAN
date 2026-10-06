"""Build the Task B evidence-class corpus (spec 3.4).

**Every label comes from a published curated source, never from this project's
judgement.** The rules are the spec's:

| Class | Label source |
|---|---|
| `molecular_glue` | the **intersection of at least two** of MGDB, MolGlueDB, MGTbind |
| `protac` | PROTAC-DB 3.0 |
| `native_cofactor` | BioLiP2 biologically relevant ligands in cofactor CCD classes |
| `crystallisation_artefact` | BioLiP2 artefact-flagged ligands |
| `bivalent_inhibitor` | **not built**: see `BIVALENT_NOTE` |

Compounds are matched to PDB chemical components by **InChIKey skeleton** (the
first block, which encodes connectivity and ignores stereochemistry and salt
form), because a curated database and the PDB rarely agree on protonation state.

Where the three glue databases disagree about a compound, it is held out of
training and written to `glue_disagreements.tsv`. Disagreement between expert
curators is not noise to be averaged away: it is a labelled hard set, and model
behaviour on it belongs in FINDINGS.md.

Spec 3.4 says to balance the classes by sampling. **Marc overrode that**: "don't
pin to the smallest, treat them all as unique data" (DECISIONS.md D-022). Pinning
every class to the 38 examples PROTAC-DB could contribute would have thrown away
some 20,000 real labels. So every unique example is kept and the imbalance is
made visible instead, by reporting **per-class precision, recall and F1** beside
the macro-F1 rather than the macro figure alone.

Two input forms are used, both allowed by spec 3.4: an entry title plus its
ligand list, and a Europe PMC abstract. The second matters because the structural
form is limited to what has been crystallised, and almost no PROTAC has been.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.common import ATLAS, VALIDATION, Manifest, log_event, write_jsonl  # noqa: E402

CORPUS = ROOT / "lm" / "corpus"
STAGE = "lm_task_b"
SEED = 20261003

CLASSES = ("molecular_glue", "protac", "native_cofactor", "crystallisation_artefact")

BIVALENT_NOTE = (
    "`bivalent_inhibitor` is NOT built. Spec 3.4 defines its label as two binding "
    "sites within ONE chain, taken from the pipeline's own geometry and "
    "cross-checked against the absence of a degrader annotation in all four "
    "databases. Stage 1.3 records bridges between two DISTINCT chains and the "
    "half-interfaces behind them, but it does not detect two spatially separate "
    "sites on a single chain, so the label cannot be derived from what the "
    "pipeline currently produces. Inventing it from ligand size or from "
    "PROTAC-DB membership would be this project's judgement rather than a "
    "published source, which spec 4.1b forbids. Task B therefore ships as a "
    "four-class problem and the macro-F1 is reported over four classes, stated "
    "plainly rather than presented as if it were five."
)

# One definition, in the module that serves it. The corpus, the build-time
# inference stage and the app must send byte-identical prompts or the macro F1
# measured on one does not describe the others.
from app.lm import TRIAGE_SYSTEM as SYSTEM_TRIAGE  # noqa: E402


def skeleton(inchikey: str) -> str:
    """The connectivity block of an InChIKey: ignores stereochemistry and salt."""
    return (inchikey or "").strip().upper().split("-")[0]


def read_tsv(name: str) -> list[dict]:
    path = VALIDATION / f"{name}.tsv"
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def glue_labels() -> tuple[set[str], set[str]]:
    """Skeletons in at least two curated glue databases, and the disagreements."""
    sets = {}
    for name, column in (("mgdb_glues", "inchikey"),
                         ("molgluedb_glues", "inchikey"),
                         ("mgtbind_compounds", "inchikey")):
        sets[name] = {skeleton(r.get(column, "")) for r in read_tsv(name)
                      if skeleton(r.get(column, ""))}
    names = list(sets)
    agreed: set[str] = set()
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            agreed |= sets[names[i]] & sets[names[j]]
    everything: set[str] = set()
    for value in sets.values():
        everything |= value
    return agreed, everything - agreed


def protac_skeletons() -> set[str]:
    """InChIKey skeletons for PROTAC-DB, computed from SMILES with RDKit."""
    from rdkit import Chem, RDLogger

    RDLogger.DisableLog("rdApp.*")
    out: set[str] = set()
    for row in read_tsv("protacdb_protacs"):
        smiles = (row.get("smiles") or "").strip()
        if not smiles:
            continue
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            continue
        try:
            out.add(skeleton(Chem.MolToInchiKey(mol)))
        except Exception:  # noqa: BLE001
            continue
    return {s for s in out if s}


def build(target_per_class: int = 750) -> dict:
    rng = random.Random(SEED)
    CORPUS.mkdir(parents=True, exist_ok=True)

    db = ATLAS / "binman.sqlite"
    if not db.exists():
        raise SystemExit("build the atlas first")
    connection = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row

    # Every chemical component in the atlas, with its InChIKey skeleton.
    from pipeline.ccd_fetch import fetch_chem_comps
    from pipeline.common import Fetcher

    ccds = [r["ccd_id"] for r in connection.execute("SELECT ccd_id FROM ligand")]
    log_event("3.4", f"Task B: resolving InChIKeys for {len(ccds):,} chemical components.")
    fetcher = Fetcher("rcsb")
    skeleton_to_ccd: dict[str, str] = {}
    for meta in fetch_chem_comps(ccds, fetcher=fetcher):
        key = skeleton(meta.get("inchikey", ""))
        if key:
            skeleton_to_ccd.setdefault(key, meta["ccd_id"])
    log_event("3.4", f"Task B: {len(skeleton_to_ccd):,} components carry an InChIKey.")

    agreed, disagreed = glue_labels()
    protacs = protac_skeletons()
    artefacts = {r["ccd_id"].upper() for r in read_tsv("biolip2_artefacts")}

    # Map each label source onto CCD codes present in the atlas.
    labels: dict[str, set[str]] = {c: set() for c in CLASSES}
    labels["molecular_glue"] = {skeleton_to_ccd[s] for s in agreed if s in skeleton_to_ccd}
    labels["protac"] = {skeleton_to_ccd[s] for s in protacs if s in skeleton_to_ccd}
    labels["crystallisation_artefact"] = {
        r["ccd_id"] for r in connection.execute(
            "SELECT ccd_id FROM ligand WHERE biolip_artefact = 1")
    }
    labels["native_cofactor"] = {
        r["ccd_id"] for r in connection.execute(
            "SELECT ccd_id FROM ligand WHERE ccd_class = 'cofactor'")
    }

    # A component can only carry one label. Where sources collide, the more
    # specific designation wins over the more general, in this order.
    priority = ["molecular_glue", "protac", "crystallisation_artefact", "native_cofactor"]
    claimed: set[str] = set()
    for name in priority:
        labels[name] -= claimed
        claimed |= labels[name]

    disagreement_ccds = {skeleton_to_ccd[s] for s in disagreed if s in skeleton_to_ccd}
    disagreement_ccds -= claimed

    log_event("3.4", "Task B label sources mapped onto the atlas: "
                     + ", ".join(f"{k} {len(v):,}" for k, v in labels.items())
                     + f", held out as disagreements {len(disagreement_ccds):,}")

    # Build one example per (entry, labelled ligand): the input is the entry
    # title plus its ligand list, which is what spec 3.4 specifies.
    examples: dict[str, list[dict]] = {c: [] for c in CLASSES}
    for name, codes in labels.items():
        if not codes:
            continue
        placeholders = ",".join("?" for _ in codes)
        rows = connection.execute(
            f"SELECT e.pdb_id, e.title, l.ccd_id, l.name AS ligand_name "
            f"FROM ligand l "
            f"JOIN bridge b ON b.ccd_id = l.ccd_id AND b.status = 'ok' "
            f"JOIN entry e ON e.pdb_id = b.pdb_id "
            f"WHERE l.ccd_id IN ({placeholders}) AND e.title != '' "
            f"GROUP BY e.pdb_id, l.ccd_id",
            tuple(sorted(codes)),
        ).fetchall()
        for row in rows:
            others = [
                r["ccd_id"] for r in connection.execute(
                    "SELECT DISTINCT ccd_id FROM bridge WHERE pdb_id = ? LIMIT 8",
                    (row["pdb_id"],))
            ]
            prompt = (
                f"Entry {row['pdb_id']}: {row['title']}\n"
                f"Ligand of interest: {row['ccd_id']}"
                + (f" ({row['ligand_name']})" if row["ligand_name"] else "")
                + f"\nOther components in the entry: {', '.join(others) or 'none'}"
            )
            examples[name].append({
                "messages": [
                    {"role": "system", "content": SYSTEM_TRIAGE},
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": name},
                ],
                "label": name, "pdb_id": row["pdb_id"], "ccd_id": row["ccd_id"],
            })

    structural_available = {k: len(v) for k, v in examples.items()}

    # Second input form: a Europe PMC abstract cited by the curated database that
    # supplied the label. This is where the PROTAC class gets its examples, since
    # almost none have been crystallised.
    abstracts_path = VALIDATION / "class_abstracts.jsonl"
    abstract_rows: list[dict] = []
    if abstracts_path.exists():
        with abstracts_path.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                label = record.get("label")
                if label not in CLASSES:
                    continue
                prompt = (
                    f"Article: {record.get('title', '')}\n"
                    f"Abstract: {record.get('abstract', '')[:1400]}"
                )
                abstract_rows.append({
                    "messages": [
                        {"role": "system", "content": SYSTEM_TRIAGE},
                        {"role": "user", "content": prompt},
                        {"role": "assistant", "content": label},
                    ],
                    "label": label, "pdb_id": "", "ccd_id": "",
                    "article": record.get("identifier", ""),
                })
                examples[label].append(abstract_rows[-1])

    available = {k: len(v) for k, v in examples.items()}

    # NO class balancing: every unique example is kept (D-022). The split groups
    # by chemical component for the structural rows and by article for the
    # abstract rows, so neither a component nor a paper appears on both sides.
    groups: dict[str, list[dict]] = {}
    for name, rows in examples.items():
        for row in rows:
            key = f"ccd:{row['ccd_id']}" if row.get("ccd_id") else f"art:{row.get('article', '')}"
            groups.setdefault(key, []).append(row)
    keys = sorted(groups)
    rng.shuffle(keys)
    cut_train = int(len(keys) * 0.8)
    cut_valid = int(len(keys) * 0.9)
    train = [r for k in keys[:cut_train] for r in groups[k]]
    valid = [r for k in keys[cut_train:cut_valid] for r in groups[k]]
    test = [r for k in keys[cut_valid:] for r in groups[k]]
    for part in (train, valid, test):
        rng.shuffle(part)
    per_class = None

    counts = {
        "task_b_train": write_jsonl(CORPUS / "task_b_train.jsonl", train),
        "task_b_valid": write_jsonl(CORPUS / "task_b_valid.jsonl", valid),
        "task_b_test": write_jsonl(CORPUS / "task_b_test.jsonl", test),
    }

    with (VALIDATION / "glue_disagreements.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(["ccd_id", "reason"])
        for code in sorted(disagreement_ccds):
            writer.writerow([code, "present in exactly one curated glue database"])

    connection.close()
    report = {
        "classes": list(CLASSES),
        "bivalent_inhibitor": BIVALENT_NOTE,
        "label_sources_mapped_to_ccds": {k: len(v) for k, v in labels.items()},
        "examples_available": available,
        "structural_examples": structural_available,
        "abstract_examples": len(abstract_rows),
        "balanced": False,
        "balancing_note": (
            "Classes are NOT balanced. Spec 3.4 asks for balancing by sampling; "
            "Marc overrode it so that no real label is discarded (D-022). The "
            "imbalance is reported instead, as per-class precision, recall and F1 "
            "beside the macro figure."
        ),
        "class_distribution_train": {
            name: sum(1 for r in train if r["label"] == name) for name in CLASSES
        },
        "counts": counts,
        "glue_disagreements_held_out": len(disagreement_ccds),
        "split_rule": ("Split by chemical component, so no CCD appears in both "
                       "train and test."),
        "label_rule": ("Every label comes from a published curated source. The glue "
                       "label requires agreement between at least two of MGDB, "
                       "MolGlueDB and MGTbind."),
    }
    (CORPUS / "task_b_report.json").write_text(json.dumps(report, indent=2) + "\n")
    Manifest(STAGE).record("build", status="ok", **counts,
                           disagreements=len(disagreement_ccds))
    log_event("3.4", f"Task B corpus: {counts['task_b_train']:,} train / "
                     f"{counts['task_b_valid']:,} valid / {counts['task_b_test']:,} test "
                     f"over {len(CLASSES)} classes, unbalanced, "
                     f"{len(abstract_rows):,} abstract inputs, "
                     f"{len(disagreement_ccds):,} disagreements held out.")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the Task B triage corpus")
    parser.add_argument("--per-class", type=int, default=750)
    args = parser.parse_args()
    print(json.dumps(build(target_per_class=args.per_class), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
