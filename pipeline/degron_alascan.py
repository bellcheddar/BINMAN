"""Per-position degron importance, measured rather than inferred.

The sequence models so far ask a regression with 184 columns to work out which
positions matter from 14 positives. Slabicki et al. 2025 measured it directly:
every position of eight degron-bearing constructs mutated to alanine and
assayed against twenty glutarimide analogs, 174,640 rows
(10.1016/j.molcel.2025.07.019, supplementary Table S4).

**The mapping.** Every construct is 58 residues with its two C2H2 motifs
beginning at offsets 6 and 34, consistently across all eight genes. The ratio
table numbers positions absolutely, with the construct's start in `Position`,
so `id - start` gives the construct offset and subtracting 6 or 34 lands on the
same anchored coordinates the sequence model uses.

**The statistic.** In the EGFP-low gate a degraded reporter is enriched, so a
mutation that abolishes the degron depletes from that gate and `Ratio.to.WT`
falls below one. The magnitude of `log2(Ratio.to.WT)` is therefore how much
that position matters, and it is averaged across genes and compounds so a
single construct or a single chemotype cannot dominate.
"""

from __future__ import annotations

import argparse
import collections
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.common import INTERIM, VALIDATION, log_event  # noqa: E402

SCAN = VALIDATION / "raw" / "NIHMS2104733-supplement-6.xlsx"
# Offsets of the two C2H2 motifs within every 58-residue construct.
FINGER_OFFSETS = (6, 34)
WIDTH = 23


def position_importance() -> dict:
    """Mean |log2 ratio to wild type| per anchored position, per finger."""
    import openpyxl

    if not SCAN.exists():
        raise SystemExit(f"{SCAN} does not exist")

    book = openpyxl.load_workbook(SCAN, read_only=True, data_only=True)
    stream = book["ZF.AlaScan_Ratio_pval"].iter_rows(values_only=True)
    header = [str(x) for x in next(stream)]
    index = {name: i for i, name in enumerate(header)}

    # finger slot -> anchored position -> list of |log2 ratio|
    effects: dict[int, dict[int, list[float]]] = {0: collections.defaultdict(list),
                                                  1: collections.defaultdict(list)}
    genes: set[str] = set()
    compounds: set[str] = set()
    used = 0
    for row in stream:
        if not row or row[index["Gene"]] is None:
            continue
        if str(row[index["Gate"]]) != "low":
            continue
        try:
            residue = int(row[index["id"]])
            start = int(str(row[index["Position"]]).split("-")[0])
            ratio = float(row[index["Ratio.to.WT"]])
        except (TypeError, ValueError):
            continue
        if ratio <= 0:
            continue
        offset = residue - start
        if not 0 <= offset < 58:
            continue
        genes.add(str(row[index["Gene"]]))
        compounds.add(str(row[index["Drug"]]))
        magnitude = abs(math.log2(ratio))
        for slot, anchor in enumerate(FINGER_OFFSETS):
            position = offset - anchor
            if 0 <= position < WIDTH:
                effects[slot][position].append(magnitude)
                used += 1

    importance = {}
    for slot, by_position in effects.items():
        importance[slot] = {
            position: round(sum(values) / len(values), 4)
            for position, values in sorted(by_position.items()) if values
        }
    report = {
        "source": "Slabicki et al. 2025 Table S4, 10.1016/j.molcel.2025.07.019",
        "n_measurements_used": used,
        "n_genes": len(genes), "genes": sorted(genes),
        "n_compounds": len(compounds), "compounds": sorted(compounds),
        "gate": "low, where a degraded reporter is enriched",
        "importance_finger_1": importance.get(0, {}),
        "importance_finger_2": importance.get(1, {}),
    }
    (INTERIM / "degron_alascan_importance.json").write_text(
        json.dumps(report, indent=2) + "\n")
    log_event("5.2", f"Alanine scan: {used:,} measurements over {len(genes)} genes "
                     f"and {len(compounds)} compounds mapped to anchored positions.")
    return report


def weights_vector(columns: list[str], importance: dict, floor: float = 0.25):
    """Turn measured importance into one multiplier per feature column.

    A position the scan shows is irrelevant gets `floor` rather than zero: the
    scan covers eight degron-bearing genes, so a position that does not matter
    in those eight is weak evidence rather than proof it never matters.
    """
    import numpy as np

    f1 = {int(k): v for k, v in importance.get("importance_finger_1", {}).items()}
    f2 = {int(k): v for k, v in importance.get("importance_finger_2", {}).items()}
    peak = max([*f1.values(), *f2.values()] or [1.0])

    out = []
    for column in columns:
        if column.startswith("f1:p"):
            position = int(column.split(":")[1][1:])
            value = f1.get(position, 0.0)
        elif column.startswith("f2:p"):
            position = int(column.split(":")[1][1:])
            value = f2.get(position, 0.0)
        elif column.startswith("p"):
            position = int(column.split(":")[0][1:])
            value = max(f1.get(position, 0.0), f2.get(position, 0.0))
        else:
            out.append(1.0)
            continue
        out.append(floor + (1.0 - floor) * (value / peak if peak else 0.0))
    return np.asarray(out, dtype=float)


def main() -> int:
    argparse.ArgumentParser(description=__doc__).parse_args()
    report = position_importance()
    top1 = sorted(report["importance_finger_1"].items(),
                  key=lambda kv: -kv[1])[:8]
    print(json.dumps({k: v for k, v in report.items()
                      if not k.startswith("importance")}, indent=2))
    print("\nmost important anchored positions, finger 1:")
    for position, value in top1:
        print(f"  position {position:>2}: mean |log2 ratio to WT| {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
