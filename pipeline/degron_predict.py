"""Score every degron candidate for pomalidomide-induced degradation.

Adds `imid_degradation_score` to the atlas: the probability a C2H2 zinc finger
is degraded by pomalidomide, from the sequence model validated in D-048 and
D-049. This is a different question from `degron_geometry_score`, which asks
whether a hairpin has the right shape and which D-042 showed is uninformative
about degradability. Both columns ship, because they answer different things
and the geometry one is what the UI has always explained.

**Scope, which is the point of the column being nullable.** The model is a
C2H2 zinc-finger model trained on zinc-finger screens. A degron candidate whose
window holds no C2H2 motif gets NULL rather than a number, because the model
has nothing to say about it and a score there would be an invention. Roughly
one in ten of the atlas's hairpin candidates is a zinc finger.

**What the score means.** Trained on the Sievers pomalidomide degrome with
features weighted by the Slabicki alanine scan, it reaches a nested held-out
AUC of 0.830 with sensitivity 0.867 at specificity 0.613, which clears spec
9.2's floors.

**How far it generalises, corrected.** This docstring previously said the score
was specific to pomalidomide and predicted the promiscuous analogs barely at
all, on two compounds. Tested against all 29 glutarimides of the Slabicki
validation panel it transfers above chance to every one of the 24 whose AUC is
estimable, mean 0.779 gene-disjoint at permutation p=0.0005, and breadth does
not predict failure (D-053). The column is still named for pomalidomide because
that is what it was trained and thresholded on, and it should be read as a
glutarimide degron score rather than a pomalidomide-only one. Part of that
transfer is carried by anchored cores the training library shares with the
panel, which `pipeline/degron_panel.py` quantifies rather than hides.
"""

from __future__ import annotations

import argparse
import collections
import csv
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.common import ATLAS, INTERIM, VALIDATION, log_event  # noqa: E402
from pipeline.degron_alascan import weights_vector  # noqa: E402
from pipeline.degron_sequence import C2H2, GROUPS, align, featurise  # noqa: E402

DB = ATLAS / "binman.sqlite"
CACHE = INTERIM / "afdb"
WIDTH = 23
# How far either side of the hairpin to look for the zinc finger it sits in.
FLANK = 20


def train_model():
    """Fit on the full Sievers pomalidomide degrome, alanine-weighted."""
    import numpy as np
    import openpyxl
    from sklearn.linear_model import LogisticRegression

    rows = [r for r in csv.DictReader(
        (VALIDATION / "sievers_zf_screen.tsv").open(encoding="utf-8"),
        delimiter="\t") if r.get("aa_sequence")]
    features, _labels, _genes, columns, kept = featurise(rows)

    positives = set()
    book = openpyxl.load_workbook(
        VALIDATION / "raw" / "aat0572_sievers_data-file-s2.xlsx",
        read_only=True, data_only=True)
    stream = book["pval_FDR"].iter_rows(values_only=True)
    index = {name: i for i, name in enumerate(list(next(stream)))}
    for row in stream:
        if not row or not row[index["Gene"]]:
            continue
        value = row[index["POM.FDR"]]
        if isinstance(value, (int, float)) and value < 0.05:
            positives.add((str(row[index["Gene"]]), int(row[index["AA.Start"]]),
                           int(row[index["AA.Stop"]])))
    labels = np.asarray([
        1 if (r["gene"], int(r["zf_start"]), int(r["zf_stop"])) in positives else 0
        for r in kept])

    importance = json.loads(
        (INTERIM / "degron_alascan_importance.json").read_text())
    weights = weights_vector(columns, importance)

    model = LogisticRegression(C=0.05, max_iter=5000, class_weight="balanced",
                               solver="liblinear")
    model.fit(features * weights, labels)
    return model, weights, columns, int(labels.sum())


def sequence_from_model(path: Path) -> dict[int, str]:
    """Residue number to one-letter code, read from the AlphaFold model."""
    import gemmi

    structure = gemmi.read_structure(str(path))
    structure.setup_entities()
    out: dict[int, str] = {}
    if not len(structure):
        return out
    for chain in structure[0]:
        for residue in chain:
            code = gemmi.find_tabulated_residue(residue.name)
            if code and code.is_amino_acid():
                out[residue.seqid.num] = code.one_letter_code.upper()
    return out


def encode(core: str, columns: list[str]):
    """One feature row for an anchored zinc-finger core."""
    import numpy as np

    values = []
    for column in columns:
        name = column.split(":")
        position = int(name[0][1:]) if name[0].startswith("p") else None
        if position is None or position >= len(core):
            values.append(0.0)
            continue
        values.append(1.0 if core[position] in GROUPS[name[1]] else 0.0)
    return np.asarray(values, dtype=float)


def run(limit: int | None = None) -> dict:
    import numpy as np

    model, weights, columns, n_positive = train_model()

    connection = sqlite3.connect(DB)
    connection.execute(
        "ALTER TABLE degron ADD COLUMN imid_degradation_score REAL"
    ) if "imid_degradation_score" not in {
        r[1] for r in connection.execute("PRAGMA table_info(degron)")} else None

    rows = connection.execute(
        "SELECT id, uniprot_acc, start_res, end_res FROM degron WHERE status = 'ok'"
    ).fetchall()
    if limit:
        rows = rows[:limit]

    by_protein: dict[str, list] = collections.defaultdict(list)
    for row in rows:
        by_protein[row[1]].append(row)

    scored, skipped_no_zf, skipped_no_model = 0, 0, 0
    updates = []
    for accession, candidates in by_protein.items():
        path = next(iter(CACHE.glob(f"*{accession}*")), None)
        if path is None:
            skipped_no_model += len(candidates)
            continue
        residues = sequence_from_model(path)
        if not residues:
            skipped_no_model += len(candidates)
            continue
        for identifier, _acc, start, end in candidates:
            window = "".join(residues.get(n, "X")
                             for n in range(start - FLANK, end + FLANK + 1))
            # Score EVERY zinc finger in the window and keep the best, not the
            # first. A protein like ZNF653 carries many tandem fingers and only
            # one of them is the degron; taking the first scored ZNF653 at 0.106
            # and ZNF692 at 0.046 when both are known pomalidomide substrates.
            cores = [align(m.group(0), WIDTH) for m in C2H2.finditer(window)]
            cores = [c for c in cores if c]
            if not cores:
                skipped_no_zf += 1
                continue
            probability = max(
                float(model.predict_proba(
                    (encode(core, columns) * weights).reshape(1, -1))[0, 1])
                for core in cores)
            updates.append((round(probability, 4), identifier))
            scored += 1

    connection.executemany(
        "UPDATE degron SET imid_degradation_score = ? WHERE id = ?", updates)
    connection.commit()
    connection.close()

    report = {
        "scored": scored,
        "skipped_no_c2h2_motif": skipped_no_zf,
        "skipped_no_model": skipped_no_model,
        "training_positives": n_positive,
        "model": ("logistic regression on C2H2-anchored chemical-group features, "
                  "weighted by the Slabicki alanine scan, trained on the Sievers "
                  "pomalidomide degrome"),
        "validation": ("nested held-out AUC 0.830, sensitivity 0.867 at "
                       "specificity 0.613 (DECISIONS D-048, D-049)"),
    }
    log_event("5.2", f"imid_degradation_score written for {scored:,} degron "
                     f"candidates; {skipped_no_zf:,} carry no C2H2 motif and are "
                     "left NULL.")
    (INTERIM / "degron_predict.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    print(json.dumps(run(limit=args.limit), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
