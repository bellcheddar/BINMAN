"""Every stage writes a manifest, and the model card tells the truth.

CLAUDE.md: "Every stage writes data/manifests/<stage>.jsonl and is resumable and
idempotent." Three stages declared a STAGE constant and never wrote one, so
their runs left no trace anywhere a later build could read: the About page's
stage table is built from the manifests, and a stage absent from it has not
visibly run.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PIPELINE = ROOT / "pipeline"
# Modules that are libraries rather than stages, so a STAGE constant in them
# would be the thing out of place.
NOT_A_STAGE = {"common.py", "geometry.py", "structures.py", "rcsb.py",
               "chem_rules.py", "schema.sql"}


def _stage_modules() -> list[Path]:
    out = []
    for path in sorted(PIPELINE.glob("*.py")):
        if path.name in NOT_A_STAGE or path.name.startswith("_"):
            continue
        if re.search(r"^STAGE\s*=", path.read_text(encoding="utf-8"), re.M):
            out.append(path)
    return out


def test_every_stage_records_a_manifest():
    missing = [p.name for p in _stage_modules()
               if "Manifest(" not in p.read_text(encoding="utf-8")]
    assert not missing, (
        "these declare a STAGE and never write data/manifests/<stage>.jsonl: "
        + ", ".join(missing))


def test_no_manifest_is_orphaned_by_a_rename():
    """A renamed stage leaves its old manifest behind, and the About page's
    stage table reads the directory, so the dead one keeps being reported."""
    manifests = ROOT / "data" / "manifests"
    if not manifests.exists():
        return
    names = set()
    for path in _stage_modules():
        for match in re.finditer(r'^STAGE\s*=\s*"([^"]+)"',
                                 path.read_text(encoding="utf-8"), re.M):
            names.add(match.group(1))
    # Several stages record under a name set elsewhere (a Manifest("bridges")
    # inside another module), so this only insists the rename that happened is
    # not still on disk, rather than that every file maps to a STAGE constant.
    assert not (manifests / "apo_interface.jsonl").exists(), (
        "apo_interface was renamed to interface_persistence; its manifest "
        "should have gone with it")


def test_the_model_card_does_not_claim_task_b_is_untrained():
    """It said "NOT TRAINED: three of five classes have no published label
    source" while 27,590 bridge rows carried its predictions, and the About
    page printed it. A training run regenerates this file, so the claim can
    come back."""
    import sqlite3

    card = ROOT / "models" / "binman-lm" / "training.json"
    atlas = ROOT / "data" / "atlas" / "binman.sqlite"
    if not card.exists() or not atlas.exists():
        return
    tasks = json.loads(card.read_text(encoding="utf-8")).get("tasks") or []
    triage = next((t for t in tasks if "triage" in t.get("tag", "")), None)
    assert triage is not None, "the model card lists no triage task"

    connection = sqlite3.connect(f"file:{atlas}?mode=ro", uri=True)
    try:
        predicted = connection.execute(
            "SELECT COUNT(*) FROM bridge WHERE evidence_class IS NOT NULL"
        ).fetchone()[0]
    finally:
        connection.close()
    if predicted > 0:
        assert "NOT TRAINED" not in (triage.get("status") or ""), (
            f"the card says Task B is not trained while {predicted:,} bridge "
            "rows carry its predictions")
