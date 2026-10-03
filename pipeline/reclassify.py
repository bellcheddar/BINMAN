"""Re-run CCD classification over everything already seen, without re-doing geometry.

The classification rules are cheap and change more often than the geometry does,
so a rule fix should not cost a full pipeline run. This reads every component in
`data/reference/ccd_classes.tsv` plus the atlas ligand table, re-applies the
current rules, and writes the table back. `build_atlas.py` then picks it up.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline.ccd_classes import (  # noqa: E402
    classify, heavy_atoms_from_formula, load_table, save_table,
)
from pipeline.common import ATLAS, log_event  # noqa: E402


def run() -> dict:
    existing = load_table()
    chemistry: dict[str, dict] = {}

    db = ATLAS / "binman.sqlite"
    if db.exists():
        connection = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        for row in connection.execute(
            "SELECT ccd_id, name, formula, mw, heavy_atoms, smiles FROM ligand"
        ):
            chemistry[row["ccd_id"]] = dict(row)
        connection.close()

    codes = set(existing) | set(chemistry)
    changes: dict[str, int] = {}
    rows = []
    for code in sorted(codes):
        meta = chemistry.get(code, {})
        old = existing.get(code, {})
        formula = meta.get("formula") or old.get("formula", "")
        heavy = meta.get("heavy_atoms")
        if heavy in (None, "", 0):
            heavy = heavy_atoms_from_formula(formula)
        try:
            heavy = int(heavy) if heavy not in (None, "") else None
        except (TypeError, ValueError):
            heavy = None

        result = classify(
            code,
            name=meta.get("name") or old.get("name", ""),
            formula=formula,
            mw=meta.get("mw"),
            heavy_atoms=heavy,
            ccd_type=old.get("ccd_type", ""),
            smiles=meta.get("smiles") or old.get("smiles", ""),
        )
        before = old.get("ccd_class")
        if before and before != result.ccd_class:
            changes[f"{before} -> {result.ccd_class}"] = \
                changes.get(f"{before} -> {result.ccd_class}", 0) + 1
        rows.append(result.as_row())

    written = save_table(rows)
    log_event("1.4", f"Reclassified {written:,} chemical components. "
                     f"{sum(changes.values()):,} changed class: "
                     f"{dict(sorted(changes.items(), key=lambda kv: -kv[1])[:6])}")
    return {"components": written, "changed": sum(changes.values()),
            "transitions": dict(sorted(changes.items(), key=lambda kv: -kv[1])[:12])}


def main() -> int:
    argparse.ArgumentParser(description="Re-run CCD classification").parse_args()
    print(json.dumps(run(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
